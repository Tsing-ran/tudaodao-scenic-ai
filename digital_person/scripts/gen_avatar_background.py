"""
数字人场景背景流水线：AI 生成景区背景 → 抠像合成进 Ditto 源肖像 → 产出 avatar 变体。

原理：Ditto 是「驱动原图」引擎，输出帧背景 = 源肖像 PNG 的背景。
∴ 换背景 = 离线把背景合成进源图，运行时零开销、融合质量最高（不走实时抠像）。
变体命名 <base>_bg_<bg_id>.png，对 LiveTalking 就是一个普通 ditto avatar，零改动。

子命令：
  gen     --scenic all|lingshan,xihu     万相 t2i 批量生成景区背景图
  compose --base sweet_bob_ditto --bg all|bg_lingshan [--matting-model birefnet-portrait]
  all                                    gen + compose 一条龙
  sync    --backend http://...:8000      拉取管理端上传的自定义背景并合成（P1）

合成要点（为什么这样做）：
  - 背景整体浅景深虚化 + 人物头缘环带重虚化：Ditto putback 椭圆过渡带在头动时
    会带极轻微背景形变，低频虚化背景下 1-3px 形变肉眼不可辨（规避而非修引擎）。
  - LAB 均值色调对齐：背景色温向人物靠拢，避免「贴上去的」违和感。
"""
import argparse
import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BG_DIR = ROOT / "assets" / "avatar_backgrounds"
MASK_DIR = BG_DIR / "masks"
REVIEW_DIR = BG_DIR / "review"
PREVIEW_DIR = ROOT / "webapp" / "public" / "avatar_backgrounds"
DITTO_AVATARS_DIR = Path(os.environ.get(
    "DITTO_AVATARS_DIR", Path.home() / "Desktop/LiveTalking/data/ditto_avatars"))

W, H = 720, 1280
T2I_MODEL = "wanx2.1-t2i-plus"

# 公共后缀：无人物 + 中央留站位 + 远景浅景深 + 中上部无高对比直线（防 putback 形变穿帮）
_SUFFIX = (
    "，画面中无任何人物，画面中央及下方留出空旷站位区，远景构图，"
    "浅景深整体柔焦虚化，画面中上部无高对比直线结构，柔和自然光，"
    "竖版风景摄影，超写实，8k"
)

# bg_id 与 SCENIC_CONFIG 的景区 id 严格一致（bg_<scenic_id>）
SCENIC_BG_PROMPTS = {
    "lingshan":     "禅意佛境：远处灵山大佛剪影隐现于薄雾缭绕的青色群山之间，金色晨光透过云层，山脚香雾氤氲",
    "nihuawan":     "唐风禅意小镇暮色：白墙黛瓦与木质檐廊远景，暖黄灯笼次第亮起，樱花树影朦胧",
    "xihu":         "烟雨西湖：保俶塔与雷峰塔剪影立于画面上部远山之巅，山影与塔影溶于青灰水汽，下方湖面如镜",
    "huangshan":    "黄山云海日出：远处奇峰与迎客松剪影浮于翻涌云海之上，霞光染金",
    "gugong":       "故宫秋日仰视：金色琉璃瓦角楼飞檐位于画面上部天际，朱红宫墙在画面左右两侧延伸，银杏金黄，晨光柔和",
    "zhangjiajie":  "张家界峰林：石英砂岩石柱群在流动云雾中若隐若现，青绿苍翠，缥缈仙境",
    "bingmayong":   "博物馆大厅氛围：暖棕色调展厅，远处俑坑轮廓在琥珀色射灯下深度虚化成光斑",
    "mogaoku":      "敦煌意境：鸣沙山金色沙丘曲线与月牙泉远景，暖沙色调，天空澄澈微霞",
}


# ───────────────────────── AI 背景生成（万相 t2i） ─────────────────────────

def _download(url: str, dst: Path):
    import httpx
    with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as client:
        with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dst, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)


