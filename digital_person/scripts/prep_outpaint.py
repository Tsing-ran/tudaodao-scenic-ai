"""为 outpaint 补全肩臂准备：原图 sweet_bob 摆进 1280×720 空灵画布 + 遮罩。
保留她脸/中央躯干(不变)，遮罩待补全区 = 她外缘(被切的肩臂)+周围背景 → 模型补完整肩臂+空灵底。
用法：.venv/bin/python scripts/prep_outpaint.py [person_h=1.15] [top=0.06]
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
W, H = 1280, 720

person_h = float(sys.argv[1]) if len(sys.argv) > 1 else 1.15
top = float(sys.argv[2]) if len(sys.argv) > 2 else 0.06

pr = np.asarray(Image.open(PORTRAIT).convert("RGB"))
mask = cv2.imread(str(MASK), cv2.IMREAD_GRAYSCALE)
if mask.shape[:2] != pr.shape[:2]:
    mask = cv2.resize(mask, (pr.shape[1], pr.shape[0]))

ys, xs = np.where(mask > 96)
y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
pc, pm = pr[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]

th = max(1, int(person_h * H)); sc = th / pc.shape[0]; tw = max(1, int(pc.shape[1] * sc))
pc_r = cv2.resize(pc, (tw, th), interpolation=cv2.INTER_LANCZOS4)
pm_r = cv2.resize(pm, (tw, th), interpolation=cv2.INTER_LANCZOS4)

# 空灵底画布
canvas = np.full((H, W, 3), 234, np.uint8)
px, py = int(0.5 * W - tw / 2), int(top * H)
sx0, sy0 = max(0, -px), max(0, -py)
dx0, dy0 = max(0, px), max(0, py)
dx1, dy1 = min(W, px + tw), min(H, py + th)
cw, ch = dx1 - dx0, dy1 - dy0
cm = np.zeros((H, W), np.uint8); cp = np.zeros((H, W, 3), np.uint8)
cm[dy0:dy1, dx0:dx1] = pm_r[sy0:sy0 + ch, sx0:sx0 + cw]
cp[dy0:dy1, dx0:dx1] = pc_r[sy0:sy0 + ch, sx0:sx0 + cw]
a = (cm.astype(np.float32) / 255.0)[..., None]
canvas = (cp * a + canvas * (1 - a)).astype(np.uint8)

# 遮罩（白=待生成）：上半身(发/脸/肩)完全保留不腐蚀；只在下部被切肩臂区腐蚀补全 + 背景。
keep = (cm > 128).astype(np.uint8) * 255
keep_e = keep.copy()                                  # 默认全保留(她不动)
yb = int(0.56 * H)                                    # 这条线以下=被切肩臂区
extra = cv2.erode(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81)))  # 仅下部腐蚀 ~40px
keep_e[yb:] = extra[yb:]
gen = 255 - keep_e                                    # 白=生成(背景 + 下部肩臂补全带)
gen = cv2.GaussianBlur(gen, (0, 0), 5)                # 软边过渡

COMFY_IN.mkdir(parents=True, exist_ok=True)
Image.fromarray(canvas).save(COMFY_IN / "outpaint_canvas.png")
Image.fromarray(gen).save(COMFY_IN / "outpaint_mask.png")
print(f"✅ 画布 {COMFY_IN/'outpaint_canvas.png'}  人物 {tw}x{th}")
print(f"✅ 遮罩 {COMFY_IN/'outpaint_mask.png'}（白=补全肩臂+背景）")
