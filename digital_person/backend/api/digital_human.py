import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.core.config import settings
from backend.db.database import get_db

router = APIRouter(prefix="/digital-human", tags=["digital-human"])

# 形象库分类法（对标 HeyGen/Synthesia/讯飞 的 faceted 多维标签，裁剪适配景区导览）：
#   style  风格主轴(顶部 tab)：现代 / 古风 / 民族
#   gender 性别(副筛选)：female / male
#   persona 气质人设(对标商用"行业/用途"，对导游=服务人设)
#   outfit  服饰主题   age 年龄段(青年/中年/长者)   fit 适配景区(帮管理员快速选对)
#   recommended 进"推荐"tab(已烘录、开箱即用)   coming_soon 仅预览(InstantID 换装,烘录后上架)
# preview 路径由游客端静态服务（webapp/public/avatars/）；对应真实 MuseTalk avatar 见桥接 AVATAR_MAP。
_AVATAR_PRESETS = [
    # —— 万相高颜值形象库（10 人，每人配 8 景区 × 16:9/9:16 两版带景底图，见 assets/avatar_variants）——
    {"id": "F1_modern",  "name": "知性讲解员", "gender": "female", "style": "现代",
     "persona": "知性干练", "outfit": "海军蓝职业装", "age": "青年", "fit": "会展·都市·博物馆",
     "preview": "/avatars/F1_modern.jpg", "recommended": True},
    {"id": "F2_hanfu",   "name": "汉服讲解员", "gender": "female", "style": "古风",
     "persona": "温婉端庄", "outfit": "汉服襦裙", "age": "青年", "fit": "古镇·禅意",
     "preview": "/avatars/F2_hanfu.jpg", "recommended": True},
    {"id": "F3_youth",   "name": "活力讲解员", "gender": "female", "style": "现代",
     "persona": "亲和热忱", "outfit": "景区马甲", "age": "青年", "fit": "通用·各类景区",
     "preview": "/avatars/F3_youth.jpg", "recommended": True},
    {"id": "F4_qipao",   "name": "旗袍讲解员", "gender": "female", "style": "古风",
     "persona": "典雅端方", "outfit": "改良旗袍", "age": "青年", "fit": "古镇·民国街区",
     "preview": "/avatars/F4_qipao.jpg", "recommended": True},
    {"id": "F5_ethnic",  "name": "民族讲解员", "gender": "female", "style": "民族",
     "persona": "热情亲切", "outfit": "民族服饰银饰", "age": "青年", "fit": "民族风情区",
     "preview": "/avatars/F5_ethnic.jpg", "recommended": True},
    {"id": "F6_mature",  "name": "资深讲解员", "gender": "female", "style": "现代",
     "persona": "端庄稳重", "outfit": "高级职业套装", "age": "中年", "fit": "博物馆/人文景区",
     "preview": "/avatars/F6_mature.jpg", "recommended": True},
    {"id": "M1_modern",  "name": "儒雅讲解员", "gender": "male",   "style": "现代",
     "persona": "沉稳亲和", "outfit": "浅衬衫西装", "age": "青年", "fit": "会展·都市·博物馆",
     "preview": "/avatars/M1_modern.jpg", "recommended": True},
    {"id": "M2_scholar", "name": "文士讲解员", "gender": "male",   "style": "古风",
     "persona": "清隽温润", "outfit": "文士青衫", "age": "青年", "fit": "古镇·禅意",
     "preview": "/avatars/M2_scholar.jpg", "recommended": True},
    {"id": "M3_youth",   "name": "青年讲解员", "gender": "male",   "style": "现代",
     "persona": "朝气敬业", "outfit": "讲解员制服", "age": "青年", "fit": "通用·各类景区",
     "preview": "/avatars/M3_youth.jpg", "recommended": True},
    {"id": "M4_business","name": "商务讲解员", "gender": "male",   "style": "现代",
     "persona": "成熟稳重", "outfit": "商务正装", "age": "中年", "fit": "会展/商务景区",
     "preview": "/avatars/M4_business.jpg", "recommended": True},
    # —— 万相景区专属导览身份库（2026-06-19，每个绑一个景区，studio 底板 dh_<scenic>__<scenic>__16x9）——
    {"id": "dh_lingshan",    "name": "灵山·导览专员",   "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "灵山胜境",
     "preview": "/avatars/dh_lingshan.jpg", "scenic": "lingshan", "recommended": True},
    {"id": "dh_nihuawan",    "name": "拈花湾·导览专员", "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "拈花湾",
     "preview": "/avatars/dh_nihuawan.jpg", "scenic": "nihuawan", "recommended": True},
    {"id": "dh_xihu",        "name": "西湖·导览专员",   "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "西湖",
     "preview": "/avatars/dh_xihu.jpg", "scenic": "xihu", "recommended": True},
    {"id": "dh_mogaoku",     "name": "莫高窟·导览专员", "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "敦煌莫高窟",
     "preview": "/avatars/dh_mogaoku.jpg", "scenic": "mogaoku", "recommended": True},
    {"id": "dh_zhangjiajie", "name": "张家界·导览专员", "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "张家界",
     "preview": "/avatars/dh_zhangjiajie.jpg", "scenic": "zhangjiajie", "recommended": True},
    {"id": "dh_bingmayong",  "name": "兵马俑·导览专员", "gender": "female", "style": "现代",
     "persona": "亲和知性", "outfit": "米白高领针织", "age": "青年", "fit": "秦始皇帝陵博物院",
     "preview": "/avatars/dh_bingmayong.jpg", "scenic": "bingmayong", "recommended": True},
    {"id": "dh_gugong",      "name": "故宫·导览专员",   "gender": "female", "style": "现代",
     "persona": "端庄知性", "outfit": "米白高领针织", "age": "青年", "fit": "故宫博物院",
     "preview": "/avatars/dh_gugong.jpg", "scenic": "gugong", "recommended": True},
    # —— 历史/原 sweet_bob 系列 ——
    {"id": "female_sweet",   "name": "亲和讲解员", "gender": "female", "style": "现代",
     "persona": "亲切热忱", "outfit": "浅色活力装", "age": "青年", "fit": "现代/都市景区",
     "preview": "/avatars/female_sweet.jpg", "recommended": True},
    {"id": "female_guofeng", "name": "古典讲解员", "gender": "female", "style": "古风",
     "persona": "知性温雅", "outfit": "汉服襦裙", "age": "青年", "fit": "古镇·禅意",
     "preview": "/avatars/female_guofeng.jpg", "recommended": True},
    {"id": "male_casual",    "name": "阳光讲解员", "gender": "male",   "style": "现代",
     "persona": "亲切热情", "outfit": "休闲装", "age": "青年", "fit": "现代/都市景区",
     "preview": "/avatars/male_casual.jpg", "recommended": True},
    # —— AI 换装系列（InstantID 同脸换装/妆造，烘录后上架）——
    {"id": "outfit_qipao",  "name": "旗袍", "gender": "female", "style": "古风",
     "persona": "典雅端方", "outfit": "旗袍", "age": "青年", "fit": "古镇·民国街区",
     "preview": "/avatars/outfit_qipao.jpg", "coming_soon": True},
    {"id": "outfit_hanfu",  "name": "汉服", "gender": "female", "style": "古风",
     "persona": "温婉端庄", "outfit": "汉服", "age": "青年", "fit": "古镇·禅意",
     "preview": "/avatars/outfit_hanfu.jpg", "coming_soon": True},
    {"id": "outfit_blazer", "name": "职业正装", "gender": "female", "style": "现代",
     "persona": "沉稳干练", "outfit": "职业正装", "age": "青年", "fit": "会展/都市/博物馆",
     "preview": "/avatars/outfit_blazer.jpg", "coming_soon": True},
    {"id": "outfit_ethnic", "name": "民族服饰", "gender": "female", "style": "民族",
     "persona": "热情亲切", "outfit": "民族服饰", "age": "青年", "fit": "民族风情区",
     "preview": "/avatars/outfit_ethnic.jpg", "coming_soon": True},
    {"id": "outfit_vest",   "name": "导览马甲", "gender": "female", "style": "现代",
     "persona": "规范专业", "outfit": "导览马甲", "age": "青年", "fit": "通用·各类景区",
     "preview": "/avatars/outfit_vest.jpg", "coming_soon": True},
    {"id": "outfit_coat",   "name": "冬季大衣", "gender": "female", "style": "现代",
     "persona": "知性稳重", "outfit": "冬季大衣", "age": "青年", "fit": "北方/冬季景区",
     "preview": "/avatars/outfit_coat.jpg", "coming_soon": True},
    {"id": "female_mature", "name": "稳重讲解员", "gender": "female", "style": "现代",
     "persona": "端庄稳重", "outfit": "知性套装", "age": "中年", "fit": "博物馆/人文景区",
     "preview": "/avatars/female_mature.jpg", "coming_soon": True},
    # —— 旧占位 id（兼容已有配置行，UI 不展示）——
    {"id": "female_elegant", "name": "素雅讲解员", "gender": "female", "style": "古风", "legacy": True},
    {"id": "female_young",   "name": "清新讲解员", "gender": "female", "style": "现代", "legacy": True},
    {"id": "male_mature",    "name": "沉稳讲解员", "gender": "male",   "style": "现代", "legacy": True},
    {"id": "male_young",     "name": "阳光讲解员", "gender": "male",   "style": "现代", "legacy": True},
]

