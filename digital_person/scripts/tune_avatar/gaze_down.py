"""把肖像的眼神几何下移一点点（眼神预补偿）。
用途：EchoMimic 对参考图有"眼球上翻+略抬头"的一致性偏置 → 给它一张瞳孔略朝下的参考，
生成后正好落回"直视镜头"。纯 CPU（mediapipe 虹膜关键点），不占 GPU。
用法: gaze_down.py <in.png> <out.png> [delta_ratio=0.35]
  delta_ratio = 虹膜下移量 / 虹膜半径。0=不动；0.35≈轻微；0.6≈明显。
"""
import sys
import cv2
import numpy as np
import mediapipe as mp

IN = sys.argv[1]
OUT = sys.argv[2]
DELTA_RATIO = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35

# mediapipe 虹膜关键点（refine_landmarks=True）：右眼 468中心+469~472，左眼 473中心+474~477
IRIS = {"right": (468, [469, 470, 471, 472]), "left": (473, [474, 475, 476, 477])}

img = cv2.imread(IN)
h, w = img.shape[:2]
fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, refine_landmarks=True,
                                     max_num_faces=1, min_detection_confidence=0.5)
res = fm.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
if not res.multi_face_landmarks:
    sys.exit("❌ 未检测到人脸")
lm = res.multi_face_landmarks[0].landmark
out = img.copy()

for side, (c_idx, ring) in IRIS.items():
    cx, cy = lm[c_idx].x * w, lm[c_idx].y * h
    r = np.mean([np.hypot(lm[i].x * w - cx, lm[i].y * h - cy) for i in ring])
    R = int(r * 1.25)
    cx, cy = int(cx), int(cy)
    delta = int(r * DELTA_RATIO)

    # 1) 取原虹膜圆形 patch（含软边）
    mask = np.zeros((h, w), np.uint8)
    cv2.circle(mask, (cx, cy), R, 255, -1)
    mask_soft = cv2.GaussianBlur(mask, (0, 0), R * 0.15)

    # 2) 巩膜底色：取虹膜正上方一圈的浅色像素中位，把原虹膜位置擦成巩膜
    band = out[max(0, cy - R - 6):cy - R + 2, cx - R:cx + R]
    sclera = np.median(band.reshape(-1, 3), axis=0) if band.size else np.array([235, 235, 240])
    erase = (mask_soft.astype(np.float32) / 255)[..., None]
    out = (out * (1 - erase) + sclera[None, None, :] * erase).astype(np.uint8)

    # 3) 把虹膜 patch 贴到下移 delta 的位置（软边混合）
    iris_patch = img.copy()
    Md = np.float32([[1, 0, 0], [0, 1, delta]])
    iris_shift = cv2.warpAffine(iris_patch, Md, (w, h), borderMode=cv2.BORDER_REPLICATE)
    mask_shift = cv2.warpAffine(mask_soft, Md, (w, h))
    a = (mask_shift.astype(np.float32) / 255)[..., None]
    out = (out * (1 - a) + iris_shift * a).astype(np.uint8)

cv2.imwrite(OUT, out)
print(f"✅ 眼神下移 {DELTA_RATIO} → {OUT}")
