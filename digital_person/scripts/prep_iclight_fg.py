"""为 IC-Light fbc 准备前景图：sweet_bob 抠像放到 1280×720 中性灰底上（中景半身、居中）。
IC-Light 用「前景=灰底主体 + 背景=场景」做背景条件重打光，输出=主体按场景光照重打光并融入。
foreground 必须是确定的 sweet_bob 本人（保身份），只让 IC-Light 改光照、融边。
用法：.venv/bin/python scripts/prep_iclight_fg.py [person_h=1.05] [top=0.06]
"""
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PORTRAIT = Path.home() / "Desktop/LiveTalking/data/ditto_avatars/sweet_bob_ditto.png"
MASK = ROOT / "assets/avatar_backgrounds/masks/sweet_bob_ditto.birefnet-portrait.png"
COMFY_IN = Path.home() / "Desktop/ComfyUI/input"
LS_W, LS_H = 1280, 720
GREY = 127

person_h = float(sys.argv[1]) if len(sys.argv) > 1 else 1.05
top = float(sys.argv[2]) if len(sys.argv) > 2 else 0.06

pr = np.asarray(Image.open(PORTRAIT).convert("RGB"))
mask = cv2.imread(str(MASK), cv2.IMREAD_GRAYSCALE)
if mask.shape[:2] != pr.shape[:2]:
    mask = cv2.resize(mask, (pr.shape[1], pr.shape[0]))

ys, xs = np.where(mask > 96)
y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
pc, pm = pr[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]

th = max(1, int(person_h * LS_H))
sc = th / pc.shape[0]
tw = max(1, int(pc.shape[1] * sc))
pc_r = cv2.resize(pc, (tw, th), interpolation=cv2.INTER_LANCZOS4)
pm_r = cv2.resize(pm, (tw, th), interpolation=cv2.INTER_LANCZOS4)

canvas = np.full((LS_H, LS_W, 3), GREY, np.uint8)
px, py = int(0.5 * LS_W - tw / 2), int(top * LS_H)
sx0, sy0 = max(0, -px), max(0, -py)
dx0, dy0 = max(0, px), max(0, py)
dx1, dy1 = min(LS_W, px + tw), min(LS_H, py + th)
cw, ch = dx1 - dx0, dy1 - dy0
a = (pm_r[sy0:sy0 + ch, sx0:sx0 + cw].astype(np.float32) / 255.0)[..., None]
canvas[dy0:dy1, dx0:dx1] = (pc_r[sy0:sy0 + ch, sx0:sx0 + cw] * a +
                            canvas[dy0:dy1, dx0:dx1] * (1 - a)).astype(np.uint8)

COMFY_IN.mkdir(parents=True, exist_ok=True)
out = COMFY_IN / "iclight_fg.png"
Image.fromarray(canvas).save(out)
print(f"✅ 前景(灰底主体) {out}  人物 {tw}x{th} @ top{top}")

# 背景：复用已生成的灵山横版景区图 → 也放进 ComfyUI/input
bg_src = ROOT / "assets/avatar_backgrounds/lsbg_lingshan.png"
if bg_src.exists():
    Image.open(bg_src).convert("RGB").resize((LS_W, LS_H), Image.LANCZOS).save(COMFY_IN / "iclight_bg_lingshan.png")
    print(f"✅ 背景 {COMFY_IN / 'iclight_bg_lingshan.png'}")
