"""把 sweet_bob 原图摆进 16:9 框：保原脸不动，舒服的大小/头位 + 空灵柔光底。
放弃了可切换景区背景——背景只做干净空灵的柔光渐变+辉光，等于一张干净人像，无"贴场景"问题。
纯 CPU。用法：.venv/bin/python scripts/gen_avatar_clean16x9.py [person_h=1.22] [top=0.07] [xc=0.5]
"""
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PORTRAIT = Path.home() / "Desktop/LiveTalking/data/ditto_avatars/sweet_bob_ditto.png"
MASK = ROOT / "assets/avatar_backgrounds/masks/sweet_bob_ditto.birefnet-portrait.png"
DITTO_DIR = Path.home() / "Desktop/LiveTalking/data/ditto_avatars"
REVIEW = ROOT / "assets/ui_shots"
W, H = 1280, 720

person_h = float(sys.argv[1]) if len(sys.argv) > 1 else 1.22   # 人物高/画高（>1=下部裁，近景）
top = float(sys.argv[2]) if len(sys.argv) > 2 else 0.07        # 头顶距上边（留头顶空间）
xc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5


def ethereal_bg(cx, cy):
    """空灵柔光底：柔和浅色垂直渐变 + 人物身后径向暖辉光。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vgrad = 1.0 - 0.14 * (yy / H)                               # 顶部稍亮、底部略沉
    d = np.sqrt(((xx - cx) / (W * 0.50)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    glow = np.clip(1.0 - d, 0, 1) ** 1.6                        # 身后柔辉光
    base = np.array([232, 235, 240], np.float32)               # 冷白柔灰
    warm = np.array([247, 242, 234], np.float32)               # 暖白辉光（衬肤色）
    bg = base[None, None, :] * vgrad[..., None]
    bg = bg * (1 - 0.40 * glow[..., None]) + warm[None, None, :] * (0.40 * glow[..., None])
    return bg.clip(0, 255).astype(np.uint8)


pr = np.asarray(Image.open(PORTRAIT).convert("RGB"))
mask = cv2.imread(str(MASK), cv2.IMREAD_GRAYSCALE)
if mask.shape[:2] != pr.shape[:2]:
    mask = cv2.resize(mask, (pr.shape[1], pr.shape[0]))

ys, xs = np.where(mask > 96)
y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
pc, pm = pr[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]

th = max(1, int(person_h * H))
sc = th / pc.shape[0]
tw = max(1, int(pc.shape[1] * sc))
pc_r = cv2.resize(pc, (tw, th), interpolation=cv2.INTER_LANCZOS4)
pm_r = cv2.resize(pm, (tw, th), interpolation=cv2.INTER_LANCZOS4)

px, py = int(xc * W - tw / 2), int(top * H)
# 人物中心（身后辉光对齐）
bg = ethereal_bg(px + tw / 2, py + th * 0.42)

sx0, sy0 = max(0, -px), max(0, -py)
dx0, dy0 = max(0, px), max(0, py)
dx1, dy1 = min(W, px + tw), min(H, py + th)
cw, ch = dx1 - dx0, dy1 - dy0
cm = np.zeros((H, W), np.uint8); cp = np.zeros((H, W, 3), np.uint8)
cm[dy0:dy1, dx0:dx1] = pm_r[sy0:sy0 + ch, sx0:sx0 + cw]
cp[dy0:dy1, dx0:dx1] = pc_r[sy0:sy0 + ch, sx0:sx0 + cw]

alpha = cv2.GaussianBlur(cm.astype(np.float32) / 255.0, (0, 0), 1.5)[..., None]  # 轻羽化，底色近肤色背景无贴感
out = (cp * alpha + bg * (1 - alpha)).clip(0, 255).astype(np.uint8)

REVIEW.mkdir(parents=True, exist_ok=True)
Image.fromarray(out).save(REVIEW / "clean16x9.png")
Image.fromarray(out).save(DITTO_DIR / "sweet_bob_clean.png")
print(f"✅ {REVIEW / 'clean16x9.png'}  人物 {tw}x{th} @ top{top} xc{xc}")
print(f"✅ Ditto 底板 sweet_bob_clean")
