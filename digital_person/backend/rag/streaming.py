"""
流式 RAG 流水线：LLM 生成第一句话就立即推送给 TTS，不等完整回复。

时序图：
  LLM:  [句1生成完]→[句2生成中...]→[句3生成中...]
  TTS:        [句1合成]→[句2合成]→[句3合成]
  数字人:          [句1播放]→[句2播放]→[句3播放]

这样用户听到第一句话的延迟 ≈ RAG检索 + LLM首句生成 + TTS首句合成
≈ 0.3s + 0.8s + 0.4s = 1.5s（GPU状态下）
"""

import re
import asyncio
from typing import AsyncGenerator

from backend.rag.retriever import retrieve
from backend.llm.prompts import build_system_prompt
from backend.llm.client import chat_stream
from backend.rag.pipeline import get_scenic_config

# 句子分隔符：遇到这些符号就认为一句话结束，立即送给 TTS
_SENTENCE_END = re.compile(r'([。！？!?…]+|\.{2,})')


async def stream_sentences(
    query: str,
    scenic_id: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """
    按句子流式输出，每完成一句就 yield 一次。
    队友的 TTS 模块订阅这个流，每收到一句就立即合成音频。

    yield 格式:
        {"type": "sentence", "text": "这是一句话"}
        {"type": "done", "full_text": "完整回复"}
    """
    history = history or []
    cfg = get_scenic_config(scenic_id)

    context_chunks = retrieve(query, scenic_id)
    system_prompt = build_system_prompt(
        scenic_name=cfg["name"],
        guide_name=cfg["guide_name"],
        context_chunks=context_chunks,
    )

    buffer = ""
    full_text = ""

    async for token in chat_stream(system_prompt, history, query):
        buffer += token
        full_text += token

        # 检测句子边界
        match = _SENTENCE_END.search(buffer)
        while match:
            end_pos = match.end()
            sentence = buffer[:end_pos].strip()
            if sentence:
                yield {"type": "sentence", "text": sentence}
            buffer = buffer[end_pos:]
            match = _SENTENCE_END.search(buffer)

    # 输出剩余不完整的句子
    if buffer.strip():
        yield {"type": "sentence", "text": buffer.strip()}

    yield {"type": "done", "full_text": full_text}
