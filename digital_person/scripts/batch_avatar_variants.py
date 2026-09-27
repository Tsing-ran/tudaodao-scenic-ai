"""批量：形象库 10 人 × 8 景区 × (16:9+9:16) = 160 个「同一人带景区背景」数字人底图。

流程：①万相生成 8 景区背景各两比例(跳过已有) ②rembg 每形象抠一次人(省时) ③同一抠像
合成到每个景区背景的两个比例（腾讯会议式：景深柔焦背景 + 锐利人物 + 色调匹配 + 软边）。
产物 assets/avatar_variants/<avatar>__<scenic>__<16x9|9x16>.png
用法：unset 代理后 .venv/bin/python scripts/batch_avatar_variants.py
"""
import os
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
import httpx
import dashscope
from dashscope import ImageSynthesis
from dotenv import load_dotenv
from rembg import new_session, remove

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "assets" / "avatar_library"
BGDIR = ROOT / "assets" / "avatar_backgrounds"
OUT = ROOT / "assets" / "avatar_variants"
_HTTP = httpx.Client(trust_env=False, timeout=120, follow_redirects=True)

# 8 景区背景 prompt（无人物、留构图空间、景深虚化）
SCENIC_BG = {
    "lingshan":   "灵山胜境景区风光，晨雾缭绕的黛青远山，远处佛教宝塔与禅意建筑剪影，柔和金色晨光，唯美宁静",
    "nihuawan":   "拈花湾禅意小镇夜景，唐风木构街巷暖黄灯笼，静谧水景倒影，淡雅禅意，温暖柔光",
    "xihu":       "杭州西湖湖光山色，平静湖面远处断桥与雷峰塔剪影，岸边垂柳，烟雨朦胧远山，淡雅清新",
    "huangshan":  "黄山云海日出，奇松立于云雾缭绕的花岗岩峰峦之间，金色霞光，壮丽缥缈",
    "gugong":     "北京故宫风光，红墙金瓦的宫殿庑殿顶，蓝天，庄严恢宏的中式建筑，对称构图",
    "zhangjiajie":"张家界石英砂岩峰林，云雾缭绕的擎天石柱群，葱郁植被，缥缈仙境",
    "bingmayong": "西安兵马俑坑，整齐排列的陶俑军阵，土黄色调，恢宏的考古坑道，肃穆历史感",
    "mogaoku":    "敦煌莫高窟九层楼，崖壁石窟与飞檐木构，黄昏暖光，西北苍茫，壁画飞天意境的柔和氛围",
}
# 比例 → (W, H, 人物高占比, 头顶余量)
ASPECTS = {
    "16x9": (1280, 720, 1.25, 110),   # 横版：人物居中、两侧留景
    "9x16": (720, 1280, 1.05, 80),    # 竖版：人物头+上半身充满高度
}


def gen_backgrounds():
    BGDIR.mkdir(parents=True, exist_ok=True)
    for scenic, prompt in SCENIC_BG.items():
        for asp, (W, H, _, _) in ASPECTS.items():
            dst = BGDIR / f"{scenic}_bg_{asp}.png"
            if dst.exists():
                continue
            shape = "竖版9:16构图" if H > W else "横版16:9构图"
            r = ImageSynthesis.call(
                model="wanx2.1-t2i-plus",
                prompt=f"{prompt}，画面简洁干净，无人物，{shape}，电影感风光摄影，景深虚化，超写实，8k",
                negative_prompt="人物，人，文字，水印，杂乱，过曝", n=1, size=f"{W}*{H}")
            if r.status_code != 200:
                print(f"  ❌ bg {scenic}/{asp}: {r.message}", flush=True); continue
            dst.write_bytes(_HTTP.get(r.output.results[0].url).content)
            print(f"  ✅ bg {dst.name}", flush=True)


def cutout(avatar_png, sess):
    """rembg 抠人一次，返回 (裁好的人物RGB, 对应mask) bbox。"""
    src = Image.open(avatar_png).convert("RGB")
    mask = np.array(remove(np.array(src), session=sess, only_mask=True))
    ys, xs = np.where(mask > 25)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    return src.crop((x0, y0, x1 + 1, y1 + 1)), Image.fromarray(mask).crop((x0, y0, x1 + 1, y1 + 1))


def compose(person, pmask, bg_path, W, H, person_h, top, out):
    th = int(H * person_h); tw = int(person.width * th / person.height)
    pe = person.resize((tw, th), Image.LANCZOS); pm = pmask.resize((tw, th), Image.LANCZOS)
    px = (W - tw) // 2; py = top
    bg = Image.open(bg_path).convert("RGB")
    bw, bh = W, int(bg.height * W / bg.width)
    if bh < H: bh = H; bw = int(bg.width * H / bg.height)
    bg = bg.resize((bw, bh), Image.LANCZOS).crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
    # 色调匹配（人物往背景色温靠 12%，融入）
    p = np.array(pe).astype(np.float32); a = (np.array(pm).astype(np.float32) / 255)[..., None]
    bgm = np.array(bg).astype(np.float32).reshape(-1, 3).mean(0)
    pm_mean = (p * a).reshape(-1, 3).sum(0) / (a.sum() + 1e-6)
    pe = Image.fromarray(np.clip(p + (bgm - pm_mean) * 0.12, 0, 255).astype(np.uint8))
    # 软边（收缩去光晕 + 羽化）
    m = cv2.erode(np.array(pm).astype(np.float32) / 255, np.ones((3, 3), np.uint8), 1)
    alpha = Image.fromarray((np.clip(cv2.GaussianBlur(m, (0, 0), 3.0), 0, 1) * 255).astype(np.uint8))
    canvas = bg.copy(); canvas.paste(pe, (px, py), alpha); canvas.save(out)


def main():
    print("=== 1) 生成 8 景区背景 ×2 比例 ===", flush=True)
    gen_backgrounds()
    print("=== 2) 抠人 + 合成 160 底图 ===", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    sess = new_session("birefnet-portrait")
    n = 0
    for av in sorted(LIB.glob("[FM]*.png")):
        aid = av.stem
        person, pmask = cutout(av, sess)
        for scenic in SCENIC_BG:
            for asp, (W, H, ph, top) in ASPECTS.items():
                bg = BGDIR / f"{scenic}_bg_{asp}.png"
                if not bg.exists():
                    continue
                dst = OUT / f"{aid}__{scenic}__{asp}.png"
                compose(person, pmask, bg, W, H, ph, top, dst)
                n += 1
        print(f"  ✅ {aid} ×16", flush=True)
    print(f"完成 {n} 个底图 → {OUT}", flush=True)


if __name__ == "__main__":
    main()