# 风格主轴枚举（前端 tab 顺序）：推荐由 recommended 标记派生
AVATAR_STYLES = ["现代", "古风", "民族"]


# ── 形象「是否真有底板」= 文件系统真值（杜绝撒谎目录：列了却没烘 → 选了静默回落）──
def _find_ditto_dir() -> str | None:
    if os.environ.get("DITTO_AVATARS_DIR"):
        return os.environ["DITTO_AVATARS_DIR"]
    for p in (os.path.expanduser("~/Desktop/LiveTalking/data/ditto_avatars"),
              "/root/autodl-tmp/LiveTalking/data/ditto_avatars"):
        if os.path.isdir(p):
            return p
    return None

_DITTO_DIR = _find_ditto_dir()

# preset id → ditto 底板基名前缀（与桥接 AVATAR_MAP 同源意图）
_DITTO_BASE = {
    "female_sweet": "sweet_bob_ditto", "female_guofeng": "guofeng_female",
    **{i: i for i in ("F1_modern", "F2_hanfu", "F3_youth", "F4_qipao", "F5_ethnic",
                      "F6_mature", "M1_modern", "M2_scholar", "M3_youth", "M4_business")},
    "outfit_qipao": "sweet_outfit_qipao", "outfit_hanfu": "sweet_outfit_hanfu",
    "outfit_blazer": "sweet_outfit_blazer", "outfit_ethnic": "sweet_outfit_ethnic",
    "outfit_vest": "sweet_outfit_vest", "outfit_coat": "sweet_outfit_coat",
    # 万相景区专属导览身份库（2026-06-19，每个绑一个景区；故宫 2026-06-26 补齐）
    **{i: i for i in ("dh_lingshan", "dh_nihuawan", "dh_xihu", "dh_gugong",
                      "dh_mogaoku", "dh_zhangjiajie", "dh_bingmayong")},
}


