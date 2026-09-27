"""
通义千问 API 封装（DashScope）。

两个接口：
- chat()：文本对话，用 qwen-max-latest
- chat_stream()：流式输出，前端打字机效果用
"""

import re
from typing import AsyncGenerator, List
import dashscope
from dashscope import Generation

from backend.core.config import settings

dashscope.api_key = settings.dashscope_api_key

# 中文情绪标签 → 英文 key（数字人表情控制用）
_EMOTION_MAP = {
    "开心": "happy",
    "兴奋": "excited",
    "平静": "neutral",
    "好奇": "curious",
    "关切": "empathetic",
    "抱歉": "apologetic",
    "温暖": "empathetic",
    "温柔": "empathetic",
    "安慰": "empathetic",
    "耐心": "empathetic",
    "歉意": "apologetic",
    "抱歉地": "apologetic",
}
# 不锚定位置：情绪标签现在在正文前，但也兼容在末尾的旧格式
_EMOTION_RE = re.compile(
    r'\[\s*(?:情绪|emotion)\s*[：:]\s*([^\]\r\n]{1,20})\s*\]',
    re.IGNORECASE,
)

# 中文句子结束符
_SENTENCE_ENDERS = frozenset('。！？…!?')


def _llm_backend() -> str:
    return getattr(settings, "llm_backend", "dashscope")


def _local_llm_base() -> str:
    return getattr(settings, "local_llm_base", "http://127.0.0.1:11434/v1").rstrip("/")


def _local_llm_model() -> str:
    return getattr(settings, "local_llm_model", "qwen2.5:7b")


def extract_emotion(text: str) -> tuple[str, str]:
    """从文本中解析并剥离 [情绪:X] 标签（可在开头或结尾）。

    LLM 偶尔会输出未在提示白名单里的值，如 [情绪：温暖]。这类标签也必须从正文
    中删除，避免被前端展示或送入 TTS 读出来；未知值只影响表情兜底为 neutral。
    """
    m = _EMOTION_RE.search(text)
    if m:
        clean = _EMOTION_RE.sub("", text).strip()
        clean = re.sub(r'^\s*[\r\n]+', '', clean).strip()
        return clean, _EMOTION_MAP.get(m.group(1).strip(), "neutral")
    return text.strip(), "neutral"


def _get_model(fast: bool) -> str:
    """fast=True 用 fast_model（qwen-flash，首 token ~150ms），否则 qa 主模型（qwen-plus）。
    本地后端用 local_llm_model（单模型兼顾 qa/生成）。"""
    if _llm_backend() == "local":
        return _local_llm_model()
    return settings.fast_model if fast else settings.llm_model


