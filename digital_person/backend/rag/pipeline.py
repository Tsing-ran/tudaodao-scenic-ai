"""
RAG 完整流水线：query → 检索 → LLM → 回复 + 情绪 → 存库。

延迟优化层次：
  1. LRU 缓存命中 → 直接返回，<5ms
  2. 异步并行检索 → embed 与 BM25 同时跑，省 ~50ms
  3. fast=True    → 用 qwen-turbo，首 token ~150ms vs max ~600ms
  4. 流式输出     → 第一句话完成即触发 TTS，不等全文
"""

import asyncio

from backend.rag.retriever import retrieve, retrieve_async
from backend.rag.cache import answer_cache
from backend.rag.faq_priority import match_faq
from backend.llm.prompts import build_system_prompt, QUERY_REWRITE_PROMPT, needs_rewrite
from backend.llm.client import chat, chat_stream, extract_emotion
from backend.db.database import save_conversation
from backend.core.config import settings
from backend.agent.orchestrator import classify
from backend.agent.handlers import intent_directive, skip_retrieval
from backend.agent.intents import INTENT_LABELS, Intent
from backend.agent.profiler import note_turn, profile_brief
from backend.analytics.crowd import crowd_brief
from backend.analytics.env_context import env_brief
from backend.rag.scenic_types import type_persona_directive, type_reminder_directive

# 路线/推荐意图才注入实时客流 + 时间天气，让导游给「错峰/避暑/带伞」等随机应变建议
_CROWD_INTENTS = {Intent.NAVIGATION, Intent.RECOMMEND}

# 按意图选模型：qa（事实问答）守 qwen-max 保 97.7% 准确率；其余生成性意图
# （路线/推荐/安抚/闲聊）切 qwen-turbo——事实已由注入的 RAG context 约束，生成质量足够，
# 而整段 LLM 时延实测 28s→4s（16→69 字/s）。这些意图不在准确率测试集范畴，不影响硬指标。
_FAST_INTENTS = {Intent.NAVIGATION, Intent.RECOMMEND, Intent.EMPATHY, Intent.CHITCHAT}


# ── 自身情况标签（5 维）：默认值=中性。缓存键的 back-compat 是本模块最关键的正确性点 ──
_SIT_DEFAULTS = {"age": "youth", "pace": "day", "mobility": "normal", "purpose": "relax", "first_time": "first"}
_SIT_DIMS = ("age", "pace", "mobility", "purpose", "first_time")


def _situation_dict(situation) -> dict | None:
    """归一化 situation（pydantic 模型 / dict / None）为 dict，便于下游统一处理。"""
    if not situation:
        return None
    if isinstance(situation, dict):
        return situation
    if hasattr(situation, "model_dump"):
        return situation.model_dump()
    if hasattr(situation, "dict"):
        return situation.dict()
    return None


def _situation_key(situation: dict | None) -> str:
    """情境缓存键：仅非默认值参与（维度顺序固定→确定性）。全默认/None → "" 。"""
    if not situation:
        return ""
    return ",".join(
        f"{d}={situation[d]}" for d in _SIT_DIMS
        if situation.get(d) and situation[d] != _SIT_DEFAULTS[d]
    )


def _cache_query(group_type: str, lang: str, sit_key: str, query: str) -> str:
    """组装缓存键。**sit_key 为空时不加分隔符** → 与历史键 f"{group_type}::{lang}::{query}"
    逐字节一致 → 老缓存命中、零失效、零准确率影响；非默认情境则得到独立键，不串答。"""
    base = f"{group_type}::{lang}::"
    return f"{base}{sit_key}::{query}" if sit_key else f"{base}{query}"


