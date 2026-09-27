"""把竖版 Ditto 底图(720x1280, sweet_bob+景区背景)重取景为 16:9(1280x720)完整头。

保留「人物+近景整块锐利」(用户认可的取景、人不变窄)，只把中间块到两侧模糊背景的硬边
**宽羽化渐变**掉 → 自然景深 falloff、无接缝。不抠像、不重新生成、零身份风险。
用法：.venv/bin/python scripts/reframe_16x9.py <竖版png> <输出png> [人物块高=760] [羽化px=180]
"""
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

SRC = sys.argv[1]
OUT = sys.argv[2]
BLOCK_H = int(sys.argv[3]) if len(sys.argv) > 3 else 760   # 从竖图顶部取多高(含头肩到胸)
FEATHER = int(sys.argv[4]) if len(sys.argv) > 4 else 180   # 中间块向两侧羽化宽度
W, H = 1280, 720

img = Image.open(SRC).convert("RGB")

# 1) 统一柔焦背景：同图 fit-cover 到 16:9，整张重模糊（无中心/侧边之分）
bg_fit = img.resize((W, int(W * img.height / img.width)), Image.LANCZOS)
top = max(0, (bg_fit.height - H) // 2)
bg = np.array(bg_fit.crop((0, top, W, top + H))).astype(np.float32)
bg = cv2.GaussianBlur(bg, (0, 0), 24)
bg = np.clip(bg * 1.04 + 5, 0, 255)

# 2) 中间锐利块：竖图顶部 BLOCK_H(头肩到胸，完整头) 缩到画布高、居中
block = img.crop((0, 0, img.width, BLOCK_H))
bh = H
bw = int(block.width * bh / block.height)
block = np.array(block.resize((bw, bh), Image.LANCZOS)).astype(np.float32)
bx = (W - bw) // 2

# 3) 把中间块贴到背景同位置，alpha = 中间 1、左右各 FEATHER 内余弦渐变到 0
layer = bg.copy()
layer[:, bx:bx + bw] = block
alpha = np.zeros((W,), np.float32)
alpha[bx:bx + bw] = 1.0
for i in range(FEATHER):
    t = 0.5 - 0.5 * np.cos(np.pi * i / FEATHER)      # 0→1 余弦渐变
    if bx + i < W:           alpha[bx + i] = t        # 左边内缘渐入
    if bx + bw - 1 - i >= 0: alpha[bx + bw - 1 - i] = t  # 右边内缘渐出
a = alpha[None, :, None]
out = (layer * a + bg * (1 - a)).astype(np.uint8)

Image.fromarray(out).save(OUT)
print(f"✅ 16:9 完整头(羽化无接缝): {OUT}  中间块 {bw}px 居中 + 羽化 {FEATHER}px")
