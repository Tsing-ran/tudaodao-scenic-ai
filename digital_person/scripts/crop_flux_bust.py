"""把 Flux Kontext 上景成品（1392×752 等）裁成半身 640×360 直播底板。
裁切几何 = 灵山定版配方：rembg 检测发顶+肩线 → 头发完整(头顶留12%)、胸口截断(肩下0.18头颈)，
16:9 自动按头部水平居中（替代灵山专用的 cx 硬编码，适配各景区人物位置不同）。
用法: crop_flux_bust.py <in.png> <out.png>
"""
import sys
from PIL import Image
import numpy as np
import rembg

IN = sys.argv[1]
OUT = sys.argv[2]

im = Image.open(IN).convert("RGB")
W, H = im.size
a = np.asarray(rembg.remove(im, session=rembg.new_session("birefnet-portrait")))[..., 3] > 128
rw = a.sum(axis=1)                        # 每行人物宽度
ys = np.where(a.max(axis=1))[0]
hair_top = int(ys.min())
maxw = rw.max()
# 肩线 = 从上往下第一处宽度达到 0.82*max（肩开始张开）
shoulder_y = int(np.where(rw >= 0.82 * maxw)[0][0])
head_neck = max(1, shoulder_y - hair_top)
chest_y = int(shoulder_y + 0.18 * head_neck)        # 胸口=肩下一点
crop_top = max(0, int(hair_top - 0.12 * head_neck)) # 头顶留12%(发完整)
crop_h = chest_y - crop_top
crop_w = int(crop_h * 16 / 9)
# 头部水平中心：头区(发顶→肩)每列是否有人物 → 列均值，自动居中
head_band = a[hair_top:shoulder_y]
head_cols = np.where(head_band.any(axis=0))[0]
cx = int(head_cols.mean()) if len(head_cols) else W // 2
x0 = max(0, min(W - crop_w, cx - crop_w // 2))
crop = im.crop((x0, crop_top, x0 + crop_w, crop_top + crop_h)).resize((640, 360), Image.LANCZOS)
crop.save(OUT)
print(f"{OUT}  hair_top={hair_top} shoulder_y={shoulder_y} chest_y={chest_y} "
      f"crop=({x0},{crop_top},{crop_w}x{crop_h}) cx={cx} -> 640x360")