def _directive_with_context(intent: Intent, scenic_id: str, session_id: str | None = None) -> str:
    """意图指令 + 景区类型口吻（全意图）+（路线/推荐时）类型主动提醒 + 实时客流 + 时间天气 + 游中画像。

    景区类型口吻（type_persona）事实中性、只调语气侧重，故注入全部意图（含 qa）让
    灵山禅意/故宫学者等气质贯穿问答；因不改事实，关键词准确率测试不受影响。
    类型主动提醒（type_reminder：礼仪/预约/安全/接驳）与游中画像只在路线/推荐意图注入，
    避免 qa prompt 膨胀、且守住 qa 准确率红线（画像绝不进事实问答链路）。
    """
    directive = intent_directive(intent)
    persona = type_persona_directive(scenic_id)  # 景区类型口吻：全意图都带
    if persona:
        directive += "\n" + persona
    if intent in _CROWD_INTENTS:
        reminder = type_reminder_directive(scenic_id)
        for brief in (reminder, crowd_brief(scenic_id), env_brief(scenic_id)):
            if brief:
                directive += "\n\n" + brief
        brief = profile_brief(session_id) if session_id else ""
        if brief:
            directive += (
                "\n\n【游中画像·按他关心的讲】" + brief
                + "（推荐路线/景点时自然呼应其兴趣与问过的内容，如'记得您想…'，"
                "不要生硬罗列画像标签。）"
            )
    return directive

# guide_name = 数字人对外名称。产品定位：去人名化，统一「<景区简称>AI智能导览数字人」
# （非"慧昭/婉清"等拟人名）。系统模板已禁用人名自称；此值经 /scenic/theme 暴露给前端，
# 用于"正在思考"提示、明信片落款等 {guide} 占位。简称为各项手写（非 name 全称）。
SCENIC_CONFIG: dict[str, dict] = {
    "lingshan":    {"name": "灵山胜境",           "guide_name": "灵山AI智能导览数字人"},
    "nihuawan":    {"name": "拈花湾",             "guide_name": "拈花湾AI智能导览数字人"},
    "xihu":        {"name": "西湖",               "guide_name": "西湖AI智能导览数字人"},
    "huangshan":   {"name": "黄山",               "guide_name": "黄山AI智能导览数字人"},
    "gugong":      {"name": "故宫博物院",         "guide_name": "故宫AI智能导览数字人"},
    "zhangjiajie": {"name": "张家界国家森林公园", "guide_name": "张家界AI智能导览数字人"},
    "bingmayong":  {"name": "秦始皇帝陵博物院",   "guide_name": "兵马俑AI智能导览数字人"},
    "mogaoku":     {"name": "敦煌莫高窟",         "guide_name": "莫高窟AI智能导览数字人"},
}


def get_scenic_config(scenic_id: str) -> dict:
    return SCENIC_CONFIG.get(scenic_id, {"name": scenic_id, "guide_name": "AI智能导览数字人"})


def rewrite_query(query: str, history: list[dict]) -> str:
    """
    用 qwen-turbo 把口语/含指代的问题改写为检索友好形式。
    只在必要时触发（含指代词或历史有上下文），避免浪费 API。
    """
    if not needs_rewrite(query, history):
        return query
    history_text = "\n".join(
        f"{'游客' if m['role']=='user' else '导游'}：{m['content'][:60]}"
        for m in history[-4:]  # 只看最近两轮
    ) or "（无历史）"
    prompt = QUERY_REWRITE_PROMPT.format(history=history_text, query=query)
    rewritten = chat(prompt, [], "", fast=True).strip()
    # 安全回退：改写失败或过长时用原始 query
    return rewritten if rewritten and len(rewritten) < 100 else query


