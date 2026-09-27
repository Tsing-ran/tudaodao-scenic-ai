"""
云端 ASR：DashScope `qwen3-asr-flash` 语音识别大模型。

为什么在本地 faster-whisper 之上再加云端档：
  small 档 whisper 对**带口音的普通话**（南方口音、方言腔）与生僻专名的识别
  明显弱于云端 ASR 大模型；qwen3-asr 系列原生覆盖普通话口音/多种方言/多语种，
  并支持"上下文偏置"——把景区专名表作为上下文注入，专名识别率进一步提升
  （效果等同热词，但容量远大于 whisper 的 hotwords 参数）。

设计：
  - 纯 CPU、零显存；与 LLM/TTS 共用 DASHSCOPE_API_KEY，无新增依赖。
  - 带超时保护：云端超时/报错由上层（transcriber.transcribe）落回本地 whisper，
    游客感知只是"这一句稍慢"，不会失败。
  - webm/opus、m4a/aac、wav、mp3 等浏览器录音格式均被模型直接支持，无需转码。
"""
import os
from concurrent.futures import ThreadPoolExecutor

# 独立小线程池：只为云端调用的超时控制（SDK 自身无细粒度超时参数）
_EXEC = ThreadPoolExecutor(max_workers=4)

# qwen3-asr 支持强制指定的语言代码；不在此集合则交给模型自动检测
_SUPPORTED_LANG = {"zh", "en", "ja", "ko", "es", "fr", "de", "ar", "it", "pt", "ru"}

# 各景区通用的问询词汇（设施/服务类），与景区专名表一并注入上下文
_COMMON_TERMS = "游客中心 洗手间 卫生间 索道 门票 检票口 讲解 观光车 直达车 停车场 母婴室 医务室 素斋"


def _build_context(scenic_id: str) -> str:
    """把景区专名表 + 通用问询词构造成识别上下文（上下文偏置）。"""
    from backend.asr.transcriber import SCENIC_HOTWORDS

    words = SCENIC_HOTWORDS.get(scenic_id, "")
    return f"景区语音导览中游客的提问。可能出现的专有名词：{words} {_COMMON_TERMS}".strip()


def _api_key() -> str:
    """优先 settings（.env 加载），环境变量兜底——与 LLM/TTS 共用同一把 Key。"""
    try:
        from backend.core.config import settings
        if settings.dashscope_api_key:
            return settings.dashscope_api_key
    except Exception:
        pass
    return os.environ.get("DASHSCOPE_API_KEY", "")


def _call(audio_path: str, scenic_id: str, language: str, model: str) -> dict:
    from dashscope import MultiModalConversation

    messages = [
        # system 文本即识别上下文：qwen3-asr 会据此偏置专名（不会把上下文念出来）
        {"role": "system", "content": [{"text": _build_context(scenic_id)}]},
        {"role": "user", "content": [{"audio": f"file://{os.path.abspath(audio_path)}"}]},
    ]
    asr_options = {"enable_itn": True}      # 逆文本归一化："八十八米"→"88米"
    if language in _SUPPORTED_LANG:
        asr_options["language"] = language  # 显式指定；"auto" 等则由模型自检

    resp = MultiModalConversation.call(
        api_key=_api_key(),
        model=model,
        messages=messages,
        result_format="message",
        asr_options=asr_options,
    )
    if getattr(resp, "status_code", None) != 200:
        raise RuntimeError(
            f"dashscope asr {getattr(resp, 'code', resp.status_code)}: "
            f"{getattr(resp, 'message', '')}"
        )

    msg = resp.output.choices[0].message
    content = msg.content if isinstance(msg.content, list) else [{"text": str(msg.content)}]
    text = "".join(c.get("text", "") for c in content if isinstance(c, dict)).strip()

    # annotations 里带检出语种/时长（不同版本字段名略有差异，全部宽松读取）
    lang, duration = language, 0.0
    for a in getattr(msg, "annotations", None) or []:
        if isinstance(a, dict):
            lang = a.get("language") or lang
            try:
                duration = float(a.get("duration") or a.get("audio_duration") or 0) or duration
            except (TypeError, ValueError):
                pass

    return {
        "text": text,
        "language": lang,
        "duration": round(duration, 2),
        "hotwords_used": True,
        "engine": "cloud",
    }


def transcribe_cloud(audio_path: str, scenic_id: str, language: str,
                     model: str, timeout: float) -> dict:
    """云端转写，超时抛 TimeoutError，其余失败抛原始异常；由调用方决定兜底。"""
    if not _api_key():
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")
    fut = _EXEC.submit(_call, audio_path, scenic_id, language, model)
    return fut.result(timeout=timeout)
