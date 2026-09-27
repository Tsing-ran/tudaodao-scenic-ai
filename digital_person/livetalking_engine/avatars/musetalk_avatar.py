###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################
#
#  MuseTalk 数字人 — 迁移自 musereal.py + museasr.py
#

import math
import torch
import numpy as np

import subprocess
import os
import time
import torch.nn.functional as F
import cv2
import glob
import pickle
import copy

import queue
from queue import Queue
from threading import Thread, Event
import torch.multiprocessing as mp

from avatars.musetalk.utils.utils import get_file_type,get_video_fps,datagen
from avatars.musetalk.myutil import get_image_blending
from avatars.musetalk.utils.utils import load_all_model
from avatars.musetalk.whisper.audio2feature import Audio2Feature

from avatars.audio_features.whisper import WhisperASR
import asyncio
from av import AudioFrame, VideoFrame
from avatars.base_avatar import BaseAvatar

from tqdm import tqdm
from utils.logger import logger
from utils.image import read_imgs, mirror_index
from utils.device import initialize_device
from registry import register

device = initialize_device()
logger.info('Using {} for inference.'.format(device))

def load_model():
    # load model weights
    vae, unet, pe = load_all_model()
    #device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu"))
    timesteps = torch.tensor([0], device=device)
    pe = pe.half().to(device)
    vae.vae = vae.vae.half().to(device)
    unet.model = unet.model.half().to(device)
    # Initialize audio processor and Whisper model
    audio_processor = Audio2Feature(model_path="./models/whisper")
    return vae, unet, pe, timesteps, audio_processor

def load_avatar(avatar_id):
    avatar_path = f"./data/avatars/{avatar_id}"
    full_imgs_path = f"{avatar_path}/full_imgs" 
    coords_path = f"{avatar_path}/coords.pkl"
    latents_out_path= f"{avatar_path}/latents.pt"
    video_out_path = f"{avatar_path}/vid_output/"
    mask_out_path =f"{avatar_path}/mask"
    mask_coords_path =f"{avatar_path}/mask_coords.pkl"
    avatar_info_path = f"{avatar_path}/avator_info.json"

    input_latent_list_cycle = torch.load(latents_out_path)
    with open(coords_path, 'rb') as f:
        coord_list_cycle = pickle.load(f)
    frame_list_cycle = None
    input_img_list = glob.glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    frame_list_cycle = read_imgs(input_img_list)
    with open(mask_coords_path, 'rb') as f:
        mask_coords_list_cycle = pickle.load(f)
    input_mask_list = glob.glob(os.path.join(mask_out_path, '*.[jpJP][pnPN]*[gG]'))
    input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    mask_list_cycle = read_imgs(input_mask_list)
    return frame_list_cycle,mask_list_cycle,coord_list_cycle,mask_coords_list_cycle,input_latent_list_cycle

@torch.no_grad()
def warm_up(batch_size,model):
    # 预热函数
    print('warmup model...')
    vae, unet, pe, timesteps, audio_processor = model
    whisper_batch = np.ones((batch_size, 50, 384), dtype=np.uint8)
    latent_batch = torch.ones(batch_size, 8, 32, 32).to(unet.device)

    audio_feature_batch = torch.from_numpy(whisper_batch)
    audio_feature_batch = audio_feature_batch.to(device=unet.device, dtype=unet.model.dtype)
    audio_feature_batch = pe(audio_feature_batch)
    latent_batch = latent_batch.to(dtype=unet.model.dtype)
    pred_latents = unet.model(latent_batch,
                              timesteps,
                              encoder_hidden_states=audio_feature_batch).sample
    vae.decode_latents(pred_latents)    

# ── 面部情绪管理：RAG 情绪标签 → 表情底座 ──────────────────────────────
# RAG 输出 6 类情绪（client.py 的 _EMOTION_MAP），归并到 3 套已烘录的表情底座。
# 底座命名约定：主 avatar=<id>（平静），表情变体=<id>_happy / <id>_concerned。
EMO_TO_BASE = {
    "happy": "happy", "excited": "happy",
    "neutral": "neutral", "curious": "neutral", "calm": "neutral",
    "empathetic": "concerned", "apologetic": "concerned", "concerned": "concerned",
}