def _recenter_person(im):
    """生图人物常偏离水平中心（存量底图 235/275 偏心，实测偏差可达 ±14% 画宽），
    cover 裁切播放时偏移会被放大 → 落盘前按最大人脸中心水平平移居中（reflect 补边）。
    cv2 缺失或未检出人脸时原图返回，不阻断生成。"""
    try:
        import cv2
        import numpy as np
    except Exception:  # noqa: BLE001
        return im
    bgr = np.array(im)[:, :, ::-1]
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5,
                                     minSize=(bgr.shape[0] // 10, bgr.shape[0] // 10))
    if len(faces) == 0:
        return im
    x, _y, fw, _fh = max(faces, key=lambda f: f[2] * f[3])
    h, w = bgr.shape[:2]
    dx = round(w / 2.0 - (x + fw / 2.0))
    if abs(dx) <= max(2, w * 0.008):
        return im
    mat = np.float32([[1, 0, dx], [0, 1, 0]])
    shifted = cv2.warpAffine(bgr, mat, (w, h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REFLECT)
    from PIL import Image as _Image
    return _Image.fromarray(shifted[:, :, ::-1])


def _face_center_offset(im):
    """只校验、绝不平移（平移=唇形坍缩根因一，已禁用 _recenter_person）：
    检测最大人脸，返回 (offset_pct, centered)——offset_pct=人脸中心相对画面水平中线的
    偏移占画宽百分比；centered = 偏差 ≤3%。cv2 缺失/未检出人脸时 (None, True) 不阻断。"""
    try:
        import cv2
        import numpy as np
    except Exception:  # noqa: BLE001
        return None, True
    try:
        bgr = np.array(im)[:, :, ::-1]
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5,
                                         minSize=(bgr.shape[0] // 10, bgr.shape[0] // 10))
        if len(faces) == 0:
            return None, True
        x, _y, fw, _fh = max(faces, key=lambda f: f[2] * f[3])
        h, w = bgr.shape[:2]
        offset_pct = abs(w / 2.0 - (x + fw / 2.0)) / w * 100.0
        return round(offset_pct, 1), offset_pct <= 3.0
    except Exception:  # noqa: BLE001
        return None, True


def _ditto_ready(aid: str):
    """该形象在 ditto_avatars/ 是否真有底板。None=查不到目录(如 ECS/无 GPU 机)→不改判定。"""
    if not _DITTO_DIR:
        return None
    base = _DITTO_BASE.get(aid) or (aid if aid.startswith("custom_") else None)
    if not base:
        return False
    return bool(glob.glob(os.path.join(_DITTO_DIR, f"{base}*.png")))


# ── AI 定制形象（万相 t2i 在线生成 → 落 ditto_avatars 即可热切驱动）──
#    存盘目录与背景上传同源；preview 走相对 /rag/digital-human/avatar-preview/<id>。
#    不返回 AutoDL token 绝对地址，避免实例 URL 轮换后游客端裂图。
_CUSTOM_DIR: Path = settings.vector_store_dir.parent / "custom_avatars"
_CUSTOM_JSON: Path = _CUSTOM_DIR / "custom_avatars.json"


def _load_custom() -> list[dict]:
    if _CUSTOM_JSON.is_file():
        try:
            return json.loads(_CUSTOM_JSON.read_text("utf-8"))
        except Exception:
            return []
    return []


def _save_custom(items: list[dict]) -> None:
    _CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    _CUSTOM_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")


def _effective_avatars() -> list[dict]:
    """presets ∧ 文件系统真值：标 ready；无底板者强制 coming_soon。legacy/目录未知者保持原样。
    末尾追加 AI 定制形象（custom_avatars.json，按文件存在性判 ready）。"""
    out = []
    for a in _AVATAR_PRESETS:
        if a.get("legacy"):
            out.append(a); continue
        rdy = _ditto_ready(a["id"])
        if rdy is None:
            out.append(a); continue
        a = dict(a)
        a["ready"] = rdy
        if rdy:
            a.pop("coming_soon", None)
        else:
            a["coming_soon"] = True
        out.append(a)
    for c in _load_custom():
        c = dict(c)
        rdy = _ditto_ready(c["id"])
        c["ready"] = bool(rdy)
        if rdy:
            c.pop("coming_soon", None)
        else:
            c["coming_soon"] = True
        out.append(c)
    return out


# ── 形象「艺名 + 欢迎语」+ 按景区发布（生产者/消费者分离）────────────────────
# 艺名（stage name）= 文艺、平实、不低俗、无营销话术，游客端展示、管理端可改。
# 零 DB 播种默认：跨部署无需先写库即有一套体面艺名（与 _scenic_default_config 同哲学）。
_DEFAULT_STAGE_NAMES = {
    "dh_lingshan": "云岫", "dh_nihuawan": "拈微", "dh_xihu": "照水", "dh_gugong": "望舒",
    "dh_mogaoku": "鸣沙", "dh_zhangjiajie": "青崖", "dh_bingmayong": "扶风",
    "female_sweet": "青禾", "female_guofeng": "疏影", "male_casual": "晓风",
    "F1_modern": "知言", "F2_hanfu": "绾云", "F3_youth": "小满", "F4_qipao": "锦瑟",
    "F5_ethnic": "阿朵", "F6_mature": "静仪",
    "M1_modern": "叙白", "M2_scholar": "墨临", "M3_youth": "远山", "M4_business": "承稷",
}

# 艺名合法性：strip 后 1-8 字，且至少含一个中英文字/数字（拒纯符号/空白）
_STAGE_NAME_OK = re.compile(r"[A-Za-z0-9一-鿿]")


def _clean_stage_name(s: str | None) -> str | None:
    """校验艺名，合法返回 strip 后的值，非法返回 None。"""
    s = (s or "").strip()
    if not s or len(s) > 8 or not _STAGE_NAME_OK.search(s):
        return None
    return s


def _avatar_meta_map(conn) -> dict[str, dict]:
    rows = conn.execute("SELECT avatar_id, stage_name, welcome_text FROM dh_avatar_meta").fetchall()
    return {r["avatar_id"]: {"stage_name": r["stage_name"], "welcome_text": r["welcome_text"]}
            for r in rows}


def _publish_map(conn, scenic_id: str) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT avatar_id, enabled, sort, stage_name_override "
        "FROM dh_avatar_publish WHERE scenic_id=?", (scenic_id,)
    ).fetchall()
    return {r["avatar_id"]: {"enabled": r["enabled"], "sort": r["sort"],
                             "stage_name_override": r["stage_name_override"]} for r in rows}


def _resolve_stage_name(aid: str, name: str | None, meta: dict | None, pub_row: dict | None) -> str:
    """艺名解析优先级：本景区覆盖 > 全局元数据 > 内置默认 > 形象原名 > id。"""
    override = (pub_row or {}).get("stage_name_override")
    if override:
        return override
    if meta and meta.get("stage_name"):
        return meta["stage_name"]
    if aid in _DEFAULT_STAGE_NAMES:
        return _DEFAULT_STAGE_NAMES[aid]
    return name or aid


def _merge_meta(item: dict, meta_map: dict, pub_row: dict | None) -> dict:
    """给形象条目附上 stage_name / welcome_text（增量字段，不改原有字段）。"""
    item = dict(item)
    aid = item["id"]
    meta = meta_map.get(aid)
    stage = _resolve_stage_name(aid, item.get("name"), meta, pub_row)
    item["stage_name"] = stage
    wt = (meta or {}).get("welcome_text") or ""
    item["welcome_text"] = wt if wt else f"大家好，我是{stage}，很高兴为您导览。"
    return item


def _default_visible(a: dict, scenic_id: str | None) -> bool:
    """无 publish 行时的默认可见规则：本景区专属身份 或 通用推荐（已就绪）形象。
    coming_soon/legacy 一律不可见；他景区专属身份对本景区不可见。"""
    if a.get("legacy") or a.get("coming_soon"):
        return False
    if a.get("scenic"):
        return a["scenic"] == scenic_id
    return bool(a.get("recommended"))


def _is_published(a: dict, scenic_id: str | None, pub_row: dict | None) -> bool:
    """游客端最终可见性：有 publish 行按 enabled 强制，否则走默认可见规则。"""
    if pub_row is not None:
        return bool(pub_row["enabled"])
    return _default_visible(a, scenic_id)

# 音色目录：映射到 Qwen3-TTS-Flash 系统音色（桥接 VOICE_MAP 翻译），消息级即时切换。
_VOICE_PRESETS = [
    {"id": "voice_gentle_f", "name": "知性温柔", "gender": "female", "tone": "知性、从容（默认）"},
    {"id": "voice_lively_f", "name": "活泼亲和", "gender": "female", "tone": "明快、亲和"},
    {"id": "voice_wu_f",     "name": "吴侬软语", "gender": "female", "tone": "吴语方言、软糯（江南景区特色）"},
    {"id": "voice_calm_m",   "name": "沉稳大气", "gender": "male",   "tone": "低沉、可靠"},
    {"id": "voice_bright_m", "name": "京腔青年", "gender": "male",   "tone": "北京话、爽朗"},
]

# 场景背景目录：'' = 原始极简灰底（兼容旧行为）；bg_<scenic_id> 与景区 id 严格对应。
# 背景=离线烘进 Ditto 源肖像（变体 <base>_bg_<bg_id>.png），切换「下次连接生效」；
# 变体由 scripts/gen_avatar_background.py 产出，桥接按存在性解析、缺失自动回落原图。
_BACKGROUND_PRESETS = [
    {"id": "",                "name": "极简灰底（原始）", "scenic": None,          "preview": None},
    {"id": "bg_lingshan",     "name": "灵山·禅意佛境",   "scenic": "lingshan",    "preview": "/avatar_backgrounds/bg_lingshan.jpg"},
    {"id": "bg_nihuawan",     "name": "拈花湾·禅镇暮色", "scenic": "nihuawan",    "preview": "/avatar_backgrounds/bg_nihuawan.jpg"},
    {"id": "bg_xihu",         "name": "西湖·烟雨如画",   "scenic": "xihu",        "preview": "/avatar_backgrounds/bg_xihu.jpg"},
    {"id": "bg_huangshan",    "name": "黄山·云海日出",   "scenic": "huangshan",   "preview": "/avatar_backgrounds/bg_huangshan.jpg"},
    {"id": "bg_gugong",       "name": "故宫·朱墙秋色",   "scenic": "gugong",      "preview": "/avatar_backgrounds/bg_gugong.jpg"},
    {"id": "bg_zhangjiajie",  "name": "张家界·峰林云雾", "scenic": "zhangjiajie", "preview": "/avatar_backgrounds/bg_zhangjiajie.jpg"},
    {"id": "bg_bingmayong",   "name": "兵马俑·展厅光影", "scenic": "bingmayong",  "preview": "/avatar_backgrounds/bg_bingmayong.jpg"},
    {"id": "bg_mogaoku",      "name": "敦煌·鸣沙月泉",   "scenic": "mogaoku",     "preview": "/avatar_backgrounds/bg_mogaoku.jpg"},
]

# 管理端上传的自定义背景原图落盘目录（ECS/本地通用；合成由本地脚本拉取）
_BG_UPLOAD_DIR: Path = settings.vector_store_dir.parent / "backgrounds"

_DEFAULT_CONFIG = {
    "avatar_id":       "female_sweet",
    "avatar_name":     "亲和讲解员",
    "voice_id":        "voice_gentle_f",
    "voice_name":      "知性温柔",
    "background_id":   "",
    "background_name": "",
}

# 景区 → 该景区专属身份形象（preset 的 scenic 绑定）。用于「未单独配置时的智能默认」：
# 每个景区自动用自己的专属数字人（灵山→dh_lingshan、故宫→dh_gugong…），跨部署零 DB 播种。
_SCENIC_BOUND_AVATAR = {p["scenic"]: p for p in _AVATAR_PRESETS if p.get("scenic")}


def _scenic_default_config(scenic_id: str) -> dict | None:
    """该景区有专属身份形象且底板就绪 → 以它为 avatar 的默认配置；否则 None（回落全局默认）。
    _ditto_ready 明确返回 False（查到目录但无底板）才放弃；None（无 GPU 目录，如纯云端）仍采用，
    交由桥接候选解析在缺板时优雅回落。"""
    p = _SCENIC_BOUND_AVATAR.get(scenic_id)
    if not p or _ditto_ready(p["id"]) is False:
        return None
    return {**_DEFAULT_CONFIG, "avatar_id": p["id"], "avatar_name": p["name"]}


class ConfigIn(BaseModel):
    scenic_id:   str
    avatar_id:   str
    avatar_name: str
    voice_id:    str
    voice_name:  str
    background_id:   str | None = None   # 可选：旧管理端不传也兼容
    background_name: str | None = None


def _row_to_dict(row) -> dict:
    return {
        "scenic_id":       row["scenic_id"],
        "avatar_id":       row["avatar_id"],
        "avatar_name":     row["avatar_name"],
        "voice_id":        row["voice_id"],
        "voice_name":      row["voice_name"],
        "background_id":   row["background_id"],
        "background_name": row["background_name"],
        "updated_at":      row["updated_at"],
    }


def _valid_background_ids(conn) -> set[str]:
    """合法背景集合 = 内置 presets ∪ 已合成完毕(ready)的上传背景。"""
    ids = {b["id"] for b in _BACKGROUND_PRESETS}
    rows = conn.execute("SELECT bg_id FROM dh_background WHERE status='ready'").fetchall()
    return ids | {r["bg_id"] for r in rows}


def _uploaded_backgrounds(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT bg_id, name, scenic_id, status FROM dh_background ORDER BY created_at DESC"
    ).fetchall()
    return [{"id": r["bg_id"], "name": r["name"], "scenic": r["scenic_id"],
             "preview": f"/avatar_backgrounds/{r['bg_id']}.jpg" if r["status"] == "ready" else None,
             "source": "upload", "status": r["status"]} for r in rows]


def _normalize_preview(item: dict) -> dict:
    """返回可被当前网关稳定解析的预览路径。
    内置静态形象走游客端同源 /avatars；AI 定制形象走同源 /rag 代理。
    兼容历史 custom_avatars.json 中写入的旧 AutoDL 绝对 URL。"""
    prev = item.get("preview")
    if not isinstance(prev, str):
        return item
    item = dict(item)
    marker = "/rag/digital-human/avatar-preview/"
    if marker in prev:
        item["preview"] = marker + prev.split(marker, 1)[1]
    elif prev.startswith("/digital-human/avatar-preview/"):
        item["preview"] = "/rag" + prev
    elif item.get("custom") and not prev.startswith(("/rag/", "/avatars/")):
        item["preview"] = f"/rag/digital-human/avatar-preview/{item['id']}"
    elif item.get("custom") and prev.startswith("/avatars/"):
        item["preview"] = f"/rag/digital-human/avatar-preview/{item['id']}"
    return item


def _absolutize_preview(item: dict) -> dict:
    """兼容旧函数名，实际只做相对 URL 归一化。"""
    return _normalize_preview(item)


@router.get("/presets")
def get_presets(scenic_id: str | None = None, audience: str = "admin"):
    """返回可供选择的形象、音色与场景背景列表。

    - 无参数（旧行为）：返回全量形象，附增量字段 stage_name/welcome_text，向后兼容未升级前端。
    - audience=admin&scenic_id=X：全量 + 每项 `published`（该景区游客端是否可见）。
    - audience=visitor&scenic_id=X：只返回已发布形象（生产者/消费者分离），本景区专属浮顶排序。
    """
    with get_db() as conn:
        backgrounds = _BACKGROUND_PRESETS + _uploaded_backgrounds(conn)
        meta_map = _avatar_meta_map(conn)
        pub_map = _publish_map(conn, scenic_id) if scenic_id else {}

    rows = []  # (原序 idx, avatar dict, pub_row)
    for idx, a in enumerate(_effective_avatars()):
        a = _absolutize_preview(a)
        pub_row = pub_map.get(a["id"])
        a = _merge_meta(a, meta_map, pub_row)
        published = _is_published(a, scenic_id, pub_row) if scenic_id else None
        if audience == "visitor":
            if a.get("legacy"):
                continue
            if scenic_id and not published:
                continue
        elif scenic_id is not None:
            a["published"] = bool(published)
        rows.append((idx, a, pub_row))

    if audience == "visitor" and scenic_id:
        rows.sort(key=lambda t: (0 if t[1].get("scenic") == scenic_id else 1,
                                 (t[2]["sort"] if t[2] else 0), t[0]))

    avatars = [a for _idx, a, _pub in rows]
    return {"avatars": avatars, "voices": _VOICE_PRESETS, "backgrounds": backgrounds}


@router.get("/config")
def get_config(scenic_id: str = "default"):
    """
    获取指定景区的数字人配置。
    若该景区未单独配置，回落到 'default'；若 default 也没有，返回内置默认值。
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM digital_human_config WHERE scenic_id = ?", (scenic_id,)
        ).fetchone()
        if row:
            result = _row_to_dict(row)
        else:
            result = None
            # 无显式配置：优先该景区专属身份形象（灵山→dh_lingshan、故宫→dh_gugong），更具体优先
            if scenic_id != "default":
                bound = _scenic_default_config(scenic_id)
                if bound:
                    result = {**bound, "scenic_id": scenic_id, "updated_at": None, "fallback": True}
                else:
                    # 再回落到全局 default 行
                    drow = conn.execute(
                        "SELECT * FROM digital_human_config WHERE scenic_id = 'default'"
                    ).fetchone()
                    if drow:
                        result = {**_row_to_dict(drow), "scenic_id": scenic_id, "fallback": True}
            if result is None:
                result = {**_DEFAULT_CONFIG, "scenic_id": scenic_id, "updated_at": None,
                          "fallback": True}

        # 附艺名（游客端进场即知当前形象艺名）
        meta_map = _avatar_meta_map(conn)
        pub_row = _publish_map(conn, scenic_id).get(result["avatar_id"]) if scenic_id != "default" else None
        result["stage_name"] = _resolve_stage_name(
            result["avatar_id"], result.get("avatar_name"),
            meta_map.get(result["avatar_id"]), pub_row)
    return result


@router.get("/config/all")
def get_all_configs():
    """返回所有景区的配置快照（管理后台列表页用）。"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM digital_human_config ORDER BY scenic_id").fetchall()
    return [_row_to_dict(r) for r in rows]


@router.put("/config")
def put_config(body: ConfigIn):
    """
    新建或更新指定景区的数字人配置（UPSERT）。
    scenic_id='default' 表示全局默认，其余景区未设置时回落到它。
    """
    avatar_ids = {a["id"] for a in _effective_avatars() if not a.get("coming_soon")}
    voice_ids  = {v["id"] for v in _VOICE_PRESETS}
    if body.avatar_id not in avatar_ids:
        raise HTTPException(status_code=400, detail=f"无效 avatar_id: {body.avatar_id}")
    if body.voice_id not in voice_ids:
        raise HTTPException(status_code=400, detail=f"无效 voice_id: {body.voice_id}")

    with get_db() as conn:
        bg = body.background_id or ""
        if bg and bg not in _valid_background_ids(conn):
            raise HTTPException(status_code=400, detail=f"无效 background_id: {bg}")
        conn.execute(
            """INSERT INTO digital_human_config
                   (scenic_id, avatar_id, avatar_name, voice_id, voice_name,
                    background_id, background_name, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
               ON CONFLICT(scenic_id) DO UPDATE SET
                   avatar_id       = excluded.avatar_id,
                   avatar_name     = excluded.avatar_name,
                   voice_id        = excluded.voice_id,
                   voice_name      = excluded.voice_name,
                   background_id   = excluded.background_id,
                   background_name = excluded.background_name,
                   updated_at      = excluded.updated_at""",
            (body.scenic_id, body.avatar_id, body.avatar_name,
             body.voice_id, body.voice_name, bg, body.background_name or ""),
        )
    return {"ok": True, "scenic_id": body.scenic_id}


# ── 形象艺名/欢迎语 + 按景区发布（管理端=生产者）─────────────────────────

class AvatarMetaIn(BaseModel):
    avatar_id:    str
    stage_name:   str | None = None   # 不传=不改；传空/非法=400
    welcome_text: str | None = None   # 不传=不改；≤60 字


class AvatarPublishIn(BaseModel):
    scenic_id:           str
    avatar_id:           str
    enabled:             bool = True
    sort:                int | None = None
    stage_name_override: str | None = None   # 空串=清除覆盖


@router.get("/avatar-meta")
def get_avatar_meta(scenic_id: str = "default"):
    """管理端：全量形象的艺名/欢迎语/该景区发布状态（供形象管理列表页）。"""
    eff = _effective_avatars()
    with get_db() as conn:
        meta_map = _avatar_meta_map(conn)
        pub_map = _publish_map(conn, scenic_id)
    out = []
    for a in eff:
        aid = a["id"]
        meta = meta_map.get(aid)
        pub = pub_map.get(aid)
        out.append({
            "avatar_id":           aid,
            "name":                a.get("name"),
            "stage_name":          _resolve_stage_name(aid, a.get("name"), meta, pub),
            "welcome_text":        (meta or {}).get("welcome_text") or "",
            "enabled":             bool(pub["enabled"]) if pub else _default_visible(a, scenic_id),
            "sort":                pub["sort"] if pub else 0,
            "stage_name_override": (pub or {}).get("stage_name_override"),
            "source":              "db" if meta else "default",
        })
    return out


@router.put("/avatar-meta")
def put_avatar_meta(body: AvatarMetaIn):
    """更新某形象的艺名/欢迎语（全局，部分字段 COALESCE）。"""
    valid_ids = {a["id"] for a in _effective_avatars()}
    if body.avatar_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"无效 avatar_id: {body.avatar_id}")
    stage = None
    if body.stage_name is not None:
        stage = _clean_stage_name(body.stage_name)
        if stage is None:
            raise HTTPException(status_code=400, detail="艺名需为 1-8 个字符且含有效文字")
    welcome = body.welcome_text.strip()[:60] if body.welcome_text is not None else None

    with get_db() as conn:
        existing = conn.execute(
            "SELECT stage_name, welcome_text FROM dh_avatar_meta WHERE avatar_id=?",
            (body.avatar_id,)
        ).fetchone()
        cur_stage = existing["stage_name"] if existing else None
        cur_welcome = existing["welcome_text"] if existing else None
        new_stage = stage if stage is not None else cur_stage
        if not new_stage:  # 首次只改欢迎语时补一个体面的默认艺名（stage_name NOT NULL）
            nm = next((a.get("name") for a in _effective_avatars()
                       if a["id"] == body.avatar_id), None)
            new_stage = _DEFAULT_STAGE_NAMES.get(body.avatar_id) or nm or body.avatar_id
        new_welcome = welcome if welcome is not None else (cur_welcome or "")
        conn.execute(
            """INSERT INTO dh_avatar_meta (avatar_id, stage_name, welcome_text, updated_at)
               VALUES (?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
               ON CONFLICT(avatar_id) DO UPDATE SET
                 stage_name   = excluded.stage_name,
                 welcome_text = excluded.welcome_text,
                 updated_at   = excluded.updated_at""",
            (body.avatar_id, new_stage, new_welcome))
    return {"ok": True, "avatar_id": body.avatar_id,
            "stage_name": new_stage, "welcome_text": new_welcome}


