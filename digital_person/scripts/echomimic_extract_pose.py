#!/usr/bin/env python
"""EchoMimicV2 自定义 pose 提取（从驱动视频抽 DWPose + 对齐参考图）。
忠实复刻官方 demo.ipynb 的 get_video_pose / get_pose_params / save_pose_params / save_aligned_img，
只把 notebook 全局 height/width 改成显式入参、并跳过会因无音频崩溃的 convert_fps（decord 内部已重采样到 24fps）。

用法（在 echomimic_v2 仓库根目录、echomimic env 下）：
  python echomimic_extract_pose.py --refimg <ref.png> --drive <wave.mp4> \
      --pose_out assets/halfbody_demo/pose/wave_greet --refimg_out assets/halfbody_demo/refimag/wave_aligned.png
产出：pose npy 目录 + 对齐后的参考图，供 infer.py 用（--pose_dir / --refimg_name）。
"""
import os, sys, argparse, numpy as np, cv2, decord
from multiprocessing.pool import ThreadPool
from src.models.dwpose.dwpose_detector import dwpose_detector as dwprocessor

MAX_SIZE = 768

def get_video_pose(video_path, max_frame=None):
    vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
    stride = max(1, int(vr.get_avg_fps() / 24))
    frames = vr.get_batch(list(range(0, len(vr), stride))).asnumpy()
    if max_frame is not None:
        frames = frames[0:max_frame]
    h, w, _ = frames[0].shape
    poses = [dwprocessor(f) for f in frames]
    dwprocessor.release_memory()
    return poses, h, w, frames

def get_img_pose(img_path):
    frame = cv2.imread(img_path)
    h, w, _ = frame.shape
    short = min(h, w)
    r = max(MAX_SIZE / short, 1.0)
    frame = cv2.resize(frame, (int(r * w), int(r * h)))
    h, w, _ = frame.shape
    poses = [dwprocessor(frame)]
    dwprocessor.release_memory()
    return poses, h, w, frame

def resize_and_pad(img, max_size):
    out = np.zeros((max_size, max_size, 3)).astype('uint8')
    imh, imw = img.shape[0], img.shape[1]
    half = max_size // 2
    if imh > imw:
        imh_new = max_size; imw_new = int(round(imw / imh * imh_new)); half_w = imw_new // 2
        rb, re = 0, max_size; cb = half - half_w; ce = cb + imw_new
    else:
        imw_new = max_size; imh_new = int(round(imh / imw * imw_new)); half_h = imh_new // 2
        cb, ce = 0, max_size; rb = half - half_h; re = rb + imh_new
    out[rb:re, cb:ce, :] = cv2.resize(img, (imw_new, imh_new))
    return out

def resize_and_pad_param(imh, imw, max_size):
    half = max_size // 2
    if imh > imw:
        imh_new = max_size; imw_new = int(round(imw / imh * imh_new)); half_w = imw_new // 2
        rb, re = 0, max_size; cb = half - half_w; ce = cb + imw_new
    else:
        imw_new = max_size; imh_new = max_size; half_h = imh_new // 2
        cb, ce = 0, max_size; rb = half - half_h; re = rb + imh_new
    return imh_new, imw_new, rb, re, cb, ce

def _smooth_seq(arr, win):
    """对 [T, ...] 序列做居中滑动平均（边界收缩窗口），降抖动。win 为奇数。"""
    T = arr.shape[0]
    r = win // 2
    out = np.empty_like(arr, dtype=np.float64)
    for t in range(T):
        a = max(0, t - r); b = min(T, t + r + 1)
        out[t] = arr[a:b].mean(axis=0)
    return out.astype(arr.dtype)

def smooth_poses(detected_poses, win):
    """对 DWPose 逐帧关键点做时间平滑（body/hands/faces），仅在全序列形状一致时生效。
    根治"摆臂/身体逐帧抖"：DWPose 逐帧检测有噪声 + i2v 本身轻微抖，平滑后明显更稳。"""
    if win < 3:
        return detected_poses
    for key, getter in [
        ('bodies', lambda dp: dp['bodies']['candidate']),
        ('hands', lambda dp: dp['hands']),
        ('faces', lambda dp: dp['faces']),
    ]:
        try:
            seq = [getter(dp) for dp in detected_poses]
            shapes = {s.shape for s in seq}
            if len(shapes) != 1:
                print(f'[smooth] skip {key}: 形状不一致 {shapes}')
                continue
            sm = _smooth_seq(np.stack(seq, 0), win)
            for i, dp in enumerate(detected_poses):
                if key == 'bodies':
                    dp['bodies']['candidate'] = sm[i]
                else:
                    dp[key] = sm[i]
        except Exception as e:
            print(f'[smooth] skip {key}: {e}')
    print(f'[smooth] 时间平滑 win={win} 完成')
    return detected_poses

