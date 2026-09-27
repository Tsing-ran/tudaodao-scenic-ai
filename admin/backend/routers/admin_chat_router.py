"""景区运营智能代理（管理端「数据分析助手」升级版）。

从"读一份静态数据快照后聊天"升级为**工具调用代理**：
  1. 按需实时调用各类运营数据接口（客流/情感/知识空缺/推荐/画像/消费/FAQ…），
     而非固定喂一份 5 分钟缓存快照——问什么查什么，数据永远最新。
  2. 除了解读，还能**主动建议可执行的运营动作**：起草应急广播 / 建议新增 FAQ。
     动作经"抽取pass"从答复中结构化提取，SSE 下发前端渲染成确认卡，管理员点按确认后才执行。

SSE 事件（向后兼容旧前端：旧前端只认 data:{text}/[DONE]，其余静默忽略）：
  data: {"status": "正在查询实时客流…"}   # 工具调用进度
  data: {"text": "..."}                    # 最终答复增量
  data: {"action": {...}}                  # 建议动作卡（broadcast / add_faq）
  data: [DONE]

任一环节异常 → 回退到静态快照流式（保证不假死）。
"""
import asyncio
import json

import dashscope
import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

ANALYTICS_BASE = "http://127.0.0.1:6006/rag"
_MODEL = "qwen-plus"
_MAX_ROUNDS = 5
_TOOL_TIMEOUT = 14.0

# ── 只读数据工具：名 → 相对 URL 模板。{sc}=scenic_id ──────────────────────
_READ_TOOLS = {
    "get_overview":        "/analytics/bi/overview?scenic_id={sc}",
    "get_dashboard":       "/analytics/dashboard?scenic_id={sc}&days=7",
    "get_crowd":           "/analytics/crowd?scenic_id={sc}",
    "get_sentiment":       "/analytics/sentiment-trend?scenic_id={sc}",
    "get_knowledge_gaps":  "/analytics/knowledge-gaps?scenic_id={sc}",
    "get_reco_performance":"/analytics/reco-performance?scenic_id={sc}&days=7",
    "get_feature_usage":   "/analytics/feature-usage?scenic_id={sc}&days=7",
    "get_profile":         "/analytics/profile?scenic_id={sc}&days=7",
    "get_topic_intents":   "/analytics/topic-intents?scenic_id={sc}&days=30&limit=8",
    "get_demographics":    "/analytics/bi/demographics?scenic_id={sc}",
    "get_spending":        "/analytics/bi/spending?scenic_id={sc}",
    # ── 消费分析→营销决策（数据源=赛题行为数据真实样本，real_only 口径）──
    "get_spend_tiers":       "/analytics/bi/spend-tiers?scenic_id={sc}",
    "get_spend_drivers":     "/analytics/bi/spend-drivers?scenic_id={sc}",
    "get_satisfaction_value":"/analytics/bi/satisfaction-value?scenic_id={sc}",
    "get_spend_trend":       "/analytics/bi/spend-trend?scenic_id={sc}",
    "get_marketing_advice":  "/analytics/bi/marketing-advice?scenic_id={sc}",
    "list_faq":            "/kb/faq?scenic_id={sc}",
}

_READ_DESC = {
    "get_overview": "景区总览KPI：服务游客数、人均消费、营收、平均满意度/停留时长/同行规模",
    "get_dashboard": "运营概览：对话总量、会话数、满意度、上下文命中率、情感分布、每日趋势",
    "get_crowd": "实时客流压力：各景点当前拥挤指数、高峰/低谷、下一场演出",
    "get_sentiment": "情感趋势：逐日满意度与正/负面情感占比、总体满意度",
    "get_knowledge_gaps": "知识空缺：游客问了但答不出的问题（按频次排序）",
    "get_reco_performance": "推荐效果：曝光/点击/点击率、热门推荐项、动作分布",
    "get_feature_usage": "功能使用：各功能打开次数、平均评分、活跃会话数",
    "get_profile": "客群画像：同行关系/语言/兴趣分布、动态兴趣、游览风格、未满足需求",
    "get_topic_intents": "热门话题意图分布（近30天问题的意图分类TOP）",
    "get_demographics": "客群结构：年龄段/性别/同行规模分布（行为数据）",
    "get_spending": "消费结构：各消费品类占比、客单价、总花费分布",
    "get_spend_tiers": "客单价分层：低/中/高消费人群占比、各层营收贡献占比与画像（识别高价值客群，如少数高消费撬动多数营收）",
    "get_spend_drivers": "消费驱动因子：不同停留时长/同行规模的客单价均值（支撑延长停留、家庭/团队套票等决策）",
    "get_satisfaction_value": "满意度×消费四象限：定位高消费但低满意的营收风险客群",
    "get_spend_trend": "消费趋势：按月客流/客单价/营收走势（淡旺季营销节奏）",
    "get_marketing_advice": "规则化营销决策建议（洞察→建议→预期，数字均来自真实消费样本）",
    "list_faq": "当前已录入的FAQ问答清单",
}

