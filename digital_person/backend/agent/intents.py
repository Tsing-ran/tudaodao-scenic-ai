"""
意图定义与关键词规则表。

Orchestrator 的"快筛"层：高频关键词秒级命中即路由（0ms），
未命中再交给 LLM 兜底（见 orchestrator.py）。
"""

from enum import Enum


class Intent(str, Enum):
    QA         = "qa"          # 知识问答（默认，走 RAG）
    NAVIGATION = "navigation"  # 路线规划
    RECOMMEND  = "recommend"   # 个性化推荐
    EMPATHY    = "empathy"     # 情感安抚 / 求助
    CHITCHAT   = "chitchat"    # 闲聊（跳过 RAG）


# 中文意图名（演示、日志、前端展示用）
INTENT_LABELS: dict["Intent", str] = {
    Intent.QA:         "知识问答",
    Intent.NAVIGATION: "路线规划",
    Intent.RECOMMEND:  "个性推荐",
    Intent.EMPATHY:    "情感安抚",
    Intent.CHITCHAT:   "闲聊互动",
}

# 关键词规则表。按列表顺序匹配，第一个命中的意图胜出。
# 顺序很重要：先判信号最强、最该优先处理的意图（情感安抚），
# 再到路线、推荐，最后闲聊。
_RULES: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.EMPATHY, (
        "排队", "太久", "好烦", "烦死", "累死", "好累", "投诉", "不满",
        "退票", "退钱", "找不到", "迷路", "怎么办", "帮帮", "太差",
        "失望", "生气", "差评", "态度",
    )),
    (Intent.NAVIGATION, (
        "怎么走", "怎么去", "怎么逛", "路线", "顺序", "先去", "导航", "线路",
        "行程", "攻略", "几个小时", "半天", "一天", "时间安排", "先逛", "路过",
        "从哪", "到哪",
    )),
    (Intent.RECOMMEND, (
        "推荐", "值得", "必去", "必看", "有什么好", "适合", "哪个好", "最好玩",
        "不容错过", "打卡", "拍照", "出片", "好吃的", "特产",
    )),
    (Intent.CHITCHAT, (
        "你叫什么", "你是谁", "你几岁", "你多大", "你会", "你能做", "你好呀",
        "无聊", "陪我", "讲个笑话", "唱歌", "你喜欢",
    )),
]


def match_by_rules(query: str) -> Intent | None:
    """关键词快筛。命中返回对应意图，未命中返回 None（交给 LLM 兜底）。"""
    for intent, keywords in _RULES:
        if any(kw in query for kw in keywords):
            return intent
    return None