def gen_background_t2i(bg_id: str, prompt: str, out: Path) -> None:
    import dashscope
    from dashscope import ImageSynthesis
    print(f"[gen] {bg_id} ← {T2I_MODEL} …（约 30-60s）")
    rsp = ImageSynthesis.call(model=T2I_MODEL, prompt=prompt + _SUFFIX, n=1, size=f"{W}*{H}")
    if rsp.status_code != 200:
        sys.exit(f"❌ 文生图失败 {bg_id}: code={rsp.code} msg={rsp.message}")
    _download(rsp.output.results[0].url, out)
    print(f"      ✅ {out}")


def cmd_gen(scenics: list[str]):
    _init_dashscope()
    BG_DIR.mkdir(parents=True, exist_ok=True)
    for sid in scenics:
        if sid not in SCENIC_BG_PROMPTS:
            print(f"⚠️ 未知景区 {sid}，跳过（可选：{','.join(SCENIC_BG_PROMPTS)}）")
            continue
        gen_background_t2i(f"bg_{sid}", SCENIC_BG_PROMPTS[sid], BG_DIR / f"bg_{sid}.png")


def _init_dashscope():
    import dashscope
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        sys.exit("❌ .env 里没有 DASHSCOPE_API_KEY")
    dashscope.api_key = key


# ───────────────────────── 抠像与合成 ─────────────────────────

def extract_person_mask(portrait: Path, model: str = "birefnet-portrait") -> np.ndarray:
    """人物 alpha mask（uint8 HxW）。同 base 只算一次，缓存到 masks/。"""
    cache = MASK_DIR / f"{portrait.stem}.{model}.png"
    if cache.exists():
        return cv2.imread(str(cache), cv2.IMREAD_GRAYSCALE)
    print(f"[mask] rembg({model}) 抠像 {portrait.name} …（首次需下载模型）")
    from rembg import new_session, remove
    img = Image.open(portrait).convert("RGB")
    mask = remove(img, session=new_session(model), only_mask=True)
    mask = np.asarray(mask.convert("L"))
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(cache), mask)
    print(f"      ✅ mask 缓存：{cache}")
    return mask


def fit_cover(img: Image.Image, size: tuple[int, int] = (W, H)) -> Image.Image:
    """等比缩放 + 中心裁剪铺满目标尺寸。"""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def depth_blur(bg: np.ndarray, mask: np.ndarray,
               base_sigma: float = 6, near_sigma: float = 14, band_px: int = 90) -> np.ndarray:
    """两级景深：全图基础虚化 + 人物周边环带重虚化（防 putback 头缘形变穿帮）。"""
    base = cv2.GaussianBlur(bg, (0, 0), base_sigma)
    near = cv2.GaussianBlur(bg, (0, 0), near_sigma)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (band_px, band_px))
    band = cv2.dilate((mask > 64).astype(np.uint8), k).astype(np.float32)
    band = cv2.GaussianBlur(band, (0, 0), band_px / 4)[..., None]  # 软边过渡
    return (near * band + base * (1 - band)).astype(np.uint8)


def tone_match_lab(bg: np.ndarray, portrait: np.ndarray, mask: np.ndarray,
                   strength: float = 0.35) -> np.ndarray:
    """背景 LAB 均值向人物（mask 内像素）靠拢，统一色温。"""
    bg_lab = cv2.cvtColor(bg, cv2.COLOR_RGB2LAB).astype(np.float32)
    p_lab = cv2.cvtColor(portrait, cv2.COLOR_RGB2LAB).astype(np.float32)
    person = mask > 128
    if person.sum() < 1000:
        return bg
    delta = p_lab[person].mean(axis=0) - bg_lab.reshape(-1, 3).mean(axis=0)
    bg_lab += delta * strength
    return cv2.cvtColor(bg_lab.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)


