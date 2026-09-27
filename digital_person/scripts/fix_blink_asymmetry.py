"""
眨眼对称化后处理 —— 修复 i2v 生成的"慢闭快开"眨眼问题。

根因：万相 i2v 视频扩散模型生成的眨眼动画不对称：
  - 闭眼：渐进（4-6 帧）√
  - 睁眼：瞬间（1-2 帧，模型随机性）✗

修复算法：
  1. 逐帧提取灰度均值（眼睛区域 ROI）→ 亮度时序
  2. 检测"亮度突升"事件（1 帧内亮度增量 > 阈值 → 快速睁眼）
  3. 在突升前插入 2 帧线性插值，把睁眼过程拉到 3 帧（≈120ms @25fps）
  4. 重新编码为 mp4

用法：
  .venv/bin/python scripts/fix_blink_asymmetry.py
  （自动处理三套 idle，覆盖原文件并备份）
"""
import sys
from pathlib import Path

import cv2
import numpy as np

BASE = Path(__file__).parent.parent
LT   = Path("/home/jiale/Desktop/LiveTalking")

IDLE_PATHS = [
    BASE / "assets/avatar_src/sweet_bob/idle.mp4",
    BASE / "assets/avatar_src/sweet_bob_happy/idle.mp4",
    BASE / "assets/avatar_src/sweet_bob_concerned/idle.mp4",
]

# 眼睛区域 ROI：人脸在帧中大致居中，取帧高度 15%~45%、帧宽度 20%~80% 的矩形
EYE_ROW_START = 0.15
EYE_ROW_END   = 0.45
EYE_COL_START = 0.20
EYE_COL_END   = 0.80

# 亮度突升检测阈值：>8 视为"瞬间睁眼"（0-255 灰度均值，经验值）
BRIGHTNESS_JUMP_THRESHOLD = 8
# 插入帧数（睁眼过程拉长到 1+2=3 帧）
INTERP_FRAMES = 2


def eye_brightness(frame_gray: np.ndarray) -> float:
    h, w = frame_gray.shape
    r1, r2 = int(h * EYE_ROW_START), int(h * EYE_ROW_END)
    c1, c2 = int(w * EYE_COL_START), int(w * EYE_COL_END)
    roi = frame_gray[r1:r2, c1:c2]
    return float(roi.mean())


def fix_video(src: Path) -> int:
    """处理一个 idle.mp4，返回检测到的突升事件数。"""
    cap = cv2.VideoCapture(str(src))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames = []
    while True:
        ret, f = cap.read()
        if not ret:
            break
        frames.append(f)
    cap.release()

    if not frames:
        print(f"  [警告] {src.name} 无帧，跳过")
        return 0

    # 计算逐帧亮度
    bright = [eye_brightness(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) for f in frames]

    # 检测突升事件并插帧
    out_frames = []
    i = 0
    events = 0
    while i < len(frames):
        out_frames.append(frames[i])
        if i + 1 < len(frames):
            jump = bright[i + 1] - bright[i]
            if jump > BRIGHTNESS_JUMP_THRESHOLD:
                # 插入 INTERP_FRAMES 帧
                for k in range(1, INTERP_FRAMES + 1):
                    alpha = k / (INTERP_FRAMES + 1)
                    interp = cv2.addWeighted(frames[i], 1 - alpha, frames[i + 1], alpha, 0)
                    out_frames.append(interp)
                events += 1
        i += 1

    # 备份原文件
    bak = src.with_suffix(".mp4.bak2")
    if not bak.exists():
        src.rename(bak)
    else:
        src.unlink()

    # 写新视频
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(src), fourcc, fps, (w, h))
    for f in out_frames:
        writer.write(f)
    writer.release()

    print(f"  {src.name}: {len(frames)} → {len(out_frames)} 帧，检测到 {events} 处突升，已插帧")
    return events


def main():
    print("=== 眨眼对称化后处理 ===\n")
    for p in IDLE_PATHS:
        if not p.exists():
            print(f"[跳过] 不存在: {p}")
            continue
        print(f"处理: {p.name}")
        fix_video(p)

    print("\n处理完成。请运行 genavatar 重烘三套 avatar。")


if __name__ == "__main__":
    main()
