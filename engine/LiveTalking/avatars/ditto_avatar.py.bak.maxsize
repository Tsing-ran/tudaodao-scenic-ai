###############################################################################
#  Ditto 实时全脸驱动 avatar（替换 MuseTalk"活嘴死脸"）
#
#  原理：Ditto = LivePortrait 隐式关键点 warp + 音频→运动扩散(LMDM)。
#  不重新生成脸，而是把源肖像"驱动"起来 → 身份/取景/眼神 100% 保留，全脸协调动。
#
#  集成方式：复用 BaseAvatar 的 TTS(qwentts/ttsbackend) 与 output(rtmp)，
#  音频侧用 BaseASR 的 20ms PCM 队列+静音注入；视频侧完全绕过
#  inference/process_frames/paste_back（Ditto SDK 自带流水线），
#  feeder 线程攒 200ms chunk 喂 SDK，emitter 线程把帧+对齐音频推 RTMP。
#  静音时持续喂零 → Ditto 自己生成自然待机微动（不再需要待机底座视频，
#  也没有 MuseTalk 的待机↔说话硬切）。
#
#  启动：--model ditto --avatar_id <源肖像.png 路径或 data/ditto_avatars/<id>.png>
#  需要 env：LD_LIBRARY_PATH 指向 cudnn8（TRT 8.6.1 依赖，见 ditto-engine 记忆）
###############################################################################

import os
import sys
import time
import queue
from queue import Queue
from threading import Thread, Lock

import cv2
import numpy as np

from avatars.base_avatar import BaseAvatar, AudioFrameData
from avatars.audio_features.base_asr import BaseASR
from registry import register
from utils.logger import logger

DITTO_ROOT = os.getenv("DITTO_ROOT", os.path.expanduser("~/Desktop/ditto-talkinghead"))
DITTO_DATA_ROOT = os.getenv("DITTO_DATA_ROOT",
                            os.path.join(DITTO_ROOT, "checkpoints/ditto_trt_Ampere_Plus"))
DITTO_CFG_PKL = os.getenv("DITTO_CFG_PKL",
                          os.path.join(DITTO_ROOT, "checkpoints/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl"))

# 用户定稿的自然度旋钮（外部 env 可覆盖）：
# LIP_KNEE=0.05 软膝压嘴(保音素形状只压大张口)；SMO_K_D=1 去运动平滑(音素利落)；
# STEPS=25 扩散步数(4080 实测 25.5fps 过实时线)
os.environ.setdefault("DITTO_LIP_KNEE", "0.05")
os.environ.setdefault("DITTO_SMO_K_D", "1")
os.environ.setdefault("DITTO_STEPS", "25")

CHUNKSIZE = (3, 5, 2)                     # 历史/当前/未来（25fps 帧数）
WIN_LEN = int(sum(CHUNKSIZE) * 0.04 * 16000) + 80   # 6480 样本滑窗
STEP = CHUNKSIZE[1] * 640                 # 3200 样本 = 200ms = 5 帧
HIST = CHUNKSIZE[0] * 640                 # 1920 历史
PCM_FRAME = 320                           # 20ms@16k
FRAMES_PER_CHUNK = STEP // PCM_FRAME      # 10 个 20ms 帧/chunk

# RAG [情绪:X] → Ditto 8 类情绪条件（0Angry 1Disgust 2Fear 3Happy 4Neutral 5Sad 6Surprise 7Contempt）
# 混合类别（tuple）经 softmax 摊平成 ~50/50，比单类柔和——导游不演苦情戏：
# 关切/抱歉 = Neutral+Sad 微垂；兴奋 = Happy+Surprise 提神；好奇 = Neutral+Surprise 轻挑眉
EMO_TO_DITTO = {
    "happy": 3, "excited": (3, 6),
    "neutral": 4, "calm": 4, "curious": (4, 6),
    "concerned": (4, 5), "empathetic": (4, 5), "apologetic": (4, 5),
}
EMO_IDLE_REVERT_SEC = float(os.getenv("DITTO_EMO_IDLE_REVERT", "4"))  # 静音 N 秒后表情回中性
# feeder 反压阈值：pending_audio（待 emitter 配对推流的音频帧）积压超过此值则等。
# 用下游真实消费速率反压，使 feeder 跟随 emitter/SDK 实际 fps（~21-25），
# 不再按固定 25fps 时钟超产音频→堆 pending（旧 bug：音频 50/s vs 视频 42/s→8s 积压→语音永远排队不出声）。
PENDING_MAX = int(os.getenv("DITTO_PENDING_MAX", "30"))               # 30 帧≈0.6s 抗抖动缓冲


