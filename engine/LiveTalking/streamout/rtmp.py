###############################################################################
#  Output — RTMP 推流输出
###############################################################################

import os
import json
import time
import threading
import urllib.request
import numpy as np
from streamout.base_output import BaseOutput
from registry import register
from utils.logger import logger
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from avatars.base_avatar import BaseAvatar


@register("streamout", "rtmp")
class RTMPOutput(BaseOutput):
    """RTMP 推流输出模式 — 基于 python_rtmpstream 库推送音视频"""

    def __init__(self, opt=None, parent: Optional['BaseAvatar'] = None, **kwargs):
        super().__init__(opt, parent)
        self.push_url = getattr(opt, 'push_url', 'rtmp://localhost/live/livestream')
        self.width = getattr(opt, 'W', 450)
        self.height = getattr(opt, 'H', 450)
        self.fps = getattr(opt, 'fps', 25)
        self.bitrate = getattr(opt, 'bitrate', 1000000)
        self._streamer = None

        #统计视频帧率用
        self.framecount = 0
        self.lasttime = time.perf_counter()
        self.totaltime = 0

        # ── 推流看门狗状态 ─────────────────────────────────────────────
        # python_rtmpstream(C++ Streamer) 无自动重连：RTMP 连接被 SRS 断开后
        # (实测每 5-10min 一次 "cleanup when unpublish")，stream_frame() 继续往
        # 死管子写、不报错 → 画面永久卡死。看门狗轮询 SRS publish.active，掉线则
        # 置 _reconnect_pending；emitter 线程在 push_video_frame 顶部消费此标志、
        # 重建 Streamer(仅重连 RTMP ~1-2s，不碰 TRT/引擎)。所有 _streamer 改动
        # 都在 emitter 单线程内，看门狗只置 bool → 零锁零竞态。
        self._reconnect_pending = False     # 看门狗→emitter 的重连请求(仅 emitter 清)
        self._ever_active = False            # 曾成功发布过(避免启动期误判为掉线)
        self._reconnect_count = 0            # 累计重连次数(观测用)
        self._srs_api = os.getenv(
            "SRS_API_URL", "http://127.0.0.1:1985/api/v1/streams/")
        # 从 push_url 取流名：rtmp://host/live/livestream → livestream
        self._stream_key = self.push_url.rstrip('/').split('/')[-1]
        # 不走系统代理(localhost 调 SRS API)
        self._url_opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}))

    def start(self) -> None:
        """Streamer 延迟到第一帧视频到达时再根据实际宽高初始化"""
        import queue
        self._audio_queue = queue.Queue()
        self._quit_event = False
        # 启动推流看门狗(daemon，随进程退出)
        self._watchdog_thread = threading.Thread(
            target=self._watchdog, name="rtmp-watchdog", daemon=True)
        self._watchdog_thread.start()

    def _srs_publish_active(self) -> Optional[bool]:
        """查 SRS 当前是否有活跃发布端推到本流；API 不可达返回 None(不算掉线)。"""
        try:
            with self._url_opener.open(self._srs_api, timeout=2) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            return None
        for s in data.get("streams", []):
            url = s.get("url", "")
            name = s.get("name", "")
            if url.endswith("/" + self._stream_key) or self._stream_key in name:
                return bool(s.get("publish", {}).get("active"))
        return False   # 流对象都没有 = 没在发布

    def _watchdog(self) -> None:
        """轮询 SRS publish.active；连续两次(~6s)确认掉线则请求 emitter 重连。"""
        miss = 0
        while not self._quit_event:
            time.sleep(2)   # 轮询周期；2 次未发布(~4s)才判掉线，避开单次 API 抖动误判
            if self._streamer is None or self._reconnect_pending:
                continue   # 尚未起流 / 正在重连，跳过
            active = self._srs_publish_active()
            if active is None:
                continue   # API 抖动，不判掉线
            if active:
                self._ever_active = True
                miss = 0
            elif self._ever_active:
                miss += 1
                if miss >= 2:
                    logger.warning(
                        "[rtmp-watchdog] 检测到推流掉线(publish.active=false)，"
                        "请求 emitter 重连 RTMP")
                    self._reconnect_pending = True
                    miss = 0

    def _init_streamer(self, frame_height, frame_width):
        try:
            from rtmp_streaming import StreamerConfig, Streamer
        except ImportError:
            logger.error("rtmp_streaming is not installed. Please install python_rtmpstream.")
            raise

        sc = StreamerConfig()
        sc.source_width = frame_width
        sc.source_height = frame_height
        sc.stream_width = frame_width
        sc.stream_height = frame_height
        sc.stream_fps = self.fps
        sc.stream_bitrate = self.bitrate
        sc.stream_profile = 'main'
        sc.audio_channel = 1
        
        sc.sample_rate = getattr(self.opt, 'sample_rate', 16000)
        if self.parent:
            sc.sample_rate = self.parent.sample_rate
            
        sc.stream_server = self.push_url

        # 先 init 再赋值：避免半初始化的 Streamer 被(同线程后续)音频帧调用
        streamer = Streamer()
        streamer.init(sc)
        self._streamer = streamer

        self._starttime=time.perf_counter()
        self._totalframe=0
        logger.info(f"RTMP output started via python_rtmpstream: {self.push_url} with resolution {frame_width}x{frame_height}")

    def push_video_frame(self, frame) -> None:
        if isinstance(frame, np.ndarray):
            # 看门狗请求重连：丢弃旧 Streamer(C++ 析构关旧 RTMP)，下方按需重建。
            # 仅 emitter 线程在此清标志/改 _streamer → 与看门狗无竞态。
            if self._reconnect_pending:
                self._reconnect_pending = False
                self._streamer = None
                self._reconnect_count += 1
                logger.warning(f"[rtmp-watchdog] 第 {self._reconnect_count} 次重建 Streamer 重连 RTMP")
            if self._streamer is None:
                self.height, self.width = frame.shape[:2]
                try:
                    self._init_streamer(self.height, self.width)
                except Exception as e:
                    # RTMP 连接瞬时失败：保持 _streamer=None，丢弃本帧、下一帧重试，
                    # 绝不让异常冒泡杀死 emitter 线程(否则永久黑屏)
                    self._streamer = None
                    logger.warning(f"[rtmp-watchdog] Streamer 初始化失败({type(e).__name__}: {e})，下一帧重试")
                    return

                # Consume any buffered audio that arrived before the first video frame
                while not self._audio_queue.empty():
                    buffered_audio = self._audio_queue.get()
                    self._streamer.stream_frame_audio(buffered_audio)

            import cv2
            # Convert BGR (OpenCV) to RGB since Streamer expects RGB memory layout
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._streamer.stream_frame(rgb_frame)

            delay = self._starttime+self._totalframe*0.04-time.perf_counter() #40ms
            if delay > 0:
                time.sleep(delay)
            self._totalframe += 1

            self.totaltime += (time.perf_counter() - self.lasttime)
            self.framecount += 1
            self.lasttime = time.perf_counter()
            if self.framecount==100:
                logger.info(f"------actual avg final fps:{self.framecount/self.totaltime:.4f}")
                self.framecount = 0
                self.totaltime=0

    def push_audio_frame(self, frame, eventpoint=None) -> None:
        if isinstance(frame, np.ndarray):
            # The upstream pipeline typically passes np.int16 (after multiplying by 32767).
            # The python_rtmpstream bindings expect np.float32 for AV_SAMPLE_FMT_FLTP.
            if frame.dtype == np.int16:
                frame = frame.astype(np.float32) / 32767.0
            
            if self._streamer:
                self._streamer.stream_frame_audio(frame)
                self.parent.notify(eventpoint)
            else:
                self._audio_queue.put(frame)

    def stop(self) -> None:
        self._quit_event = True   # 看门狗线程随之退出
        self._streamer = None
        logger.info("RTMP output stopped")
