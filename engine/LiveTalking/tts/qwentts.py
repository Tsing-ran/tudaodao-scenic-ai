import os
import base64
import time
import threading
import numpy as np
import resampy

from utils.logger import logger
from .base_tts import BaseTTS, State
from registry import register

try:
    import dashscope
    from dashscope.audio.qwen_tts_realtime import (
        QwenTtsRealtime,
        QwenTtsRealtimeCallback,
        AudioFormat,
    )
except ImportError:
    logger.error("QwenTTS 需要安装 dashscope SDK: pip install dashscope>=1.25.11")
    raise


SRC_SR = 24000   # Qwen TTS 只支持 24kHz 输出
DST_SR = 16000   # 项目标准采样率

# ── 韵律随情绪：speech_rate 绑定 RAG 的 [情绪:X]（播音"停连/语气"外化到声音）──
# 6 类情绪并到 3 档语速。基准 0.9（用户定：放慢避免"急促/谄媚"）。
# 关切/抱歉再放慢=关怀感；喜悦/兴奋略快=活泼但不抢拍（用户对"太快"敏感，故只 +0.03）。
EMO_RATE = {
    "happy": 0.93, "excited": 0.93,
    "neutral": 0.90, "curious": 0.90, "calm": 0.90,
    "empathetic": 0.85, "apologetic": 0.85, "concerned": 0.85,
}