def get_pose_params(detected_poses, max_size, height, width):
    w_min_all, w_max_all, h_min_all, h_max_all, mid_all = [], [], [], [], []
    for num, dp in enumerate(detected_poses):
        dp['num'] = num
        cand_body = dp['bodies']['candidate']; score_body = dp['bodies']['score']
        cand_face = dp['faces']; score_face = dp['faces_score']
        cand_hand = dp['hands']; score_hand = dp['hands_score']
        if cand_face.shape[0] > 1:
            cand_face = cand_face[0]; score_face = score_face[0]
            dp['faces'] = cand_face.reshape(1, cand_face.shape[0], cand_face.shape[1])
            dp['faces_score'] = score_face.reshape(1, score_face.shape[0])
        else:
            cand_face = cand_face[0]; score_face = score_face[0]
        if score_body.shape[0] > 1:
            idx = int(np.argmax([score_body[k].mean() for k in range(score_body.shape[0])]))
            cand_body = cand_body[idx * 18:(idx + 1) * 18, :]; score_body = score_body[idx]
            score_hand = score_hand[(idx * 2):(idx * 2 + 2), :]; cand_hand = cand_hand[(idx * 2):(idx * 2 + 2), :, :]
        else:
            score_body = score_body[0]
        body_pose = np.concatenate((cand_body,)); mid_ = body_pose[1, 0]
        face_pose = cand_face
        h_min, h_max = np.min(face_pose[:, 1]), np.max(body_pose[:7, 1])
        h_ = h_max - h_min; mid_w = mid_
        w_min_all.append(mid_w - h_ // 2); w_max_all.append(mid_w + h_ // 2)
        h_min_all.append(h_min); h_max_all.append(h_max); mid_all.append(mid_w)
    w_min = np.min(w_min_all); w_max = np.max(w_max_all)
    h_min = np.min(h_min_all); h_max = np.max(h_max_all); mid = np.mean(mid_all)
    margin = 0.25; h_margin = (h_max - h_min) * margin
    h_min = max(h_min - h_margin * 0.65, 0); h_max = min(h_max + h_margin * 0.05, 1)
    h_min_real = int(h_min * height); h_max_real = int(h_max * height); mid_real = int(mid * width)
    height_new = h_max_real - h_min_real + 1; width_new = height_new
    w_min_real = mid_real - width_new // 2
    if w_min_real < 0:
        w_min_real = 0; width_new = mid_real * 2
    w_max_real = w_min_real + width_new
    w_min = w_min_real / width; w_max = w_max_real / width
    imh_new, imw_new, rb, re, cb, ce = resize_and_pad_param(height_new, width_new, max_size)
    return {'draw_pose_params': [imh_new, imw_new, rb, re, cb, ce],
            'pose_params': [w_min, w_max, h_min, h_max],
            'video_params': [h_min_real, h_max_real, w_min_real, w_max_real]}

def _save_item(args):
    dp, pose_params, draw_params, save_dir = args
    w_min, w_max, h_min, h_max = pose_params
    num = dp['num']
    cb = dp['bodies']['candidate']; cf = dp['faces'][0]; ch = dp['hands']
    cb[:, 0] = (cb[:, 0] - w_min) / (w_max - w_min); cb[:, 1] = (cb[:, 1] - h_min) / (h_max - h_min)
    cf[:, 0] = (cf[:, 0] - w_min) / (w_max - w_min); cf[:, 1] = (cf[:, 1] - h_min) / (h_max - h_min)
    ch[:, :, 0] = (ch[:, :, 0] - w_min) / (w_max - w_min); ch[:, :, 1] = (ch[:, :, 1] - h_min) / (h_max - h_min)
    dp['bodies']['candidate'] = cb; dp['faces'] = cf.reshape(1, cf.shape[0], cf.shape[1]); dp['hands'] = ch
    dp['draw_pose_params'] = draw_params
    np.save(os.path.join(save_dir, f'{num}.npy'), dp)

def save_pose_params(detected_poses, pose_params, draw_params, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    pool = ThreadPool(8)
    pool.map(_save_item, [[dp, pose_params, draw_params, save_dir] for dp in detected_poses])
    pool.close(); pool.join()
    return save_dir

def save_aligned_img(frame, video_params, max_size, out_path):
    h0, h1, w0, w1 = video_params
    img = resize_and_pad(frame[h0:h1, w0:w1, :], max_size)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, img)
    return out_path

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--refimg', required=True)
    ap.add_argument('--drive', required=True)
    ap.add_argument('--pose_out', required=True)
    ap.add_argument('--refimg_out', required=True)
    ap.add_argument('--smooth', type=int, default=5, help='时间平滑窗口(奇数, 0/1=关)')
    a = ap.parse_args()
    # 对齐参考图（用参考图自身人体框裁切对齐）
    dp_r, hr, wr, frame_r = get_img_pose(a.refimg)
    res_r = get_pose_params(dp_r, MAX_SIZE, hr, wr)
    save_aligned_img(frame_r, res_r['video_params'], MAX_SIZE, a.refimg_out)
    print('[align] ref ->', a.refimg_out)
    # 抽驱动视频 pose（归一化到 [0,1]，每帧 npy 带 draw_pose_params）
    dp_v, hv, wv, _ = get_video_pose(a.drive)
    dp_v = smooth_poses(dp_v, a.smooth)        # 时间平滑降抖动
    res_v = get_pose_params(dp_v, MAX_SIZE, hv, wv)
    save_pose_params(dp_v, res_v['pose_params'], res_v['draw_pose_params'], a.pose_out)
    print(f'[pose] {len(dp_v)} frames ->', a.pose_out)