def variant_name(base_id: str, bg_id: str) -> str:
    """变体命名 <base>_bg_<x>：bg_id 自带 bg_ 前缀(预设)直接拼，否则(上传件)补 bg_。
    须与 bridge/server.py 的 _resolve_avatar_variant 保持一致。"""
    suffix = bg_id if bg_id.startswith("bg_") else f"bg_{bg_id}"
    return f"{base_id}_{suffix}"


def compose_variant(base_id: str, portrait: Path, bg_path: Path, bg_id: str,
                    matting_model: str = "birefnet-portrait") -> Path:
    portrait_rgb = np.asarray(Image.open(portrait).convert("RGB"))
    assert portrait_rgb.shape[:2] == (H, W), f"源肖像须为 {W}x{H}，实际 {portrait_rgb.shape}"
    mask = extract_person_mask(portrait, matting_model)

    bg = np.asarray(fit_cover(Image.open(bg_path).convert("RGB")))
    bg = depth_blur(bg, mask)
    bg = tone_match_lab(bg, portrait_rgb, mask)

    # alpha 合成（边缘羽化 ~2px）
    alpha = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 2)[..., None]
    out = (portrait_rgb * alpha + bg * (1 - alpha)).clip(0, 255).astype(np.uint8)

    DITTO_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    variant = DITTO_AVATARS_DIR / f"{variant_name(base_id, bg_id)}.png"
    Image.fromarray(out).save(variant)

    # 副产物：前端预览缩略图 + 审图三联拼板
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    prev = Image.fromarray(out).resize((360, 640), Image.LANCZOS)
    prev.convert("RGB").save(PREVIEW_DIR / f"{bg_id}.jpg", quality=80)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    trip = np.hstack([portrait_rgb, np.asarray(fit_cover(Image.open(bg_path).convert("RGB"))), out])
    Image.fromarray(trip).save(REVIEW_DIR / f"{variant_name(base_id, bg_id)}.jpg", quality=85)

    print(f"[compose] ✅ {variant}")
    return variant


def cmd_compose(base_id: str, bgs: list[str], matting_model: str):
    portrait = DITTO_AVATARS_DIR / f"{base_id}.png"
    if not portrait.exists():
        sys.exit(f"❌ 源肖像不存在：{portrait}")
    done = []
    for bg_id in bgs:
        bg_path = BG_DIR / f"{bg_id}.png"
        if not bg_path.exists():
            print(f"⚠️ 背景图不存在，跳过：{bg_path}（先跑 gen）")
            continue
        done.append(compose_variant(base_id, portrait, bg_path, bg_id, matting_model))
    if done:
        print("\n" + "=" * 60)
        print(f"已产出 {len(done)} 个变体。后续步骤：")
        print("  1. 人工审图：assets/avatar_backgrounds/review/（三联：原肖像|背景|合成）")
        print("  2. 管理端配置：PUT /digital-human/config 带 background_id（如 bg_lingshan）")
        print("  3. ⚠️ 换了背景的景区须重跑 scripts/prerender_faq.py（FAQ 缓存片烘着旧背景）")
        print("=" * 60)


# ───────────────────────── 横版底板（16:9 中景半身，根治"裁竖图头偏大"） ─────────────────────────
# 窗口③工单：游客端舞台已改 16:9 横屏。现有竖版底板塞横框只能裁(头大)或模糊填充(人窄)。
# 根治=做横版构图底板：横版景区背景 + 竖版肖像抠像缩到中景半身、居中、左右留景。
# 复用既有甜美脸(不重跑 InstantID)，前端满幅 object-cover 即可。

LS_W, LS_H = 1280, 720

_LS_SUFFIX = (
    "，画面中无任何人物，画面中央偏下留出半身人物站位区，"
    "主体景物分布于画面左右两侧与中上部、中心视觉留白，"
    "横版风景摄影，远景构图，浅景深整体柔焦虚化，柔和自然光，超写实，8k"
)