@router.put("/avatar-publish")
def put_avatar_publish(body: AvatarPublishIn):
    """设置某形象在某景区的发布状态/排序/艺名覆盖（UPSERT）。"""
    valid_ids = {a["id"] for a in _effective_avatars()}
    if body.avatar_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"无效 avatar_id: {body.avatar_id}")
    override = None
    if body.stage_name_override is not None and body.stage_name_override.strip():
        override = _clean_stage_name(body.stage_name_override)
        if override is None:
            raise HTTPException(status_code=400, detail="艺名需为 1-8 个字符且含有效文字")

    with get_db() as conn:
        existing = conn.execute(
            "SELECT sort, stage_name_override FROM dh_avatar_publish "
            "WHERE scenic_id=? AND avatar_id=?", (body.scenic_id, body.avatar_id)
        ).fetchone()
        cur_sort = existing["sort"] if existing else 0
        cur_override = existing["stage_name_override"] if existing else None
        new_sort = body.sort if body.sort is not None else cur_sort
        # 传了 stage_name_override 字段（含空串"清除"）才动它，否则保留原值
        new_override = override if body.stage_name_override is not None else cur_override
        conn.execute(
            """INSERT INTO dh_avatar_publish
                   (scenic_id, avatar_id, enabled, sort, stage_name_override, updated_at)
               VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
               ON CONFLICT(scenic_id, avatar_id) DO UPDATE SET
                 enabled             = excluded.enabled,
                 sort                = excluded.sort,
                 stage_name_override = excluded.stage_name_override,
                 updated_at          = excluded.updated_at""",
            (body.scenic_id, body.avatar_id, int(body.enabled), new_sort, new_override))
    return {"ok": True, "scenic_id": body.scenic_id, "avatar_id": body.avatar_id,
            "enabled": body.enabled}


