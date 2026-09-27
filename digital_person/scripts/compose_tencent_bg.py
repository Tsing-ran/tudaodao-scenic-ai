"""腾讯会议式虚拟背景：rembg 精细抠 sweet_bob → 叠到完整 16:9 场景背景上（完整头、软边自然）。

用法：compose_tencent_bg.py <人物竖版png> <背景16x9png> <输出png> [人物高占比=0.96] [头顶余量px=40]
  人物高占比 >1 = 人物比画面高（胸口在底部自然裁切，更近景）；头顶余量大 = 人物整体下移。
"""
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from rembg import new_session, remove

PERSON = sys.argv[1]
BG = sys.argv[2]
OUT = sys.argv[3]
PERSON_H = float(sys.argv[4]) if len(sys.argv) > 4 else 0.96
TOP_MARGIN = int(sys.argv[5]) if len(sys.argv) > 5 else 40
# 输出比例：16:9 给 1280 720；9:16 给 720 1280（compose 自动按此布局人物+背景）
W = int(sys.argv[7]) if len(sys.argv) > 7 else 1280
H = int(sys.argv[8]) if len(sys.argv) > 8 else 720

# 1) 抠像（birefnet-portrait，发丝边好）
src = Image.open(PERSON).convert("RGB")
arr = np.array(src)
mask = np.array(remove(arr, session=new_session("birefnet-portrait"), only_mask=True))
ys, xs = np.where(mask > 25)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
person = src.crop((x0, y0, x1 + 1, y1 + 1))
pm = Image.fromarray(mask).crop((x0, y0, x1 + 1, y1 + 1))

# 2) 缩放：人物高 = PERSON_H*H（可 >1，胸口底部裁切）；按头顶余量 TOP_MARGIN 定位（越大越下移）
th = int(H * PERSON_H)
tw = int(person.width * th / person.height)
person = person.resize((tw, th), Image.LANCZOS)
pm = pm.resize((tw, th), Image.LANCZOS)
px = (W - tw) // 2
py = TOP_MARGIN          # 头顶留 TOP_MARGIN，底部超出画面则自然裁切

# 3) 背景 fit-cover 到 16:9
bg = Image.open(BG).convert("RGB")
bw = W; bh = int(bg.height * W / bg.width)
if bh < H: bh = H; bw = int(bg.width * H / bg.height)
bg = bg.resize((bw, bh), Image.LANCZOS)
bg = bg.crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))

# 4) 轻度色调匹配：把人物整体往背景的色温拉一点点（融入感，避免"贴上去"）
p = np.array(person).astype(np.float32)
pmask_np = (np.array(pm).astype(np.float32) / 255.0)[..., None]
bg_np = np.array(bg).astype(np.float32)
bg_mean = bg_np.reshape(-1, 3).mean(0)
p_mean = (p * pmask_np).reshape(-1, 3).sum(0) / (pmask_np.sum() + 1e-6)
p = np.clip(p + (bg_mean - p_mean) * 0.12, 0, 255)   # 12% 往背景色温靠
person = Image.fromarray(p.astype(np.uint8))

# 5) 软边合成：先轻微收缩抠像(去掉原背景渗色光晕)，再较大羽化 → 边缘与新背景自然过渡
FEATHER_SIGMA = float(sys.argv[6]) if len(sys.argv) > 6 else 2.8
m = np.array(pm).astype(np.float32) / 255.0
m = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=1)     # 收缩 ~1px，去原 misty 背景光晕
alpha = cv2.GaussianBlur(m, (0, 0), FEATHER_SIGMA)            # 大羽化软过渡
alpha = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
canvas = bg.copy()
canvas.paste(person, (px, py), alpha)

canvas.save(OUT)
print(f"✅ 腾讯会议式 16:9: {OUT}  人物 {tw}x{th} @ ({px},{py})")