def gen_background_landscape(scenic: str, prompt: str, out: Path) -> None:
    from dashscope import ImageSynthesis
    print(f"[gen-ls] {scenic} ← {T2I_MODEL} 横版 {LS_W}*{LS_H} …（约 30-60s）")
    rsp = ImageSynthesis.call(model=T2I_MODEL, prompt=prompt + _LS_SUFFIX, n=1, size=f"{LS_W}*{LS_H}")
    if rsp.status_code != 200:
        sys.exit(f"❌ 横版文生图失败 {scenic}: code={rsp.code} msg={rsp.message}")
    _download(rsp.output.results[0].url, out)
    print(f"      ✅ {out}")


def _foreground_scrim(img: np.ndarray, top_frac: float = 0.52, max_dark: float = 0.42) -> np.ndarray:
    """底部前景压暗渐变：下部 fade 成近景暗场，人物从"前景"浮现而非悬在远景上（治悬空）。
    top_frac 以上不动，往下线性压暗到 max_dark。"""
    h = img.shape[0]
    g = np.zeros(h, np.float32)
    y0 = int(top_frac * h)
    if y0 < h:
        g[y0:] = np.linspace(0, max_dark, h - y0, dtype=np.float32)
    g = cv2.GaussianBlur(g.reshape(-1, 1), (0, 0), h * 0.03).reshape(-1)  # 平滑过渡
    factor = (1.0 - g)[:, None, None]
    return (img.astype(np.float32) * factor).clip(0, 255).astype(np.uint8)


def _vignette(img: np.ndarray, strength: float = 0.22) -> np.ndarray:
    """径向暗角：边缘压暗、聚焦主体，增强景深层次（弱化"贴图"平板感）。"""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h * 0.42                      # 暗角中心略偏上（对齐人脸）
    d = np.sqrt(((xx - cx) / (w * 0.62)) ** 2 + ((yy - cy) / (h * 0.62)) ** 2)
    mask = 1.0 - strength * np.clip(d - 0.55, 0, 1)
    return (img.astype(np.float32) * mask[..., None]).clip(0, 255).astype(np.uint8)