# ── 本地 LLM 兜底分支（LLM_BACKEND=local）：OpenAI 兼容端点（Ollama/vLLM）──
# 云端路径完全不动；仅 llm_backend=local 时由 chat()/_raw_token_stream() 顶部切到这里。
def _local_chat(messages: List[dict]) -> str:
    import httpx
    r = httpx.post(
        f"{_local_llm_base()}/chat/completions",
        json={"model": _local_llm_model(), "messages": messages,
              "temperature": 0.7, "max_tokens": 1024, "stream": False},
        timeout=120, trust_env=False,   # trust_env=False 规避系统 SOCKS 代理坑
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def _local_token_stream(messages: List[dict]) -> AsyncGenerator[str, None]:
    import json as _json
    import httpx
    async with httpx.AsyncClient(timeout=120, trust_env=False) as cli:
        async with cli.stream(
            "POST", f"{_local_llm_base()}/chat/completions",
            json={"model": _local_llm_model(), "messages": messages,
                  "temperature": 0.7, "max_tokens": 1024, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = _json.loads(data)["choices"][0]["delta"].get("content")
                except Exception:  # noqa: BLE001
                    continue
                if delta:
                    yield delta


def chat(
    system_prompt: str,
    history: List[dict],
    user_message: str,
    fast: bool = False,
) -> str:
    """同步调用，返回完整回复文本。fast=True 延迟减半。"""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    if _llm_backend() == "local":
        return _local_chat(messages)

    response = Generation.call(
        model=_get_model(fast),
        messages=messages,
        result_format="message",
        temperature=0.7,
        max_tokens=1024,
    )
    if response.status_code != 200 or response.output is None:
        raise RuntimeError(
            f"DashScope 调用失败 [{response.status_code} {response.code}]: {response.message}"
        )
    return response.output.choices[0].message.content


async def _raw_token_stream(
    system_prompt: str,
    history: List[dict],
    user_message: str,
    fast: bool = False,
) -> AsyncGenerator[str, None]:
    """底层 token 流，供内部使用。"""
    import asyncio
    import threading

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    if _llm_backend() == "local":
        async for tok in _local_token_stream(messages):
            yield tok
        return

    # DashScope 的流式是同步阻塞 generator；若直接在 async 里 for 迭代会卡住
    # 事件循环，导致 FastAPI 无法逐块 flush SSE（表现为整段答案一次性到达）。
    # 解决：同步迭代放到线程里跑，token 经 asyncio.Queue 异步交回，事件循环不被阻塞。
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _produce():
        try:
            responses = Generation.call(
                model=_get_model(fast),
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,
                temperature=0.7,
                max_tokens=1024,
            )
            for resp in responses:
                if resp.status_code != 200 or resp.output is None:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        ("error", f"DashScope 流式失败 [{resp.status_code} {resp.code}]: {resp.message}"),
                    )
                    return
                delta = resp.output.choices[0].message.content
                if delta:
                    loop.call_soon_threadsafe(queue.put_nowait, ("token", delta))
        except Exception as e:  # noqa: BLE001
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    threading.Thread(target=_produce, daemon=True).start()

    while True:
        kind, val = await queue.get()
        if kind == "done":
            break
        if kind == "error":
            raise RuntimeError(val)
        yield val


async def chat_stream(
    system_prompt: str,
    history: List[dict],
    user_message: str,
    fast: bool = False,
) -> AsyncGenerator[dict, None]:
    """
    分句流式调用，yield 结构化事件 dict，供数字人驱动端使用：

      {"type": "emotion",  "value": "happy"}
          — 第一个事件，情绪已知，数字人立即设置表情

      {"type": "sentence", "text": "你好！欢迎来到灵山胜境～", "index": 0}
          — 每完整一句 yield 一次，TTS 收到即可开始合成

      {"type": "end",      "full_text": "...（已剥离情绪标签的干净正文）"}
          — 流结束，pipeline 用 full_text 做缓存/存库
    """
    buffer = ""
    full_text = ""
    sentence_idx = 0
    emotion_found = False

    async for token in _raw_token_stream(system_prompt, history, user_message, fast):
        buffer += token
        full_text += token

        # ── 优先探测情绪标签（出现即立刻 yield，不等到句子结束）────────
        if not emotion_found:
            m = _EMOTION_RE.search(buffer)
            if m:
                emotion_found = True
                yield {"type": "emotion", "value": _EMOTION_MAP.get(m.group(1).strip(), "neutral")}
                # 从 buffer 中移除标签，剩余内容继续分句处理
                buffer = _EMOTION_RE.sub("", buffer).lstrip("\n").lstrip()

        # ── 扫描 buffer，遇句子结束符就 yield 完整一句 ────────────────
        while True:
            end_pos = next(
                (i for i, ch in enumerate(buffer) if ch in _SENTENCE_ENDERS), -1
            )
            if end_pos == -1:
                break
            sentence = buffer[: end_pos + 1].strip()
            buffer = buffer[end_pos + 1 :]
            if sentence:
                yield {"type": "sentence", "text": sentence, "index": sentence_idx}
                sentence_idx += 1

    # ── 流结束：处理 buffer 尾部 ────────────────────────────────────
    # 兜底：LLM 未遵循"在前"指令，情绪标签出现在末尾
    if not emotion_found:
        m = _EMOTION_RE.search(buffer)
        if m:
            yield {"type": "emotion", "value": _EMOTION_MAP.get(m.group(1).strip(), "neutral")}
            buffer = _EMOTION_RE.sub("", buffer).strip()

    # 最后一句（无结束符的尾部文字）
    tail = _EMOTION_RE.sub("", buffer).strip()
    if tail:
        yield {"type": "sentence", "text": tail, "index": sentence_idx}

    clean_full_text, _ = extract_emotion(full_text)
    yield {"type": "end", "full_text": clean_full_text}