def load_model():
    """模型句柄=路径（SDK 在会话内构建，TRT 引擎加载 ~6s）"""
    return {"data_root": DITTO_DATA_ROOT, "cfg_pkl": DITTO_CFG_PKL}


def load_avatar(avatar_id):
    """avatar = 源肖像图：绝对路径，或 data/ditto_avatars/<id>.png"""
    if os.path.isfile(avatar_id):
        return os.path.abspath(avatar_id)
    p = os.path.join("data", "ditto_avatars", f"{avatar_id}.png")
    if os.path.isfile(p):
        return os.path.abspath(p)
    raise FileNotFoundError(f"[ditto] 源肖像不存在: {avatar_id}（绝对路径或 data/ditto_avatars/<id>.png）")


def warm_up(batch_size, model):
    pass  # 预热在会话首个 chunk 内完成


class _PCMBuffer(BaseASR):
    """只复用 BaseASR 的 20ms 队列 + 静音注入 + flush_talk，不做特征提取"""
    def run_step(self):
        pass


@register("avatar", "ditto")
class DittoAvatar(BaseAvatar):
    def __init__(self, opt, model, avatar):
        super().__init__(opt)   # 初始化 TTS + output(rtmp)
        self.asr = _PCMBuffer(opt, self)

        if DITTO_ROOT not in sys.path:
            sys.path.insert(0, DITTO_ROOT)
        from stream_pipeline_online import StreamSDK

        t0 = time.time()
        self.SDK = StreamSDK(model["cfg_pkl"], model["data_root"])
        self.SDK.setup(avatar, "/tmp/ditto_live_dummy.mp4")
        self.SDK.setup_Nd(N_d=-1, fade_in=-1, fade_out=-1, ctrl_info={})
        assert self.SDK.online_mode, "ditto cfg 必须是 online 版(v0.4_hubert_cfg_trt_online.pkl)"

        # 帧出口：替换 SDK 的文件 writer → 内存队列（emitter 取走推 RTMP）
        # maxsize 即稳态延迟上限：SDK 出帧(25.5fps)略快于发送(25fps)→队列会填满到 maxsize，
        # 语音帧得排在这一队 idle 帧后面。64 帧=2.56s 缓冲（实测端到端延迟主凶）→压到 6 帧≈0.24s。
        # SDK.writer 回调里 put 用阻塞=天然背压，队列满则 SDK 自动等（不丢帧、不卡死）。
        self.frame_queue: Queue = Queue(maxsize=int(os.getenv("DITTO_FRAME_QUEUE", "6")))
        fq = self.frame_queue
        class _W:
            def __call__(self, frame_rgb, fmt="rgb"):
                fq.put(frame_rgb)
            def close(self):
                pass
        self.SDK.writer = _W()

        # 与帧对齐的音频（FIFO；每视频帧消费 2×20ms）
        self.pending_audio: Queue = Queue()

        # 情绪条件基线快照：默认 emo 是 cfg 里一段 600 帧真人情绪序列（自然游走），
        # set_emotion("neutral") 恢复它而非常量 Neutral——待机表情才不僵
        ch = self.SDK.condition_handler
        self._emo_default = (ch.emo_lst, ch.num_emo, ch.emo_seq) if getattr(ch, "use_emo", False) else None
        self._cur_emo = "default"
        self._src_lock = Lock()          # 串行化并发 set_source（热拔插换底板）
        logger.info(f"[ditto] SDK 就绪({time.time()-t0:.1f}s) source={avatar} "
                    f"knee={os.environ['DITTO_LIP_KNEE']} smo={os.environ['DITTO_SMO_K_D']} steps={os.environ['DITTO_STEPS']}")

    def set_emotion(self, emotion: str):
        """RAG [情绪:X] → Ditto 原生 emo 条件热切。

        原理：在线流水线每个 80 帧 chunk 都读 condition_handler.emo_seq 拼进 LMDM 条件
        （stream_pipeline_online.py L430 → condition_handler.__call__），setup 后该属性
        不再被 SDK 改写 → 单属性原子赋值（GIL）即可热切，audio2motion 线程下一个
        chunk 就用新情绪，无需停流。"""
        if self._emo_default is None:
            logger.warning(f"[ditto] cfg use_emo=False，emotion={emotion} 忽略")
            return
        idx = EMO_TO_DITTO.get(emotion, "default")
        # neutral/calm/未知 → 恢复默认真人情绪序列（比常量 Neutral 更自然）
        target = "default" if idx == 4 else idx
        if target == self._cur_emo:
            return
        ch = self.SDK.condition_handler
        if target == "default":
            ch.emo_lst, ch.num_emo, ch.emo_seq = self._emo_default
        else:
            emo_vec = ch._parse_emo_seq(list(idx) if isinstance(idx, tuple) else idx)  # [1,8]
            ch.emo_lst = emo_vec
            ch.num_emo = 1
            ch.emo_seq = np.concatenate([emo_vec] * ch.seq_frames, 0)
        self._cur_emo = target
        logger.info(f"[ditto] emotion={emotion} → Ditto emo {target} 已热切")

    def set_source(self, avatar_id: str) -> bool:
        """热拔插换底板：重跑源注册 + 复刻 setup 的源相关子调用，**不停 RTMP 流**。

        原理：Ditto 把"身份"存成 source_info 的逐帧 numpy 列表（appearance f_s /
        motion x_s / putback img_rgb+M_c2o），不绑 TRT 引擎状态（与 set_emotion 同理）。
        重跑 avatar_registrar 得新身份(~1s, 路由线程)，再复刻 setup() 里 source 相关的三处
        子调用（condition_handler/audio2motion/motion_stitch.setup，其余参数沿用首次 setup
        已存于 SDK 的值）即换人/换装。单图源 frame 数恒为 1（idx=0）、各张量 shape 一致 →
        渲染 worker 并发读不越界，最坏一帧瑕疵，对"配置级换形象"动作可接受。
        ⚠️ 绝不能整体重调 SDK.setup()——它在 L222 把 self.writer 重置成文件 writer，
        会毁掉我们的内存帧队列（__init__ 在 setup 之后才覆盖 writer）。"""
        try:
            path = load_avatar(avatar_id)
        except FileNotFoundError as e:
            logger.error(f"[ditto] set_source 失败：{e}")
            return False
        sdk = self.SDK
        with self._src_lock:
            t0 = time.time()
            crop_kwargs = {
                "crop_scale": sdk.crop_scale, "crop_vx_ratio": sdk.crop_vx_ratio,
                "crop_vy_ratio": sdk.crop_vy_ratio, "crop_flag_do_rot": sdk.crop_flag_do_rot,
            }
            tnf = getattr(sdk, "template_n_frames", -1)
            n_frames = tnf if tnf and tnf > 0 else sdk.N_d
            try:
                new_info = sdk.avatar_registrar(path, max_dim=sdk.max_size,
                                                n_frames=n_frames, **crop_kwargs)
            except Exception as e:
                logger.error(f"[ditto] set_source 注册失败({avatar_id})：{type(e).__name__}: {e}")
                return False
            # —— 复刻 setup() 的 source 相关子调用（单图源无需 smooth_x_s_info_lst）——
            sdk.source_info = new_info
            sdk.source_info_frames = len(new_info["x_s_info_lst"])
            sdk.condition_handler.setup(new_info, sdk.emo,
                                        eye_f0_mode=sdk.eye_f0_mode, ch_info=sdk.ch_info)
            sdk.audio2motion.setup(
                sdk.condition_handler.x_s_info_0,
                overlap_v2=sdk.overlap_v2, fix_kp_cond=sdk.fix_kp_cond,
                fix_kp_cond_dim=sdk.fix_kp_cond_dim, sampling_timesteps=sdk.sampling_timesteps,
                online_mode=sdk.online_mode, v_min_max_for_clip=sdk.v_min_max_for_clip,
                smo_k_d=sdk.smo_k_d,
            )
            sdk.motion_stitch.setup(
                N_d=sdk.N_d, use_d_keys=sdk.use_d_keys, relative_d=sdk.relative_d,
                drive_eye=sdk.drive_eye, delta_eye_arr=sdk.delta_eye_arr,
                delta_eye_open_n=sdk.delta_eye_open_n, fade_out_keys=sdk.fade_out_keys,
                fade_type=sdk.fade_type, flag_stitching=sdk.flag_stitching,
                is_image_flag=new_info["is_image_flag"], x_s_info=new_info["x_s_info_lst"][0],
                d0=None, ch_info=sdk.ch_info, overall_ctrl_info=sdk.overall_ctrl_info,
            )
            # 情绪基线快照随新底板刷新；表情回中性（下一句带 emotion 会重设）
            ch = sdk.condition_handler
            self._emo_default = (ch.emo_lst, ch.num_emo, ch.emo_seq) if getattr(ch, "use_emo", False) else None
            self._cur_emo = "default"
            logger.info(f"[ditto] source={avatar_id} 已热切({time.time()-t0:.2f}s)")
            return True

    def _feeder(self, quit_event):
        """攒 20ms PCM → 6480 滑窗(含 1920 历史 + 3200 当前 + 1360 未来) → SDK.run_chunk。
        静音时 BaseASR 注入零帧 → Ditto 生成自然待机微动。

        ⚠️ 关键延迟修复（2026-06-13）：idle 时 BaseASR 静音注入很快(~2× 实时)，feeder 会跑在
        SDK 前面把 idle chunk 灌满 SDK 内部队列（QUEUE_MAX_SIZE=100 → 可缓冲 ~20s），语音到达
        后排在这堆 idle 后面 → 端到端延迟 ~10s。故给 feeder 加实时节流：只允许领先墙钟 FEEDER_LEAD
        秒（抗抖动），超过则 sleep，使 SDK 队列near-empty、语音几乎即时进管线。"""
        buf = np.zeros(HIST, dtype=np.float32)   # 初始历史=零（与官方 pad 一致）
        metas = []                                # 与 buf[HIST:] 一一对应的 20ms 帧元数据
        silent_frames = 0                         # 连续静音 20ms 帧计数（表情回中性用）
        while not quit_event.is_set():
            # 下游反压：pending_audio 积压超阈值则等 emitter 消费，使 feeder 跟随真实输出速率、
            # 不超产音频（治"idle 灌满队列致语音排队"高延迟 + "音视频产速不匹配致语音堆 pending 不出声"）
            while self.pending_audio.qsize() > PENDING_MAX and not quit_event.is_set():
                time.sleep(0.01)
            # 凑满一个完整滑窗（当前 step + 未来 lookahead）
            while len(buf) < WIN_LEN:
                af = self.asr.get_audio_frame()
                buf = np.concatenate([buf, af.data])
                metas.append(af)
                # 说完一段话静音 N 秒后表情自动回默认（不让关切/喜悦在待机里挂脸上）
                silent_frames = silent_frames + 1 if af.type == 1 else 0
                if silent_frames * 0.02 > EMO_IDLE_REVERT_SEC and self._cur_emo != "default":
                    self.set_emotion("neutral")
            self.SDK.run_chunk(buf[:WIN_LEN].copy(), CHUNKSIZE)
            # 本 chunk 的"当前 200ms" = metas 前 10 帧 → 配对队列
            for af in metas[:FRAMES_PER_CHUNK]:
                self.pending_audio.put(af)
            metas = metas[FRAMES_PER_CHUNK:]
            buf = buf[STEP:]
        logger.info("[ditto] feeder 线程退出")

    def _emitter(self, quit_event):
        """SDK 帧 + 对齐音频 → RTMP。背压与 base process_frames 同款。"""
        self.output.start()
        while not quit_event.is_set():
            try:
                frame_rgb = self.frame_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue
            combine_frame = cv2.cvtColor(np.asarray(frame_rgb), cv2.COLOR_RGB2BGR)
            cv2.putText(combine_frame, "LiveTalking", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (128, 128, 128), 1)
            self.output.push_video_frame(combine_frame)
            self.record_video_data(combine_frame)

            speaking = False
            for _ in range(2):   # 每视频帧 2×20ms 音频
                try:
                    af: AudioFrameData = self.pending_audio.get(timeout=1)
                except queue.Empty:
                    af = AudioFrameData(data=np.zeros(PCM_FRAME, np.float32), type=1, userdata={})
                if af.type == 0:
                    speaking = True
                pcm16 = (af.data * 32767).astype(np.int16)
                self.output.push_audio_frame(pcm16, af.userdata)
                self.record_audio_data(pcm16)
            self.speaking = speaking

            # 输出缓冲背压（与 base render 同款节流）
            bs = self.output.get_buffer_size() if hasattr(self.output, 'get_buffer_size') else 0
            if bs >= 5:
                time.sleep(0.04 * bs * 0.8)
        self.output.stop()
        logger.info("[ditto] emitter 线程退出")

    def render(self, quit_event):
        """覆写 base.render：不走 inference/process_frames（Ditto SDK 自带流水线）"""
        self.quit_event = quit_event
        self.init_customindex()
        self.tts.render(quit_event)

        feeder = Thread(target=self._feeder, args=(quit_event,), name="ditto-feeder")
        emitter = Thread(target=self._emitter, args=(quit_event,), name="ditto-emitter")
        feeder.start()
        emitter.start()
        logger.info("[ditto] render 启动（feeder+emitter）")
        while not quit_event.is_set():
            time.sleep(0.5)
        feeder.join(timeout=3)
        emitter.join(timeout=3)
        try:
            self.SDK.close()
        except Exception:
            pass
        logger.info("[ditto] render 退出")