def compose_landscape(base_id: str, portrait: Path, bg_path: Path, scenic: str,
                      out_name: str, person_h: float = 0.92, top: float = 0.05,
                      xc: float = 0.5, matting_model: str = "birefnet-portrait") -> Path:
    """竖版肖像人物抠像 → 缩到中景半身 → 居中粘进横版景区背景。
    person_h=人物高占画高比(0.92≈头占35%)，top=人物顶距上边比，xc=水平中心比。三参可调取景。"""
    portrait_rgb = np.asarray(Image.open(portrait).convert("RGB"))
    mask = extract_person_mask(portrait, matting_model)
    if mask.shape[:2] != portrait_rgb.shape[:2]:
        mask = cv2.resize(mask, (portrait_rgb.shape[1], portrait_rgb.shape[0]))

    # 人物紧致 bbox → 裁出
    ys, xs = np.where(mask > 96)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    pc, pm = portrait_rgb[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]

    # 缩放：人物高 = person_h × 画高
    th = max(1, int(person_h * LS_H))
    sc = th / pc.shape[0]
    tw = max(1, int(pc.shape[1] * sc))
    pc_r = cv2.resize(pc, (tw, th), interpolation=cv2.INTER_LANCZOS4)
    pm_r = cv2.resize(pm, (tw, th), interpolation=cv2.INTER_LANCZOS4)

    # 横版背景：fit_cover 到 1280×720
    bg = np.asarray(fit_cover(Image.open(bg_path).convert("RGB"), (LS_W, LS_H)))

    # 粘贴位置（含越界裁剪）
    px, py = int(xc * LS_W - tw / 2), int(top * LS_H)
    sx0, sy0 = max(0, -px), max(0, -py)
    dx0, dy0 = max(0, px), max(0, py)
    dx1, dy1 = min(LS_W, px + tw), min(LS_H, py + th)
    cw, ch = dx1 - dx0, dy1 - dy0
    cm = np.zeros((LS_H, LS_W), np.uint8)
    cp = np.zeros((LS_H, LS_W, 3), np.uint8)
    if cw > 0 and ch > 0:
        cm[dy0:dy1, dx0:dx1] = pm_r[sy0:sy0 + ch, sx0:sx0 + cw]
        cp[dy0:dy1, dx0:dx1] = pc_r[sy0:sy0 + ch, sx0:sx0 + cw]

    # 横版：基础虚化减轻(远景更真实不糊成一团) + 人物周边重虚化拉开景深(portrait bokeh)
    bg = depth_blur(bg, cm, base_sigma=3.5, near_sigma=15, band_px=120)
    bg = tone_match_lab(bg, cp, cm)
    # 治肩部/边缘硬裁切：①略腐蚀(让羽化吃进人物内侧、消除抠像亮边) ②大羽化(8px 软化所有
    # 人物边含肩侧横线) ③底部 alpha 垂直渐隐(下半身/肩缘溶入背景雾气、无硬底线，契合薄雾意境)
    cm_e = cv2.erode(cm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    a = cv2.GaussianBlur(cm_e.astype(np.float32) / 255.0, (0, 0), 8)
    vfade = np.ones(LS_H, np.float32)
    y0 = int(0.58 * LS_H)
    vfade[y0:] = np.linspace(1.0, 0.10, LS_H - y0, dtype=np.float32)
    alpha = (a * vfade[:, None])[..., None]
    out = (cp * alpha + bg * (1 - alpha)).clip(0, 255).astype(np.uint8)
    # 治"悬空 + 假背景"：底部前景压暗(人物从近景浮现) + 径向暗角(聚焦主体、加景深层次)
    out = _foreground_scrim(out)
    out = _vignette(out)

    DITTO_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    variant = DITTO_AVATARS_DIR / f"{out_name}.png"
    Image.fromarray(out).save(variant)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    # 审图：横版背景 | 合成结果（同 16:9 并排）
    trip = np.hstack([bg, out])
    Image.fromarray(trip).save(REVIEW_DIR / f"{out_name}.jpg", quality=88)
    print(f"[compose-ls] ✅ {variant}  (人物 {tw}x{th} @ x{xc} top{top})")
    return variant


def cmd_landscape(scenic: str, base_id: str, person_h: float, top: float, xc: float,
                  out_name: str | None, matting_model: str):
    if scenic not in SCENIC_BG_PROMPTS:
        sys.exit(f"❌ 未知景区 {scenic}（可选：{','.join(SCENIC_BG_PROMPTS)}）")
    portrait = DITTO_AVATARS_DIR / f"{base_id}.png"
    if not portrait.exists():
        sys.exit(f"❌ 源肖像不存在：{portrait}")
    BG_DIR.mkdir(parents=True, exist_ok=True)
    ls_bg = BG_DIR / f"lsbg_{scenic}.png"
    if not ls_bg.exists():
        _init_dashscope()
        gen_background_landscape(scenic, SCENIC_BG_PROMPTS[scenic], ls_bg)
    else:
        print(f"[gen-ls] 复用已有横版背景 {ls_bg}")
    name = out_name or f"{base_id}_ls_bg_{scenic}"
    compose_landscape(base_id, portrait, ls_bg, scenic, name, person_h, top, xc, matting_model)
    print(f"\n审图：assets/avatar_backgrounds/review/{name}.jpg")
    print(f"验证 Ditto 人脸检测：cd ~/Desktop/LiveTalking 用 --avatar_id {name} 起流")


# ───────────────────────── P1：拉取管理端上传的背景 ─────────────────────────

def cmd_sync(backend: str, base_id: str, matting_model: str):
    """拉 pending 上传背景 → 下载 → 合成 → 回调 ready。本地（有 LiveTalking 数据目录的机器）跑。"""
    import httpx
    with httpx.Client(trust_env=False, timeout=60) as client:
        pending = client.get(f"{backend}/digital-human/background/pending").json()
        if not pending:
            print("没有待合成的上传背景。")
            return
        portrait = DITTO_AVATARS_DIR / f"{base_id}.png"
        for item in pending:
            bg_id = item["bg_id"]
            raw = BG_DIR / f"{bg_id}.png"
            BG_DIR.mkdir(parents=True, exist_ok=True)
            r = client.get(f"{backend}/digital-human/background/file/{bg_id}")
            r.raise_for_status()
            Image.open(io.BytesIO(r.content)).convert("RGB").save(raw)
            compose_variant(base_id, portrait, raw, bg_id, matting_model)
            client.post(f"{backend}/digital-human/background/{bg_id}/ready")
            print(f"[sync] ✅ {bg_id} 已合成并置 ready")


# ───────────────────────── CLI ─────────────────────────

def _parse_scenics(arg: str) -> list[str]:
    return list(SCENIC_BG_PROMPTS) if arg == "all" else [s.strip() for s in arg.split(",") if s.strip()]


def main():
    ap = argparse.ArgumentParser(description="数字人场景背景流水线（生成/合成/同步）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="万相 t2i 批量生成景区背景")
    g.add_argument("--scenic", default="all")

    c = sub.add_parser("compose", help="背景合成进源肖像，产出 avatar 变体")
    c.add_argument("--base", default="sweet_bob_ditto")
    c.add_argument("--bg", default="all", help="all 或 bg_lingshan,bg_xihu…")
    c.add_argument("--matting-model", default="birefnet-portrait",
                   help="rembg 模型：birefnet-portrait（发丝优）/ isnet-general-use（下载小）")

    a = sub.add_parser("all", help="gen + compose")
    a.add_argument("--scenic", default="all")
    a.add_argument("--base", default="sweet_bob_ditto")
    a.add_argument("--matting-model", default="birefnet-portrait")

    s = sub.add_parser("sync", help="拉取管理端上传的背景并合成（P1）")
    s.add_argument("--backend", default="http://localhost:8000")
    s.add_argument("--base", default="sweet_bob_ditto")
    s.add_argument("--matting-model", default="birefnet-portrait")

    ls = sub.add_parser("landscape", help="横版 16:9 中景半身底板（根治裁竖图头偏大）")
    ls.add_argument("--scenic", default="lingshan")
    ls.add_argument("--base", default="sweet_bob_ditto")
    ls.add_argument("--person-h", type=float, default=0.92, help="人物高占画高比(默认0.92≈头35%)")
    ls.add_argument("--top", type=float, default=0.05, help="人物顶距上边比")
    ls.add_argument("--xc", type=float, default=0.5, help="人物水平中心比")
    ls.add_argument("--out", default=None, help="输出名(默认 <base>_ls_bg_<scenic>)")
    ls.add_argument("--matting-model", default="birefnet-portrait")

    args = ap.parse_args()
    if args.cmd == "gen":
        cmd_gen(_parse_scenics(args.scenic))
    elif args.cmd == "compose":
        bgs = [f"bg_{s}" for s in SCENIC_BG_PROMPTS] if args.bg == "all" \
            else [b.strip() for b in args.bg.split(",") if b.strip()]
        cmd_compose(args.base, bgs, args.matting_model)
    elif args.cmd == "all":
        scenics = _parse_scenics(args.scenic)
        cmd_gen(scenics)
        cmd_compose(args.base, [f"bg_{s}" for s in scenics], args.matting_model)
    elif args.cmd == "sync":
        cmd_sync(args.backend.rstrip("/"), args.base, args.matting_model)
    elif args.cmd == "landscape":
        cmd_landscape(args.scenic, args.base, args.person_h, args.top, args.xc,
                      args.out, args.matting_model)


if __name__ == "__main__":
    main()