# ── 自定义背景上传（管理端）──────────────────────────────────────
# 拉取式衔接：后端（可能在 ECS）只登记+存原图；合成必须在有 LiveTalking 数据目录的
# 本地 GPU 机执行——`scripts/gen_avatar_background.py sync --backend <url>` 拉 pending
# → 下载原图 → 抠像合成出 avatar 变体 → 回调置 ready。与「下次连接生效」语义一致。

@router.post("/background/upload")
async def upload_background(file: UploadFile, name: str = Form(...),
                            scenic_id: str | None = Form(None)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(status_code=400, detail="仅支持 png/jpg 背景图")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="背景图不能超过 20MB")
    bg_id = "custom_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    _BG_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = _BG_UPLOAD_DIR / f"{bg_id}{suffix}"
    path.write_bytes(data)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO dh_background (bg_id, name, scenic_id, source, status, file_path)
               VALUES (?, ?, ?, 'upload', 'pending', ?)""",
            (bg_id, name, scenic_id, str(path)),
        )
    return {"ok": True, "bg_id": bg_id, "status": "pending",
            "hint": "本地执行 scripts/gen_avatar_background.py sync 完成合成后即可在配置中使用"}


@router.get("/background/pending")
def pending_backgrounds():
    """本地合成脚本轮询：待合成的上传背景。"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT bg_id, name, scenic_id FROM dh_background WHERE status='pending'"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/background/file/{bg_id}")
