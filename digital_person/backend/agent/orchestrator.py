"""
调度中枢 Orchestrator：意图识别 + 路由决策。

混合策略（速度与准确兼顾）：
  1. 规则快筛：高频关键词秒级命中，0ms（见 intents.py）
  2. LLM 兜底：规则未命中、且问题模糊（短问题 + 有上下文）时，
     调 qwen-turbo 分类；否则默认走知识问答 qa。

这是把"多智能体"从架构叙事落地为真实代码的核心模块：
classify() 决定每轮请求交给哪条处理逻辑（见 handlers.py）。
"""

from backend.agent.intents import Intent, match_by_rules
from backend.llm.client import chat

_CLASSIFY_PROMPT = """你是景区导览系统的意图分类器。判断游客这句话属于以下哪一类，只输出一个英文标签，不要任何解释：

- qa：询问景点的历史、文化、数据等知识性问题
- navigation：询问游览路线、顺序、行程安排、怎么走
- recommend：寻求推荐（值得去的、适合的、拍照点、好吃的等）
- empathy：表达负面情绪、抱怨、求助、遇到困难
- chitchat：与景点无关的闲聊、问候、调侃

游客的话：{query}

标签："""

_VALID = {i.value for i in Intent}


def _classify_by_llm(query: str) -> Intent:
    """LLM 兜底分类。失败或输出异常时安全回退到 qa。"""
    try:
        label = chat(_CLASSIFY_PROMPT.format(query=query), [], "", fast=True).strip().lower()
        for v in _VALID:          # 容错：模型可能带多余字符，取首个合法标签
            if v in label:
                return Intent(v)
    except Exception:
        pass
    return Intent.QA


def _is_ambiguous(query: str, history: list[dict]) -> bool:
    """短问题 + 有上下文 → 模糊，值得 LLM 兜底；否则默认 qa 已足够。"""
    return len(query.strip()) < 8 and bool(history)


def classify(query: str, history: list[dict] | None = None) -> Intent:
    """
    返回本轮请求的意图。
    规则命中 → 直接返回（0ms）；未命中且模糊 → LLM 兜底；否则默认 qa。
    """
    history = history or []
    hit = match_by_rules(query)
    if hit is not None:
        return hit
    if _is_ambiguous(query, history):
        return _classify_by_llm(query)
    return Intent.QA