_STATUS_HINT = {
    "get_crowd": "正在查询实时客流…", "get_sentiment": "正在分析游客情感趋势…",
    "get_knowledge_gaps": "正在梳理知识空缺…", "get_overview": "正在读取运营总览…",
    "get_dashboard": "正在读取运营概览…", "get_reco_performance": "正在核算推荐效果…",
    "get_feature_usage": "正在统计功能使用…", "get_profile": "正在分析客群画像…",
    "get_topic_intents": "正在归类热门话题…", "get_demographics": "正在读取客群结构…",
    "get_spending": "正在读取消费结构…", "list_faq": "正在查阅FAQ清单…",
    "get_spend_tiers": "正在分层客单价…", "get_spend_drivers": "正在拆解消费驱动因子…",
    "get_satisfaction_value": "正在定位消费风险客群…", "get_spend_trend": "正在分析消费趋势…",
    "get_marketing_advice": "正在生成营销决策建议…",
}

SYSTEM_AGENT = """你是景区运营智能代理，服务对象是景区管理人员（不是游客）。你不仅解读数据，更要给出可落地的运营决策支持。

工作方式：
- 你可以调用工具实时获取各类运营数据（客流、情感、知识空缺、推荐效果、客群画像、消费结构、FAQ 等）。回答前先想清楚需要哪些数据，按需调用，不要臆造数字。
- **消费分析→营销决策**：涉及消费、客单价、营收、高价值客群、套票、淡旺季、营销时，调用 get_spend_tiers（客单价分层与营收贡献）、get_spend_drivers（停留/同行规模驱动）、get_satisfaction_value（消费风险客群）、get_spend_trend（趋势）、get_marketing_advice（规则化建议）。这些数字均来自赛题《景点景区旅游数据行为分析数据》真实样本，可作为决策依据；引用时可点出关键洞察（如"高消费客群人数占比小却贡献过半营收"）。
- 一次可以调用多个工具；数据取齐后再综合作答。
- 当情况需要即时干预时，在答复中明确给出应急广播文案（用引号括出可直接播报的话）；当发现游客反复问而知识库答不好时，明确列出建议新增的问答（问题+建议答案）。系统会自动把这些建议整理成确认卡交管理员点按执行。

回答要求：中文，简洁专业，结论先行，给出可执行建议。正文控制在 250 字内。可用简短 Markdown（小标题/要点/加粗）。不要罗列原始 JSON。"""

SYSTEM_FALLBACK = "你是景区管理系统的AI智能分析助手，帮助管理员做数据分析与运营决策。简洁专业，给可落地建议，200字内。"

# 抽取pass：从答复里结构化提取"建议动作"，比让模型自己 tool-call 稳定得多
_EXTRACT_PROMPT = """你是运营动作抽取器。下面是运营代理给景区管理员的答复。请判断答复中是否**明确建议**了以下两类动作，并抽取为 JSON：
1. 应急广播：答复建议向游客即时播报某段话 → broadcast:{text:可直接播报的完整文案(≤60字), emotion:"concerned"|"neutral"|"happy"}
2. 新增FAQ：答复建议补充某些问答 → faqs:[{question, answer:建议答案草稿, category}]
只输出严格 JSON：{"broadcast": {...}或null, "faqs": [...]}。答复没有明确建议对应动作就给 null / 空数组，不要臆造。

答复原文：
"""

_ACTION_HINT = ("广播", "播报", "faq", "FAQ", "问答", "补充", "新增", "建议")


def _tool_specs() -> list:
    return [{"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": {}},
    }} for name, desc in _READ_DESC.items()]


async def _fetch_tool(client: httpx.AsyncClient, name: str, scenic_id: str) -> str:
    url = ANALYTICS_BASE + _READ_TOOLS[name].format(sc=scenic_id)
    try:
        r = await client.get(url, timeout=_TOOL_TIMEOUT)
        if r.status_code != 200:
            return json.dumps({"error": f"HTTP {r.status_code}"}, ensure_ascii=False)
        data = r.json()
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    s = json.dumps(data, ensure_ascii=False)
    return s if len(s) <= 2400 else s[:2400] + "…(truncated)"