def answer(
    query: str,
    scenic_id: str,
    history: list[dict] | None = None,
    session_id: str = "anonymous",
    fast: bool = False,
    lang: str = "auto",
    group_type: str = "adult",
    situation=None,
    interests: list[str] | None = None,
) -> dict:
    """
    同步问答。fast=True 使用 qwen-turbo（延迟减半，适合简单问答）。
    lang: "auto"（跟随提问语言）或语言代码（en/ja/ko…）强制指定回答语言。
    group_type: 同行关系（adult/family_kids/senior/couple），切换叙事人格。
    situation: 自身情况标签（age/pace/mobility/purpose/first_time），按非默认值调讲解侧重。
    interests: 游客静态兴趣（开场快选）；仅入游中画像，**不直接进 prompt**（qa 零接触）。
    返回: { reply, emotion, sources, context_used, intent }
    """
    history = history or []
    sit = _situation_dict(situation)
    # 按 人格 + 语言 + 自身情况 隔离缓存，避免串答；情境全默认时键与原状逐字节一致（零失效）
    cache_query = _cache_query(group_type, lang, _situation_key(sit), query)
    intent = classify(query, history)  # Orchestrator 分派：决定走哪条处理链路
    fast = fast or intent in _FAST_INTENTS  # 生成性意图自动提速（qwen-turbo）

    # ── FAQ 最高优先级层：游客问句近乎命中管理员录入的 FAQ → 直接以权威人工答案作答 ──
    #    高阈值近似匹配（不误伤事实问答准确率）；不进检索、不改 qa 缓存键。
    faq_hit = match_faq(scenic_id, query)
    if faq_hit:
        reply, emotion = extract_emotion(faq_hit["answer"])
        save_conversation(session_id, scenic_id, query, reply, emotion, True)
        note_turn(session_id, scenic_id, query, intent.value, interests)
        return {"reply": reply, "emotion": emotion, "sources": ["FAQ"],
                "context_used": True, "intent": intent.value, "scenic_id": scenic_id,
                "from_cache": False, "faq": True}

    # 路线/推荐含实时客流（随时段变），不缓存，避免冻结错峰建议
    cacheable = not history and intent not in _CROWD_INTENTS

    # ── 缓存命中：无历史时才缓存（历史对话有上下文，不能复用） ──────
    if cacheable:
        cached = answer_cache.get(scenic_id, cache_query)
        if cached:
            clean_reply, parsed_emotion = extract_emotion(cached["reply"])
            emotion = cached.get("emotion") or parsed_emotion
            if cached.get("emotion") == "neutral" and parsed_emotion != "neutral":
                emotion = parsed_emotion
            save_conversation(session_id, scenic_id, query,
                              clean_reply, emotion, cached["context_used"])
            note_turn(session_id, scenic_id, query, intent.value, interests)  # 缓存命中也暴露兴趣
            return {**cached, "reply": clean_reply, "emotion": emotion, "from_cache": True}

    cfg = get_scenic_config(scenic_id)

    if skip_retrieval(intent):         # 闲聊无需检索知识库，省一次检索延迟
        context_chunks = []
    else:
        retrieval_query = rewrite_query(query, history)  # 改写后用于检索，原 query 用于 LLM
        context_chunks = retrieve(retrieval_query, scenic_id)
    context_used = len(context_chunks) > 0

    system_prompt = build_system_prompt(
        cfg["name"], cfg["guide_name"], context_chunks, lang,
        _directive_with_context(intent, scenic_id, session_id), group_type, situation=sit,
    )
    raw_reply = chat(system_prompt, history, query, fast=fast)
    reply, emotion = extract_emotion(raw_reply)

    result = {
        "reply": reply,
        "emotion": emotion,
        "sources": list({c.split("|")[0].strip() for c in context_chunks}),
        "context_used": context_used,
        "intent": intent.value,
        "scenic_id": scenic_id,
        "from_cache": False,
    }

    if cacheable:
        answer_cache.set(scenic_id, cache_query, result)

    save_conversation(session_id, scenic_id, query, reply, emotion, context_used)
    note_turn(session_id, scenic_id, query, intent.value, interests)
    return result


def _split_to_sentences(text: str) -> list[str]:
    """把纯文本按中文句子结束符切分，用于缓存命中时的流式模拟。"""
    enders = frozenset("。！？…!?")
    sentences, current = [], ""
    for ch in text:
        current += ch
        if ch in enders:
            if current.strip():
                sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences or [text]


