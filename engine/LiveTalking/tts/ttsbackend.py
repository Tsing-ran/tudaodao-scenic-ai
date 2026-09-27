"""
队友语音服务 TTS 适配器 —— 让数字人用 CosyVoice 景区专属音色开口。

把队友的 TTS 后端（Digital-person_tts_backend，FastAPI）接成 LiveTalking 的
一个 TTS provider：每来一句文字 → POST {TTS_SERVER}/api/speech/tts → 拿 16kHz
单声道 WAV → 去头取 PCM → 喂给 MuseTalk 做口型同步。

用法：
    python app.py --tts ttsbackend --TTS_SERVER http://127.0.0.1:8001 ...
其中 --TTS_SERVER 指向队友服务根地址（默认 http://127.0.0.1:8001）。

音色选择优先级（与队友服务一致）：
    tts.voice_id 显式指定 > tts.scenic_id 景区默认 > 队友服务全局默认
桥接层在 /human 的 tts 字段里带上 scenic_id（见 bridge/server.py），
即可自动用该景区专属音色（灵山=禅意静女声 等）。
"""
import time
import numpy as np
import resampy
import requests

from utils.logger import logger
from .base_tts import BaseTTS, State
from registry import register

SRC_SR = 16000   # 队友服务输出 WAV_16000HZ_MONO_16BIT
DEFAULT_SERVER = "http://127.0.0.1:8001"


@register("tts", "ttsbackend")
class TeammateBackendTTS(BaseTTS):
    def txt_to_audio(self, msg: tuple[str, dict]):
        text, textevent = msg
        tts_opt = textevent.get('tts', {}) or {}
        voice_id = tts_opt.get('voice_id', '') or ''
        scenic_id = tts_opt.get('scenic_id', '') or ''
        server = getattr(self.opt, 'TTS_SERVER', None) or DEFAULT_SERVER
        self.stream_tts(self._synth(text, voice_id, scenic_id, server), msg)

    def _synth(self, text, voice_id, scenic_id, server):
        """POST 到队友 /api/speech/tts，返回一段 16kHz 单声道 PCM（去掉 WAV 头）。"""
        start = time.perf_counter()
        try:
            resp = requests.post(
                f"{server}/api/speech/tts",
                data={'text': text, 'voice_id': voice_id, 'scenic_id': scenic_id},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error("ttsbackend 合成失败 %s: %s", resp.status_code, resp.text[:300])
                return
            wav = resp.content
            logger.info(
                "ttsbackend voice=%s 用时 %.2fs, %d bytes",
                resp.headers.get('X-Voice-Id', voice_id or scenic_id or 'default'),
                time.perf_counter() - start, len(wav),
            )
            # 去掉 44 字节 WAV 头，余下为 int16 PCM
            if len(wav) > 44:
                yield wav[44:]
        except Exception:
            logger.exception('ttsbackend')

    def stream_tts(self, audio_stream, msg: tuple[str, dict]):
        text, textevent = msg
        first = True
        for chunk in audio_stream:
            if chunk is None or len(chunk) == 0:
                continue
            stream = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767
            if SRC_SR != self.sample_rate:
                stream = resampy.resample(x=stream, sr_orig=SRC_SR, sr_new=self.sample_rate)
            streamlen = stream.shape[0]
            idx = 0
            while streamlen >= self.chunk and self.state == State.RUNNING:
                eventpoint = {}
                if first:
                    eventpoint = {'status': 'start', 'text': text}
                    first = False
                eventpoint.update(**textevent)
                self.parent.put_audio_frame(stream[idx:idx + self.chunk], eventpoint)
                streamlen -= self.chunk
                idx += self.chunk
        eventpoint = {'status': 'end', 'text': text}
        eventpoint.update(**textevent)
        self.parent.put_audio_frame(np.zeros(self.chunk, np.float32), eventpoint)
        # 补发 8 帧静音，确保 inference 管线 is_all_silence 快速切换，消除说话结束后嘴巴悬开
        for _ in range(8):
            self.parent.put_audio_frame(np.zeros(self.chunk, np.float32), {})