# ── 嘴部锐度旋钮（运行时，零重烘；自动调参闭环的"执行器"）─────────────
# 固定 EMA(alpha=0.4) 消抖的同时会把快速口型混成运动模糊（抖动↔模糊二选一）。
# adaptive 模式：按前后帧运动量动态调 alpha——静止时重平滑(防抖)、
# 快速张合时几乎不平滑(保锐度)，打破二选一。unsharp 再补 256 上采样的软化。
# 默认 = 用户 6-08 确认的 fixed0.4 平滑 + 6-10 闭环终审加的 unsharp0.4（牙齿/唇缘更清、零光晕）。
# 自动调参闭环：写 TUNE_FILE(JSON) 即可热改参数、无需重启 LiveTalking。
_TUNE = {
    "ema_mode": os.getenv("MUSETALK_EMA_MODE", "fixed"),            # fixed | adaptive
    "ema_alpha": float(os.getenv("MUSETALK_EMA_ALPHA", "0.4")),     # 静止时当前帧权重
    "ema_motion_full": float(os.getenv("MUSETALK_EMA_MOTION_FULL", "18")),  # 灰阶差≥此→alpha→1
    "sharpen": float(os.getenv("MUSETALK_SHARPEN", "0.4")),         # unsharp 强度（用户终审定 0.4：牙齿/唇缘更清、零光晕）
    "sharpen_sigma": float(os.getenv("MUSETALK_SHARPEN_SIGMA", "1.0")),
}
_TUNE_FILE = os.getenv("MUSETALK_TUNE_FILE", "/tmp/tune/params.json")
_TUNE_MTIME = [0.0]

def _refresh_tune():
    """热加载：TUNE_FILE 变更时刷新嘴部旋钮，免重启 LiveTalking（调参闭环用）。"""
    try:
        m = os.path.getmtime(_TUNE_FILE)
    except OSError:
        return
    if m == _TUNE_MTIME[0]:
        return
    _TUNE_MTIME[0] = m
    try:
        import json as _json
        with open(_TUNE_FILE) as f:
            _TUNE.update(_json.load(f))
        logger.info(f"[tune] 嘴部旋钮热加载 → {_TUNE}")
    except Exception as e:
        logger.warning(f"[tune] 读取 {_TUNE_FILE} 失败: {e}")