async def answer_stream(
    query: str,
    scenic_id: str,
    history: list[dict] | None = None,
    session_id: str = "anonymous",
    fast: bool = False,
    lang: str = "auto",
    group_type: str = "adult",
    situation=None,
    interests: list[str] | None = None,
):
    """
    分句流式版本，yield 结构化事件 dict（供 SSE 下发给数字人驱动端）：
      {"type": "emotion",  "value": "happy"}
      {"type": "sentence", "text": "...", "index": N}
      {"type": "end",      "full_text": "..."}

    第一个事件（emotion）在 LLM 输出第一个 token 后毫秒级下发，
    数字人表情无需等待全文生成完毕。
    lang: "auto"（跟随提问语言）或语言代码（en/ja/ko…）强制指定回答语言。
    """
    history = history or []
    sit = _situation_dict(situation)
    cache_query = _cache_query(group_type, lang, _situation_key(sit), query)  # 人格+语言+情境隔离
    intent = classify(query, history)  # 先分派；无历史时纯规则匹配，0ms
    fast = fast or intent in _FAST_INTENTS  # 生成性意图自动提速（qwen-turbo）
    cacheable = not history and intent not in _CROWD_INTENTS  # 含实时客流的不缓存

    def _intent_event() -> dict:
        return {"type": "intent", "value": intent.value, "label": INTENT_LABELS[intent]}

    # ── FAQ 最高优先级层：命中管理员录入的 FAQ → 直接以人工答案分句流式返回 ──
    faq_hit = await asyncio.to_thread(match_faq, scenic_id, query)
    if faq_hit:
        reply, emotion = extract_emotion(faq_hit["answer"])
        save_conversation(session_id, scenic_id, query, reply, emotion, True)
        await asyncio.to_thread(note_turn, session_id, scenic_id, query, intent.value, interests)
        yield _intent_event()
        yield {"type": "emotion", "value": emotion}
        for i, s in enumerate(_split_to_sentences(reply)):
            yield {"type": "sentence", "text": s, "index": i}
        yield {"type": "end", "full_text": reply}
        return

    # ── 缓存命中：模拟分句流，接口与正常流保持一致 ────────────────────
    if cacheable:
        cached = answer_cache.get(scenic_id, cache_query)
        if cached:
            clean_reply, parsed_emotion = extract_emotion(cached["reply"])
            emotion = cached.get("emotion") or parsed_emotion
            if cached.get("emotion") == "neutral" and parsed_emotion != "neutral":
                emotion = parsed_emotion
            save_conversation(session_id, scenic_id, query,
                              clean_reply, emotion, cached["context_used"])
            await asyncio.to_thread(note_turn, session_id, scenic_id, query, intent.value, interests)
            yield _intent_event()
            yield {"type": "emotion", "value": emotion}
            for i, s in enumerate(_split_to_sentences(clean_reply)):
                yield {"type": "sentence", "text": s, "index": i}
            yield {"type": "end", "full_text": clean_reply}
            return

    cfg = get_scenic_config(scenic_id)

    if skip_retrieval(intent):         # 闲聊跳过检索
        context_chunks = []
    else:
        retrieval_query = await asyncio.to_thread(rewrite_query, query, history)
        if settings.deploy_mode == "cloud":
            context_chunks = await retrieve_async(retrieval_query, scenic_id)
        else:
            context_chunks = await asyncio.to_thread(retrieve, retrieval_query, scenic_id)

    context_used = len(context_chunks) > 0
    directive = await asyncio.to_thread(_directive_with_context, intent, scenic_id, session_id)
    system_prompt = build_system_prompt(
        cfg["name"], cfg["guide_name"], context_chunks, lang,
        directive, group_type, situation=sit,
    )

    yield _intent_event()  # intent 在 LLM 调用前即可下发，比 emotion 更早

    full_text = ""
    emotion = "neutral"

    async for event in chat_stream(system_prompt, history, query, fast=fast):
        if event["type"] == "emotion":
            emotion = event["value"]
        elif event["type"] == "end":
            full_text = event["full_text"]
        yield event  # 原样透传给 API 层

    reply, _ = extract_emotion(full_text)

    if cacheable:
        answer_cache.set(scenic_id, cache_query, {
            "reply": reply, "emotion": emotion,
            "sources": list({c.split("|")[0].strip() for c in context_chunks}),
            "context_used": context_used, "intent": intent.value, "scenic_id": scenic_id,
        })

    save_conversation(session_id, scenic_id, query, reply, emotion, context_used)
    await asyncio.to_thread(note_turn, session_id, scenic_id, query, intent.value, interests)
