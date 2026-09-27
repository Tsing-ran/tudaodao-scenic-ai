"""用 Qwen-TTS Realtime 生成独立 wav（英雄镜头旁白），16kHz mono。"""
import os, sys, base64, threading, wave
import numpy as np
import dashscope
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

TEXT = sys.argv[1] if len(sys.argv) > 1 else "大家好，我是灵山AI智能导览数字人，很高兴在这里为您导览。"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "/tmp/hero_tts.wav"
VOICE = sys.argv[3] if len(sys.argv) > 3 else "Cherry"

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
pcm = bytearray()
done = threading.Event()

class CB(QwenTtsRealtimeCallback):
    def on_open(self): print("[tts] ws open")
    def on_close(self, c, m): done.set()
    def on_event(self, r):
        t = r.get("type", "")
        if t == "response.audio.delta":
            d = r.get("delta", "")
            if d: pcm.extend(base64.b64decode(d))
        elif t == "response.done":
            print("[tts] done"); done.set()
        elif t == "error":
            print("[tts] ERROR", r); done.set()

cli = QwenTtsRealtime(model="qwen3-tts-flash-realtime", callback=CB(),
                      url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
cli.connect()
cli.update_session(voice=VOICE, response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                   sample_rate=16000, speech_rate=0.9, mode="commit")
cli.append_text(TEXT)
cli.commit()
done.wait(timeout=60)

samples = np.frombuffer(bytes(pcm), dtype=np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes(samples.tobytes())
dur = len(samples) / 16000
print(f"[tts] 写出 {OUT}  时长 {dur:.2f}s  采样 {len(samples)}")
