"""嘴部画质客观指标（自动调参闭环用）。
因每次用同一段固定音频驱动，真实嘴动逐帧一致 → 所有指标跨 run 可比，
无需分离"抖动 vs 真实运动"，只比 run 与 run 的差。
ROI 取自 sweet_bob coords.pkl：脸框[222,192,520,556]，接缝线 y≈410(upper_boundary=0.60)。
"""
import sys, glob, json
import cv2
import numpy as np

frames_dir = sys.argv[1]
# 嘴部带（脸框下 ~45%，MuseTalk 真正替换+张合区）
MX1, MY1, MX2, MY2 = 222, 400, 520, 560
# 脸框 & 接缝线（upper_boundary_ratio=0.60 → 下 40% 被替换，分界在 y≈410）
FX1, FX2, SEAM_Y = 222, 520, 410

imgs = sorted(glob.glob(frames_dir + "/*.png"))
sharp, clip, seam, tdiff = [], [], [], []
prev = None
for p in imgs:
    im = cv2.imread(p)
    if im is None:
        continue
    mouth = im[MY1:MY2, MX1:MX2]
    g = cv2.cvtColor(mouth, cv2.COLOR_BGR2GRAY)
    sharp.append(cv2.Laplacian(g, cv2.CV_64F).var())          # 锐度：高=清晰，低=糊
    clip.append(float(np.mean((g <= 2) | (g >= 253))))         # 过锐护栏：饱和像素占比
    band = cv2.cvtColor(im[SEAM_Y-3:SEAM_Y+3, FX1:FX2], cv2.COLOR_BGR2GRAY).astype(np.float64)
    seam.append(float(np.mean(np.abs(np.diff(band, axis=0)))))  # 接缝：边界纵向梯度能量
    if prev is not None and prev.shape == mouth.shape:
        tdiff.append(float(np.mean(cv2.absdiff(mouth, prev))))  # 帧间差：低=平滑(可能糊)，高=锐/抖
    prev = mouth

out = {
    "n": len(sharp),
    "sharpness": round(float(np.mean(sharp)), 1) if sharp else None,
    "clip_pct": round(float(np.mean(clip)) * 100, 3) if clip else None,
    "temporal_diff": round(float(np.mean(tdiff)), 3) if tdiff else None,
    "seam": round(float(np.mean(seam)), 3) if seam else None,
}
print(json.dumps(out, ensure_ascii=False))