def background_file(bg_id: str):
    """本地合成脚本下载上传的背景原图。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT file_path FROM dh_background WHERE bg_id=?", (bg_id,)
        ).fetchone()
    if not row or not Path(row["file_path"]).exists():
        raise HTTPException(status_code=404, detail=f"背景不存在: {bg_id}")
    return FileResponse(row["file_path"])


@router.post("/background/{bg_id}/ready")
def background_ready(bg_id: str):
    """本地合成完成回调：置 ready，背景即可被 PUT /config 引用。"""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE dh_background SET status='ready' WHERE bg_id=?", (bg_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"背景不存在: {bg_id}")
    return {"ok": True, "bg_id": bg_id, "status": "ready"}


# ── AI 定制形象：万相文生图「人景一体」→ 直接落 ditto_avatars，即可热切驱动 ──────
#   原理：Ditto「驱动源图」→ 输出≈源底板，故 AI 生成一张带景半身像存进 ditto_avatars/
#   就是一个可驱动的新形象，无需烘录（set_avatar 运行时重跑 avatar_registrar）。
#   16:9 与 9:16 用同一 seed 两次生图保证同一人，分别供手机端/大屏端，避免比例撕裂。

_SCENIC_SCENE = {
    "lingshan":    "庄严的灵山大佛与禅意广场",
    "nihuawan":    "拈花湾禅意小镇的唐风街巷",
    "xihu":        "西湖烟雨与断桥远景",
    "huangshan":   "黄山云海与奇松",
    "gugong":      "故宫红墙金瓦的宫廷",
    "zhangjiajie": "张家界石英砂岩峰林",
    "bingmayong":  "兵马俑军阵展厅",
    "mogaoku":     "敦煌莫高窟与鸣沙山",
}


class GenerateAvatarIn(BaseModel):
    prompt:    str = ""
    scenic_id: str = "lingshan"
    gender:    str = "female"     # female / male
    style:     str = "现代"       # 现代 / 古风 / 民族
    name:      str | None = None


@router.post("/generate")
def generate_avatar(body: GenerateAvatarIn):
    """AI 定制：万相在线生成「人景一体」半身像 → 落 ditto_avatars 双比例 → 即时入库可热切。"""
    if not _DITTO_DIR:
        raise HTTPException(status_code=503,
                            detail="本机无 Ditto 形象目录，AI 定制需在 GPU 部署机执行")
    try:
        import httpx
        import dashscope
        from dashscope import ImageSynthesis
        from io import BytesIO
        from PIL import Image
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"生成依赖缺失: {e}")

    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(k, None)
    key = os.environ.get("DASHSCOPE_API_KEY") or getattr(settings, "dashscope_api_key", "")
    if not key:
        raise HTTPException(status_code=500, detail="未配置 DASHSCOPE_API_KEY")
    dashscope.api_key = key

    scene = _SCENIC_SCENE.get(body.scenic_id, "中国著名景区")
    gz = "女性" if body.gender == "female" else "男性"
    extra = (body.prompt or "").strip()
    full = (f"一位{gz}景区导览讲解员，{extra + '，' if extra else ''}{body.style}气质，"
            f"职业得体着装，面带亲切微笑，正面看向镜头，半身构图居中，"
            f"站在{scene}前，真实人像摄影，柔和自然光，高清写实，画面只有一个人")
    neg = "多人,合影,卡通,动漫,3D,扭曲,变形,多手,多脸,残肢,模糊,低质量,文字,水印,丑陋,恐怖,过曝"

    aid = "custom_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    seed = int(datetime.now().timestamp()) % 2147483647
    # 万相高分生图(size) → 落盘缩到**直播流分辨率**(w,h)：热切底板必须与流同分辨率，
    # 否则 Ditto putback 撕裂/过曝（main 360p A/V 同步流；portrait 720×1280 竖版流）。
    specs = [("16x9", "1280*720", 640, 360), ("9x16", "720*1280", 720, 1280)]
    portrait_im = None
    with httpx.Client(timeout=90, trust_env=False) as cli:
        for asp, size, w, h in specs:
            resp = ImageSynthesis.call(model="wanx2.1-t2i-turbo", prompt=full,
                                       negative_prompt=neg, n=1, size=size, seed=seed,
                                       style="<photography>")
            if resp.status_code != 200:
                raise HTTPException(status_code=502,
                                    detail=f"万相生成失败: {resp.code} - {resp.message}")
            url = resp.output.results[0].url
            im = Image.open(BytesIO(cli.get(url).content)).convert("RGB")
            if im.size != (w, h):
                im = im.resize((w, h), Image.LANCZOS)
            # ⚠️ 禁用自动居中（2026-07-12）：实测水平平移过的底图会让 Ditto 嘴部驱动
            # 错位、唇形压塌成一条线（275 张存量图已全量回滚原图）。居中改由生图
            # prompt 约束（居中构图）承担，落盘一律用原图。
            # im = _recenter_person(im)
            im.save(os.path.join(_DITTO_DIR, f"{aid}__{body.scenic_id}__{asp}.png"))
            if asp == "9x16":
                portrait_im = im

    # 预览（缩略 9:16）
    _CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    prev = portrait_im.copy()
    prev.thumbnail((360, 640), Image.LANCZOS)
    prev.save(_CUSTOM_DIR / f"{aid}.jpg", quality=85)

    item = {
        "id": aid, "name": (body.name or "我的专属向导").strip()[:16],
        "gender": body.gender, "style": body.style,
        "persona": "AI 定制", "outfit": (extra[:12] or "定制造型"),
        "age": "青年", "fit": "AI 定制 · 即时生效",
        "preview": f"/rag/digital-human/avatar-preview/{aid}",
        "recommended": True, "custom": True,
    }
    items = _load_custom(); items.insert(0, item); _save_custom(items)
    return {"ok": True, "scenic_id": body.scenic_id, "avatar": {**item, "ready": True}}


# ── 甜美女性默认形象·万相候选批（供用户挑选 → 体检 → 采用为各游客端默认）────────
#   与 AI 定制同管线，但：①专为「甜美女性」基调 ②强制居中构图 + 排除背景人形剪影
#   ③落 staging 暂存目录（未体检不进 ditto_avatars）④每张只校验居中偏差不平移。
_CAND_DIR: Path = settings.vector_store_dir.parent / "avatar_candidates_staging"
_CAND_JSON: Path = _CAND_DIR / "candidates.json"
# 生成进度（内存态，轮询用）：running / target / done / error / scenic_id
_CAND_STATE: dict = {"running": False, "target": 0, "done": 0,
                     "error": None, "scenic_id": ""}


def _load_candidates() -> list[dict]:
    if _CAND_JSON.is_file():
        try:
            return json.loads(_CAND_JSON.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            return []
    return []


def _save_candidates(items: list[dict]) -> None:
    _CAND_DIR.mkdir(parents=True, exist_ok=True)
    _CAND_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")


# 候选专用场景：**刻意避开任何雕像/大佛/人形地标**（灵山场景原描述含"灵山大佛"=唇形毒源），
# 改用无人形的禅意园林/建筑虚化背景，塔影可留、佛像/人像不留。
_CAND_SCENE = {
    "lingshan":    "禅意园林的绿意亭台与虚化远塔",
    "nihuawan":    "拈花湾唐风街巷的木构廊檐",
    "xihu":        "西湖柳堤与虚化湖光",
    "gugong":      "故宫红墙与虚化宫廷回廊",
    "mogaoku":     "敦煌鸣沙山金色沙丘",
    "zhangjiajie": "张家界峰林云雾",
    "bingmayong":  "陈列展厅的暖光墙面",
}


def _sweet_candidate_prompt(scenic_id: str, extra: str) -> tuple[str, str]:
    # 复刻用户认可的母版 dh_lingshan/sweet_bob 审美（scripts/gen_sweet_bob_16x9.py 原 prompt，
    # wanx2.1-t2i-plus 产出）：瓜子脸尖下巴减龄童颜、超高颜值、齐肩内扣波波头、米白高领针织、
    # 中景半身镜头拉远=人物占比偏小。背景改为灵山禅意园林+远塔（体现景区，但排除大佛/人形剪影守唇形）。
    scenic_bg = {
        "lingshan":    "虚化的灵山胜境禅意园林、绿树与远处虚化的宝塔飞檐",
        "nihuawan":    "虚化的拈花湾唐风街巷木构廊檐与绿意",
        "xihu":        "虚化的西湖柳堤湖光",
        "gugong":      "虚化的故宫红墙宫廷回廊",
        "mogaoku":     "虚化的敦煌鸣沙山金色沙丘",
        "zhangjiajie": "虚化的张家界峰林云雾",
        "bingmayong":  "虚化的展厅暖光墙面",
    }.get(scenic_id, "虚化的中式园林绿意")
    full = (
        "一位甜美清纯的年轻女性景区讲解员，正好20岁的成年女大学生，气质甜美年轻但是成年人不是小孩，"
        "精致漂亮的瓜子脸，小巧的尖下巴，流畅匀称的脸部线条，饱满的苹果肌带来甜美减龄童颜感，"
        "明亮灵动的水汪汪大眼睛，小巧精致的鼻子，水润的唇，皮肤白皙嫩滑，"
        "超高颜值，沉鱼落雁闭月羞花般的绝世美貌，甜美清纯惹人喜爱，邻家姐姐般温柔亲和，"
        + (extra + "，" if extra else "") +
        "齐肩内扣短发波波头，完整露出全部头发不被裁切，"
        "穿米白色浅色高领针织毛衣，毛衣完整覆盖双肩和手臂，端庄保守不露肩不露肤，"
        "完全正面面对镜头，脸正对镜头端端正正，不侧脸不歪头不低头，双眼平视镜头，"
        "甜甜的浅浅微笑，弯弯的笑眼，亲切温和，不露齿不夸张，"
        "发型简洁自然，完整露出全部头发，头顶留有充足空间不被裁切，"
        "整个头部和全部头发都完整在画面内，头顶上方留有明显空白，绝不裁切到头发或头顶，"
        "中景半身像，完整露出上半身到腰部，镜头适当拉远，人物在画面中占比适中偏小，自然真实的头身比例不显头大，"
        f"柔和自然光，人物清晰在前、背景大幅虚化，背景是{scenic_bg}，"
        "背景里绝对没有任何人物、佛像、雕像、人影，超写实人像摄影，电影质感，8k"
    )
    # 唇形健康铁律：背景排除一切人形/佛像/面孔剪影；姿态守正脸；服饰排除露肩/旗袍；脸型排除圆脸
    neg = ("露肩,挖肩装,一字肩,露肩装,漏肩,镂空装,吊带,露肤,深色衣服,旗袍,唐装,立领,中式盘扣,"
           "头发被裁切,头顶被切,侧脸,歪头,低头,大头,头大,圆脸,肉脸,婴儿肥,大饼脸,方脸,双下巴,"
           "浓妆,整容脸,网红脸,丑,模糊,低质量,低龄儿童,小孩,老气,显老,"
           "多人,合影,背景人物,人群,人影,剪影,雕像,雕像人形,佛像,大佛,神像,人像画,文字,水印,过曝")
    return full, neg


def _gen_one_candidate(scenic_id: str, extra: str, idx: int) -> dict | None:
    """生成一张甜美候选（同 seed 16:9 + 9:16 成对，落 staging，只校验居中）。失败返回 None。"""
    import httpx
    import dashscope
    from dashscope import ImageSynthesis
    from io import BytesIO
    from PIL import Image

    full, neg = _sweet_candidate_prompt(scenic_id, extra)
    cid = f"cand_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}"
    # 每张不同 seed 出不同人；同一张的两个比例共用一个 seed 保证同人
    seed = (int(datetime.now().timestamp()) * 131 + idx * 97) % 2147483647
    specs = [("16x9", "1280*720", 640, 360), ("9x16", "720*1280", 720, 1280)]
    _CAND_DIR.mkdir(parents=True, exist_ok=True)
    portrait_im = None
    with httpx.Client(timeout=120, trust_env=False) as cli:
        for asp, size, w, h in specs:
            # 用 -plus（非 -turbo）：母版 dh_lingshan 即 -plus 产出，颜值/质感明显更好
            resp = ImageSynthesis.call(model="wanx2.1-t2i-plus", prompt=full,
                                       negative_prompt=neg, n=1, size=size, seed=seed)
            if resp.status_code != 200:
                raise RuntimeError(f"万相失败: {resp.code} - {resp.message}")
            url = resp.output.results[0].url
            im = Image.open(BytesIO(cli.get(url).content)).convert("RGB")
            if im.size != (w, h):
                im = im.resize((w, h), Image.LANCZOS)
            # ⚠️ 只落原图，绝不平移（平移=唇形坍缩根因），居中靠 prompt 约束 + 事后校验淘汰
            im.save(_CAND_DIR / f"{cid}__{scenic_id}__{asp}.png")
            if asp == "9x16":
                portrait_im = im
    # 只校验竖版（大屏主用）居中
    offset_pct, centered = _face_center_offset(portrait_im)
    prev = portrait_im.copy()
    prev.thumbnail((360, 640), Image.LANCZOS)
    prev.save(_CAND_DIR / f"{cid}.jpg", quality=85)
    return {
        "cand_id": cid, "scenic_id": scenic_id, "seed": seed,
        "center_offset_pct": offset_pct, "centered": bool(centered),
        "preview": f"/rag/digital-human/candidate-preview/{cid}",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _run_candidates_bg(scenic_id: str, count: int, prompt: str) -> None:
    _CAND_STATE.update(running=True, target=count, done=0, error=None, scenic_id=scenic_id)
    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(k, None)
    try:
        import dashscope
        key = os.environ.get("DASHSCOPE_API_KEY") or getattr(settings, "dashscope_api_key", "")
        dashscope.api_key = key
        for i in range(count):
            try:
                item = _gen_one_candidate(scenic_id, prompt, i)
                if item:
                    items = _load_candidates()
                    items.insert(0, item)
                    _save_candidates(items)
                    _CAND_STATE["done"] += 1
            except Exception as e:  # noqa: BLE001 单张失败跳过不炸批
                _CAND_STATE["error"] = str(e)[:200]
    finally:
        _CAND_STATE["running"] = False


class GenCandidatesIn(BaseModel):
    scenic_id: str = "lingshan"
    count:     int = 6
    prompt:    str = ""


@router.post("/generate-candidates")
def generate_candidates(body: GenCandidatesIn, background_tasks: BackgroundTasks):
    """批量生成甜美女性候选（后台任务，立即返回 started；轮询 GET /candidates）。"""
    if _CAND_STATE["running"]:
        raise HTTPException(status_code=409, detail="已有候选生成任务在进行中")
    key = os.environ.get("DASHSCOPE_API_KEY") or getattr(settings, "dashscope_api_key", "")
    if not key:
        raise HTTPException(status_code=500, detail="未配置 DASHSCOPE_API_KEY")
    count = max(1, min(int(body.count or 6), 8))
    background_tasks.add_task(_run_candidates_bg, body.scenic_id, count, (body.prompt or "").strip())
    return {"ok": True, "started": True, "target": count, "scenic_id": body.scenic_id}


@router.get("/candidates")
def list_candidates():
    """候选列表 + 生成进度。"""
    return {"candidates": _load_candidates(), "progress": dict(_CAND_STATE)}


@router.get("/candidate-preview/{cid}")
def candidate_preview(cid: str, asp: str = ""):
    """候选预览图（asp 空=缩略 jpg；asp=16x9/9x16 → 原比例 png）。"""
    if "/" in cid or "\\" in cid or ".." in cid:
        raise HTTPException(status_code=400, detail="非法 cand_id")
    if asp in ("16x9", "9x16"):
        matches = sorted(_CAND_DIR.glob(f"{cid}__*__{asp}.png"))
        if matches:
            return FileResponse(str(matches[0]), media_type="image/png")
    p = _CAND_DIR / f"{cid}.jpg"
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"候选不存在: {cid}")
    return FileResponse(str(p), media_type="image/jpeg")


class AdoptCandidateIn(BaseModel):
    name:       str | None = None
    stage_name: str | None = None


@router.post("/candidates/{cid}/adopt")
def adopt_candidate(cid: str, body: AdoptCandidateIn):
    """采用候选为可驱动形象：拒未居中 → 复制双比例进 ditto_avatars + 写 custom + 艺名。
    不写 config——设为景区默认是独立显式动作。"""
    if not _DITTO_DIR:
        raise HTTPException(status_code=503, detail="本机无 Ditto 形象目录，采用需在 GPU 部署机执行")
    if "/" in cid or "\\" in cid or ".." in cid:
        raise HTTPException(status_code=400, detail="非法 cand_id")
    cand = next((c for c in _load_candidates() if c["cand_id"] == cid), None)
    if not cand:
        raise HTTPException(status_code=404, detail=f"候选不存在: {cid}")
    if not cand.get("centered", True):
        raise HTTPException(status_code=400,
                            detail=f"该候选人物未居中（偏差 {cand.get('center_offset_pct')}%），"
                                   f"请挑选居中的候选，避免播放裁切偏移")
    import shutil
    scenic = cand["scenic_id"]
    aid = "custom_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    copied = 0
    for asp in ("16x9", "9x16"):
        src = sorted(_CAND_DIR.glob(f"{cid}__*__{asp}.png"))
        if src:
            shutil.copyfile(str(src[0]), os.path.join(_DITTO_DIR, f"{aid}__{scenic}__{asp}.png"))
            copied += 1
    if copied == 0:
        raise HTTPException(status_code=404, detail="候选底图缺失，无法采用")
    # 预览：复制候选缩略图到 custom 目录
    _CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    prev_src = _CAND_DIR / f"{cid}.jpg"
    if prev_src.is_file():
        shutil.copyfile(str(prev_src), str(_CUSTOM_DIR / f"{aid}.jpg"))
    nm = (body.name or "甜美导览专员").strip()[:16]
    item = {
        "id": aid, "name": nm, "gender": "female", "style": "现代",
        "persona": "亲和甜美", "outfit": "浅色职业装", "age": "青年",
        "fit": "AI 甜美默认 · 即时生效",
        "preview": f"/rag/digital-human/avatar-preview/{aid}",
        "recommended": True, "custom": True,
    }
    items = _load_custom(); items.insert(0, item); _save_custom(items)
    # 写艺名（若指定）
    stage = None
    if body.stage_name and body.stage_name.strip():
        stage = _clean_stage_name(body.stage_name)
    if stage:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO dh_avatar_meta (avatar_id, stage_name, welcome_text, updated_at)
                   VALUES (?, ?, '', strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
                   ON CONFLICT(avatar_id) DO UPDATE SET
                     stage_name=excluded.stage_name, updated_at=excluded.updated_at""",
                (aid, stage))
    return {"ok": True, "avatar": {**item, "ready": True}, "stage_name": stage}


# 静态形象缩略图目录（webapp 源/构建产物），供跨域绝对 URL 回退取图
_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC_AVATAR_DIRS = [
    _REPO_ROOT / "webapp" / "public" / "avatars",
    _REPO_ROOT / "webapp" / "dist" / "avatars",
]


@router.get("/avatar-preview/{aid}")
def avatar_preview(aid: str):
    """形象预览图（绝对 URL 引用，跨前端/跨域可达）。
    先查 AI 定制目录；非定制形象回退到 webapp 静态缩略图（dh_<scenic> 等上景形象走这条）。"""
    p = _CUSTOM_DIR / f"{aid}.jpg"
    if not p.is_file():
        for d in _STATIC_AVATAR_DIRS:
            cand = d / f"{aid}.jpg"
            if cand.is_file():
                p = cand
                break
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"预览不存在: {aid}")
    return FileResponse(str(p), media_type="image/jpeg")
