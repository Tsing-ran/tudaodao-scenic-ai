# -*- coding: utf-8 -*-
"""ASR 口音识别回归测试（独立脚本，不 pytest）。

用 Qwen-TTS 的口音/方言音色合成带景区专名的游客提问：
  Cherry=标准普通话  Dylan=北京话  Jada=吴语  Sunny=四川话
同一段音频分别过 云端 qwen3-asr / 本地 faster-whisper，与原文对比。
判定门槛：云端 >= 12/16 视为通过（本地结果仅作对照展示）。

跑法：.venv/bin/python tests/test_asr_accents.py
要求：.env 配置 DASHSCOPE_API_KEY；需外网（TTS 合成 + 云端识别）。
"""
import io
import os
import re
import sys
import tempfile
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import dashscope
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", "")

OUTDIR = os.path.join(tempfile.gettempdir(), "asr_accent_test")
os.makedirs(OUTDIR, exist_ok=True)

VOICES = [("Cherry", "标准普通话"), ("Dylan", "北京话"), ("Jada", "吴语"), ("Sunny", "四川话")]
SENTENCES = [
    "九龙灌浴几点开始表演",
    "灵山大佛到底有多高啊",
    "阿育王柱在哪个位置",
    "带小孩去梵宫怎么走最近",
]
CLOUD_PASS = 12   # 16 句中云端至少对 12 句

_PUNCS = re.compile(r"[，。！？、,.!?\s]")
_TAIL_PARTICLE = re.compile(r"[啊呀哦嘛呢吧]+$")

# 标准音色在基础版模型；口音/方言音色在 latest 版
_TTS_MODEL = {"Cherry": "qwen-tts", "Serena": "qwen-tts", "Ethan": "qwen-tts"}


def norm(s: str) -> str:
    """语义等价判定：去标点空白 + 去句尾语气词（"多高"与"多高啊"同义）。"""
    return _TAIL_PARTICLE.sub("", _PUNCS.sub("", s or ""))


def tts(voice: str, text: str, path: str) -> None:
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return
    model = _TTS_MODEL.get(voice, "qwen-tts-latest")
    for attempt in range(4):
        r = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
            model=model, text=text, voice=voice)
        if r.status_code == 200:
            urllib.request.urlretrieve(r.output.audio["url"], path)
            time.sleep(1.5)                    # 限流保护
            return
        if "Throttling" in str(getattr(r, "code", "")):
            time.sleep(6 * (attempt + 1))
            continue
        raise RuntimeError(f"tts {r.code}: {r.message}")
    raise RuntimeError("tts 限流重试仍失败")


def main() -> int:
    from backend.asr.cloud_asr import transcribe_cloud
    from backend.asr.transcriber import _transcribe_local

    print("合成测试音频（Qwen-TTS 口音音色）…")
    clips = []
    for vi, (voice, vlabel) in enumerate(VOICES):
        for si, sent in enumerate(SENTENCES):
            p = f"{OUTDIR}/v{vi}s{si}_{voice}.wav"
            try:
                tts(voice, sent, p)
                clips.append((vlabel, sent, p))
            except Exception as e:
                print(f"  !! {voice} 合成失败: {e}")

    stats = {"cloud": [0, 0], "local": [0, 0]}
    for vlabel, sent, p in clips:
        out = {}
        for eng in ("cloud", "local"):
            try:
                if eng == "cloud":
                    r = transcribe_cloud(p, "lingshan", "zh",
                                         model="qwen3-asr-flash", timeout=15)
                else:
                    r = _transcribe_local(p, "lingshan", "zh")
                out[eng] = r["text"]
            except Exception as e:
                out[eng] = f"<ERR {e}>"
            ok = norm(out[eng]) == norm(sent)
            stats[eng][1] += 1
            stats[eng][0] += int(ok)
            out[eng + "_ok"] = ok
        c = "OK " if out["cloud_ok"] else "ERR"
        l = "OK " if out["local_ok"] else "ERR"
        print(f"[{vlabel}] {sent}")
        print(f"   cloud {c} | {out['cloud']}")
        print(f"   local {l} | {out['local']}")

    ok, tot = stats["cloud"]
    lok, ltot = stats["local"]
    print(f"\n云端 {ok}/{tot}（门槛 {CLOUD_PASS}）  本地对照 {lok}/{ltot}")
    if tot == 0 or ok < CLOUD_PASS * tot / 16:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