@register("avatar", "musetalk")
class MuseReal(BaseAvatar):
    @torch.no_grad()
    def __init__(self, opt, model, avatar):
        super().__init__(opt)

        #self.fps = opt.fps # 20 ms per frame

        # self.batch_size = opt.batch_size
        # self.idx = 0
        # self.res_frame_queue = mp.Queue(self.batch_size*2)

        self.vae, self.unet, self.pe, self.timesteps, self.audio_processor = model

        self.frame_list_cycle,self.mask_list_cycle,self.coord_list_cycle,self.mask_coords_list_cycle, self.input_latent_list_cycle = avatar

        # ── 面部情绪：加载多套表情底座，运行时按 RAG 情绪热切换 ────────────
        # 5 个 cycle（frame/mask/coord/mask_coords/latent）共同决定脸的表情。
        # 切表情 = 整组替换为另一套底座的 5 个 cycle。
        # 关键：把所有底座截断到公共最短长度，使 inference 线程一次性算出的
        #   length 永不越界 → 无需改动共享的 base_avatar.inference()，零侵入。
        base_id = getattr(opt, "avatar_id", None)
        primary = (self.frame_list_cycle, self.mask_list_cycle, self.coord_list_cycle,
                   self.mask_coords_list_cycle, self.input_latent_list_cycle)
        self._emotion_cycles = {"neutral": primary}
        if base_id:
            for emo in ("happy", "concerned"):
                sib = f"{base_id}_{emo}"
                if os.path.isdir(f"./data/avatars/{sib}"):
                    try:
                        self._emotion_cycles[emo] = load_avatar(sib)
                        logger.info(f"[emotion] 已加载表情底座 '{emo}' <- {sib}")
                    except Exception as e:
                        logger.warning(f"[emotion] 加载 {sib} 失败: {e}")
        if len(self._emotion_cycles) > 1:
            L = min(len(c[0]) for c in self._emotion_cycles.values())
            for k in self._emotion_cycles:
                self._emotion_cycles[k] = tuple(seq[:L] for seq in self._emotion_cycles[k])
            (self.frame_list_cycle, self.mask_list_cycle, self.coord_list_cycle,
             self.mask_coords_list_cycle, self.input_latent_list_cycle) = self._emotion_cycles["neutral"]
            logger.info(f"[emotion] 表情底座 {list(self._emotion_cycles)} 已对齐长度 L={L}")
        self._current_emotion = "neutral"
        self._pending_emotion = None
        self._prev_res_frame = None  # 时序 EMA 平滑缓冲

        self.asr = WhisperASR(opt,self,self.audio_processor)
        self.asr.warm_up()

    def set_emotion(self, emotion: str):
        """由 /human 路由在收到带情绪的文本时调用：登记待切换的表情。
        真正的 cycle 替换延迟到 inference 线程的下一个 batch 执行（避免跨线程竞争）。"""
        base = EMO_TO_BASE.get(emotion, "neutral")
        if base not in self._emotion_cycles:
            base = "neutral"
        if base != self._current_emotion:
            self._pending_emotion = base

    def _apply_pending_emotion(self):
        """在 inference 线程内（安全点）原子替换 5 个 cycle 的引用。"""
        base = self._pending_emotion
        self._pending_emotion = None
        if base is None or base == self._current_emotion:
            return
        (self.frame_list_cycle, self.mask_list_cycle, self.coord_list_cycle,
         self.mask_coords_list_cycle, self.input_latent_list_cycle) = self._emotion_cycles[base]
        self._current_emotion = base
        self._prev_res_frame = None  # 情绪切换时重置 EMA 缓冲，避免跨底座帧污染
        logger.info(f"[emotion] 表情底座切换 → {base}")

    def inference_batch(self, index, audiofeat_batch):
        # 这里的 index 是针对当前 avatar 的索引
        # 返回一个 batch 的推理结果，batch 大小由 self.batch_size 决定
        if self._pending_emotion is not None:   # 说话起始帧前切换表情底座
            self._apply_pending_emotion()
        length = len(self.input_latent_list_cycle)
        whisper_batch = np.stack(audiofeat_batch)
        latent_batch = []
        for i in range(self.batch_size):
            idx = mirror_index(length, index + i)
            latent = self.input_latent_list_cycle[idx]
            latent_batch.append(latent)
        latent_batch = torch.cat(latent_batch, dim=0)
        
        audio_feature_batch = torch.from_numpy(whisper_batch)
        audio_feature_batch = audio_feature_batch.to(device=self.unet.device,
                                                        dtype=self.unet.model.dtype)
        audio_feature_batch = self.pe(audio_feature_batch)
        latent_batch = latent_batch.to(dtype=self.unet.model.dtype)

        pred_latents = self.unet.model(latent_batch, 
                                    self.timesteps, 
                                    encoder_hidden_states=audio_feature_batch).sample
        pred = self.vae.decode_latents(pred_latents)
        return pred

    def paste_back_frame(self,pred_frame,idx:int):
        bbox = self.coord_list_cycle[idx]
        ori_frame = copy.deepcopy(self.frame_list_cycle[idx])
        x1, y1, x2, y2 = bbox

        res_frame = cv2.resize(pred_frame.astype(np.uint8),(x2-x1,y2-y1))

        _refresh_tune()  # 调参闭环：热加载嘴部旋钮（仅 mtime 变更时真正读盘）
        # 时序 EMA：对嘴型做低通滤波消抖。fixed=固定 alpha；
        # adaptive=按运动量自适应（静止重平滑、运动保锐度），打破抖动↔模糊二选一。
        if self._prev_res_frame is not None and self._prev_res_frame.shape == res_frame.shape:
            if _TUNE["ema_mode"] == "adaptive":
                diff = float(np.mean(cv2.absdiff(res_frame, self._prev_res_frame)))
                alpha = _TUNE["ema_alpha"] + (1.0 - _TUNE["ema_alpha"]) * min(diff / _TUNE["ema_motion_full"], 1.0)
            else:
                alpha = _TUNE["ema_alpha"]
            res_frame = cv2.addWeighted(res_frame, alpha, self._prev_res_frame, 1.0 - alpha, 0)
        self._prev_res_frame = res_frame.copy()   # 存未锐化版，避免锐化随递归累积

        # unsharp mask：补偿 256→native 上采样 + EMA 带来的软化（0=关）
        if _TUNE["sharpen"] > 0:
            blur = cv2.GaussianBlur(res_frame, (0, 0), _TUNE["sharpen_sigma"])
            res_frame = cv2.addWeighted(res_frame, 1.0 + _TUNE["sharpen"], blur, -_TUNE["sharpen"], 0)

        mask = self.mask_list_cycle[idx]
        mask_crop_box = self.mask_coords_list_cycle[idx]

        combine_frame = get_image_blending(ori_frame,res_frame,bbox,mask,mask_crop_box)
        return combine_frame
            