@register("tts", "qwentts")
class QwenTTS(BaseTTS):
    """
    阿里云通义千问实时语音合成 (Qwen TTS Realtime)
    基于 DashScope Python SDK (dashscope >= 1.25.11)
    使用 commit 模式：只建立一次 WebSocket 连接，每次合成通过 append_text + commit 触发。

    需要设置环境变量 DASHSCOPE_API_KEY。
    用法:
        python app.py --tts qwentts --REF_FILE Cherry
    其中 REF_FILE 用作音色名称 (voice)，如 Cherry / Ethan 等系统音色。
    """

    def __init__(self, opt, parent):
        super().__init__(opt, parent)

        # 音色名, 复用 REF_FILE 参数
        self.voice = opt.REF_FILE if opt.REF_FILE else 'Cherry'
        # 模型名
        self.model = getattr(opt, 'qwen_tts_model', 'qwen3-tts-flash-realtime')
        # WebSocket URL
        self.ws_url = getattr(opt, 'qwen_tts_url',
                              'wss://dashscope.aliyuncs.com/api-ws/v1/realtime')

        # 设置 DashScope API Key
        api_key = getattr(opt, 'dashscope_api_key', None) or os.environ.get('DASHSCOPE_API_KEY')
        if api_key:
            dashscope.api_key = api_key
        else:
            logger.warning("QwenTTS: DASHSCOPE_API_KEY 未设置，请设置环境变量或通过参数传入")

        # 当前会话语速（随情绪动态调整，见 txt_to_audio）
        self.speech_rate = 0.9

        # ---------- 内部状态 ----------
        self._remainder = np.array([], dtype=np.float32)  # 上次重采样后不足一 chunk 的 16kHz 样本
        self._response_event = threading.Event()
        self._first_chunk = True          # 当前合成的一句话里的第一个音频包
        self._current_text = ''
        self._current_textevent = {}
        self._reconnecting = False        # 主动重连期间抑制 on_close 置事件（防 wait 早返回丢音频）
        self._alive = False               # 连接健康：on_open 置真，on_close/error 置假
                                          # Qwen WS 空闲 300s 被服务端超时关闭 → 合成前据此重连

        # ---------- 回调类 ----------
        tts_ref = self

        class _Callback(QwenTtsRealtimeCallback):
            def on_open(self) -> None:
                logger.info("QwenTTS WebSocket 连接已建立")
                tts_ref._alive = True

            def on_close(self, close_status_code, close_msg) -> None:
                logger.info(f"QwenTTS WebSocket 关闭: code={close_status_code}, msg={close_msg}")
                tts_ref._alive = False
                # 主动重连（换音色/语速）触发的 close 不许置事件：否则 txt_to_audio 的
                # wait() 早返回 → BaseTTS 状态离开 RUNNING → 后续音频 delta 全被丢 → 静音
                if not tts_ref._reconnecting:
                    tts_ref._response_event.set()

            def on_event(self, response: dict) -> None:
                try:
                    event_type = response.get('type', '')

                    if event_type == 'session.created':
                        logger.info(f"QwenTTS session: {response.get('session', {}).get('id', '')}")

                    elif event_type == 'response.audio.delta':
                        audio_b64 = response.get('delta', '')
                        if audio_b64:
                            pcm_data = base64.b64decode(audio_b64)
                            tts_ref._on_audio_data(pcm_data)

                    elif event_type == 'response.done':
                        logger.info("QwenTTS response done")
                        tts_ref._flush_remainder()
                        tts_ref._response_event.set()

                    elif event_type == 'error':
                        logger.error(f"QwenTTS 错误: {response}")
                        tts_ref._alive = False   # 服务端错误（如空闲 300s 超时）后连接不可用
                        tts_ref._response_event.set()

                except Exception as e:
                    logger.exception(f"QwenTTS 回调处理异常: {e}")

        # ---------- 建立唯一连接 ----------
        self._callback = _Callback()
        self._tts_client = QwenTtsRealtime(
            model=self.model,
            callback=self._callback,
            url=self.ws_url,
        )
        self._tts_client.connect()
        self._tts_client.update_session(
            voice=self.voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # Qwen TTS 只支持 24kHz 输出
            sample_rate=16000,
            speech_rate=0.9,   # 语速放慢 10%，避免 MuseTalk 嘴动过快显得急促/谄媚
            mode='commit',
        )
        logger.info(f"QwenTTS 初始化完成: model={self.model}, voice={self.voice}")

    # ========================== 核心方法 ==========================

    def txt_to_audio(self, msg: tuple[str, dict]):
        text, textevent = msg
        t_start = time.perf_counter()

        ref_file = textevent.get('tts', {}).get('ref_file',self.opt.REF_FILE)

        # 重置状态
        self._remainder = np.array([], dtype=np.float32)
        self._first_chunk = True
        self._current_text = text
        self._current_textevent = textevent
        self._response_event.clear()

        try:
            #logger.info(f"QwenTTS 发送文本: {text[:80]}...")
            # ⚠️ 延迟权衡（2026-06-13）：Qwen-TTS 改 speech_rate 必须重连(~1.5-2s)，挂在首句
            #    latency-critical 路径上→端到端可超 5s。情绪的主要表达已外化到「脸」(Ditto 8 类
            #    emo 条件，set_emotion)，语速 0.05 的差异收益远不及 2s 延迟代价 → 固定 speech_rate=0.9，
            #    不再随情绪重连。仅「换音色」「连接已死(空闲300s超时)」才重连（这两个无法避免）。
            if ref_file != self.voice:
                logger.info(f'ref_file:{ref_file},self.voice:{self.voice}')
                self.voice = ref_file
                self._reconnect_session()
            elif not self._alive:
                # 连接因空闲 300s 超时/服务端错误已死 → 先重连再合成
                # （否则 append_text 到死连接 → "Connection is already closed" → 静音）
                logger.info("QwenTTS 连接已失效（空闲超时？），合成前重连")
                self._reconnect_session()

            self._synthesize_with_retry(text)

            t_end = time.perf_counter()
            logger.info(f"QwenTTS 合成完成，耗时: {t_end - t_start:.2f}s")

        except Exception as e:
            logger.exception(f"QwenTTS txt_to_audio 异常: {e}")

    def _synthesize_with_retry(self, text: str):
        """合成一句；若连接中途死亡（commit/append 抛错或 error 回调），重连后重试一次。"""
        try:
            self._tts_client.append_text(text)
            self._tts_client.commit()
            self._response_event.wait(timeout=60)
            if self._alive:
                return
            # wait 返回但连接已死（error 回调置假）= 多半没出音频 → 重试
            logger.warning("QwenTTS 合成期间连接失效，重连重试一次")
        except Exception as e:
            logger.warning(f"QwenTTS 合成失败（{type(e).__name__}: {e}），重连重试一次")
        self._reconnect_session()
        self._first_chunk = True
        self._response_event.clear()
        self._tts_client.append_text(text)
        self._tts_client.commit()
        self._response_event.wait(timeout=60)

    def _reconnect_session(self):
        """换音色/语速的统一重连（Qwen session 已 start 后参数不可变更）。
        _reconnecting 抑制 on_close 置事件；完后再 clear 一次兜底竞态。"""
        self._reconnecting = True
        try:
            self._tts_client.close()
            self._tts_client.connect()
            self._tts_client.update_session(
                voice=self.voice,
                response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # Qwen TTS 只支持 24kHz 输出
                sample_rate=16000,
                speech_rate=self.speech_rate,
                mode='commit',
            )
        finally:
            self._reconnecting = False
        self._response_event.clear()

    # ========================== 流式音频处理（回调中调用）==========================

    def _on_audio_data(self, pcm_data: bytes):
        """收到 PCM 24kHz 16bit mono 音频，一次性 resample 到 16kHz 后分块推送"""
        if self.state != State.RUNNING:
            self._remainder = np.array([], dtype=np.float32)
            return

        # 整段 24kHz PCM -> float32 -> 一次性 resample 到 16kHz
        samples_16k = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
        #samples_16k = resampy.resample(x=samples_24k, sr_orig=SRC_SR, sr_new=DST_SR)

        # 拼接上次剩余
        if self._remainder.shape[0] > 0:
            samples_16k = np.concatenate([self._remainder, samples_16k])

        # 按 self.chunk (320 samples = 20ms @16kHz) 分块推送
        idx = 0
        total = samples_16k.shape[0]
        while total - idx >= self.chunk and self.state == State.RUNNING:
            frame = samples_16k[idx:idx + self.chunk]
            eventpoint = {}
            if self._first_chunk:
                eventpoint = {'status': 'start', 'text': self._current_text}
                self._first_chunk = False
            eventpoint.update(**self._current_textevent)
            self.parent.put_audio_frame(frame, eventpoint)
            idx += self.chunk

        # 不足一 chunk 的留到下次
        self._remainder = samples_16k[idx:] if idx < total else np.array([], dtype=np.float32)

    def _flush_remainder(self):
        """合成完毕，推送剩余样本并发送 end 事件"""
        if self.state != State.RUNNING:
            self._remainder = np.array([], dtype=np.float32)
            return

        # 推送剩余完整 chunk
        if self._remainder.shape[0] >= self.chunk:
            idx = 0
            total = self._remainder.shape[0]
            while total - idx >= self.chunk and self.state == State.RUNNING:
                frame = self._remainder[idx:idx + self.chunk]
                eventpoint = {}
                if self._first_chunk:
                    eventpoint = {'status': 'start', 'text': self._current_text}
                    self._first_chunk = False
                eventpoint.update(**self._current_textevent)
                self.parent.put_audio_frame(frame, eventpoint)
                idx += self.chunk

        self._remainder = np.array([], dtype=np.float32)

        # 发送 end 事件
        eventpoint = {'status': 'end', 'text': self._current_text}
        eventpoint.update(**self._current_textevent)
        self.parent.put_audio_frame(np.zeros(self.chunk, np.float32), eventpoint)
        # 补发 8 帧静音：inference() 每次消费 batch_size*2=8 帧，1 帧静音会被 7 帧语音淹没
        # 导致 is_all_silence=False，嘴巴持续张开；8 帧确保填满整批使状态快速切换到 idle
        for _ in range(8):
            self.parent.put_audio_frame(np.zeros(self.chunk, np.float32), {})

    def stop_tts(self):
        self._tts_client.close()
        logger.info("QwenTTS 已关闭")