def _extract_actions_sync(content: str) -> list:
    """对最终答复跑一次轻量抽取，得到结构化建议动作卡。"""
    if not content or not any(k in content for k in _ACTION_HINT):
        return []
    try:
        resp = dashscope.Generation.call(
            model="qwen-flash", result_format="message",
            messages=[{"role": "user", "content": _EXTRACT_PROMPT + content}])
        if resp.status_code != 200:
            return []
        raw = (resp.output.choices[0].message.get("content") or "").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception:
        return []
    actions = []
    bc = data.get("broadcast")
    if isinstance(bc, dict) and (bc.get("text") or "").strip():
        actions.append({"type": "broadcast", "text": bc["text"].strip(),
                        "emotion": bc.get("emotion") or "concerned"})
    faqs = [f for f in (data.get("faqs") or [])
            if isinstance(f, dict) and (f.get("question") or "").strip()]
    if faqs:
        actions.append({"type": "add_faq", "items": [
            {"question": f.get("question", "").strip(), "answer": f.get("answer", "").strip(),
             "category": f.get("category", "") or ""} for f in faqs[:6]]})
    return actions


class Message(BaseModel):
    role: str
    content: str


class AdminChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    scenic_id: Optional[str] = None


def _sse(obj) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def admin_chat(req: AdminChatRequest):
    dashscope.api_key = settings.DASHSCOPE_API_KEY
    scenic_id = req.scenic_id or "lingshan"

    messages = [{"role": "system", "content": SYSTEM_AGENT}]
    for m in req.history[-12:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    async def _finalize(content: str):
        for i in range(0, len(content), 18):
            yield _sse({"text": content[i:i + 18]})
            await asyncio.sleep(0.012)
        for act in await asyncio.to_thread(_extract_actions_sync, content):
            yield _sse({"action": act})
        yield "data: [DONE]\n\n"

    async def agent_stream():
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                for _round in range(_MAX_ROUNDS):
                    resp = await asyncio.to_thread(
                        dashscope.Generation.call,
                        model=_MODEL, messages=messages, tools=_tool_specs(),
                        result_format="message")
                    if resp.status_code != 200:
                        raise RuntimeError(getattr(resp, "message", "LLM error"))
                    msg = resp.output.choices[0].message
                    tool_calls = msg.get("tool_calls") or []
                    if not tool_calls:
                        async for ev in _finalize(msg.get("content") or ""):
                            yield ev
                        return
                    messages.append({"role": "assistant", "content": msg.get("content") or "",
                                     "tool_calls": tool_calls})
                    for tc in tool_calls:
                        name = (tc.get("function", {}) or {}).get("name", "")
                        if name in _READ_TOOLS:
                            yield _sse({"status": _STATUS_HINT.get(name, "正在查询数据…")})
                            result = await _fetch_tool(client, name, scenic_id)
                        else:
                            result = json.dumps({"error": "unknown tool"}, ensure_ascii=False)
                        messages.append({"role": "tool", "name": name,
                                         "tool_call_id": tc.get("id", name), "content": result})
                # 轮数用尽 → 纯文本收尾
                resp = await asyncio.to_thread(
                    dashscope.Generation.call, model=_MODEL, messages=messages, result_format="message")
                content = resp.output.choices[0].message.get("content") or "" if resp.status_code == 200 else ""
                async for ev in _finalize(content):
                    yield ev
                return
        except Exception:
            async for ev in _fallback_stream(req):
                yield ev

    return StreamingResponse(agent_stream(), media_type="text/event-stream")


async def _fallback_stream(req: AdminChatRequest):
    messages = [{"role": "system", "content": SYSTEM_FALLBACK}]
    for m in req.history[-8:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    def _gen():
        try:
            responses = dashscope.Generation.call(
                model=_MODEL, messages=messages, stream=True, incremental_output=True)
            for r in responses:
                if r.status_code == 200:
                    text = r.output.get("text", "")
                    if text:
                        yield _sse({"text": text})
                else:
                    yield _sse({"error": f"调用失败: {getattr(r, 'message', '')}"})
                    break
        except Exception as e:
            yield _sse({"error": str(e)})
        yield "data: [DONE]\n\n"

    for chunk in _gen():
        yield chunk
