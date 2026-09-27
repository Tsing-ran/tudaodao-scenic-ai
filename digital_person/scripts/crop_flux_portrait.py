"""把 Flux Kontext 竖版上景成品（如 752×1392）裁成 9:16 直播底板 720×1280。
竖版构图本就是半身站姿，无需 rembg——只做 9:16 等比裁切（多余从顶部天空裁，保头部留白+身体）+ 重采样。
用法: crop_flux_portrait.py <in.png> <out.png>
"""
import sys
from PIL import Image

IN, OUT = sys.argv[1], sys.argv[2]
TW, TH = 720, 1280                       # 目标 9:16
target_ar = TW / TH

im = Image.open(IN).convert("RGB")
W, H = im.size
ar = W / H
if ar > target_ar:                       # 太宽 → 裁两侧（居中）
    cw = int(H * target_ar)
    x0 = (W - cw) // 2
    box = (x0, 0, x0 + cw, H)
else:                                     # 太高 → 裁上下，偏向从顶部多裁（去多余天空，保身体）
    ch = int(W / target_ar)
    top = int((H - ch) * 0.62)           # 62% 从顶部裁、38% 从底部 → 头顶留白适中、保留身体
    box = (0, top, W, top + ch)
crop = im.crop(box).resize((TW, TH), Image.LANCZOS)
crop.save(OUT)
print(f"{OUT}  src={W}x{H} ar={ar:.3f} crop={box} -> {TW}x{TH}")
