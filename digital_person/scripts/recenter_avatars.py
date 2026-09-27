# 形象底图人物水平重居中：人脸检测→取最大脸中心→水平平移到画面正中（BORDER_REFLECT 补边）
# 用法: python recenter_avatars.py <dir> [--apply]   不带 --apply 只打印诊断不落盘
import sys, os, glob
import cv2
import numpy as np

d = sys.argv[1]
apply = "--apply" in sys.argv
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def face_center_x(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5,
                                     minSize=(img.shape[0] // 10, img.shape[0] // 10))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])   # 取最大脸
    return x + w / 2.0

n_shift = n_skip = n_noface = 0
for p in sorted(glob.glob(os.path.join(d, "*.png"))):
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is None:
        continue
    bgr = img[:, :, :3] if img.shape[2] == 4 else img
    cx = face_center_x(bgr)
    name = os.path.basename(p)
    if cx is None:
        print(f"NOFACE  {name}")
        n_noface += 1
        continue
    H, W = img.shape[:2]
    dx = round(W / 2.0 - cx)
    if abs(dx) <= max(2, W * 0.008):        # 偏差 <0.8% 视为已居中
        print(f"OK      {name}  dx={dx}")
        n_skip += 1
        continue
    print(f"SHIFT   {name}  dx={dx}  ({W}x{H})")
    n_shift += 1
    if apply:
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REFLECT)
        cv2.imwrite(p, out)

print(f"\nshift={n_shift} ok={n_skip} noface={n_noface} apply={apply}")
