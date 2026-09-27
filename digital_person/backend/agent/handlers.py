"""
各意图的处理策略：为不同意图注入不同的"任务指令"到 system prompt。

qa 走默认行为（指令为空）；其余意图追加针对性的导游话术要求。
这样同一套 RAG + LLM 链路，能对不同诉求给出差异化、有温度的回应。
"""

from backend.agent.intents import Intent

_DIRECTIVES: dict[Intent, str] = {
    Intent.NAVIGATION: (
        "\n【本轮任务：路线规划】游客在咨询游览路线。请结合知识库中的路线/景点信息，"
        "给出清晰的游览顺序，包含：建议路线、各点停留时间、景点之间的衔接讲解。"
        "若游客提到时间（半天/一天）或同行情况，据此调整路线松紧。\n"
    ),
    Intent.RECOMMEND: (
        "\n【本轮任务：个性化推荐】游客在寻求推荐。请基于知识库内容推荐 2-4 个景点/活动，"
        "每条说明推荐理由（有什么特别）。若游客提到偏好（拍照/亲子/文化），优先匹配。\n"
    ),
    Intent.EMPATHY: (
        "\n【本轮任务：情感安抚】游客可能情绪不佳或遇到困难。请首先共情、安抚，语气温暖耐心，"
        "再给出实际可行的帮助或建议。情绪标签优先选 [情绪:关切]。\n"
    ),
    Intent.CHITCHAT: (
        "\n【本轮任务：闲聊互动】游客在和你闲聊。请以亲切活泼的导游人格自然回应，简短友好，"
        "适度把话题引回景区游览，但不必生硬。无需引用知识库。\n"
    ),
}


def intent_directive(intent: Intent) -> str:
    """返回意图对应的任务指令（注入 system prompt）。qa 返回空字符串。"""
    return _DIRECTIVES.get(intent, "")


def skip_retrieval(intent: Intent) -> bool:
    """闲聊无需检索知识库，省一次检索延迟。"""
    return intent == Intent.CHITCHAT
