"""
数据分析接口，供管理后台数据大屏调用。

GET /analytics/dashboard       — 核心运营数据（总量、情绪分布、每日趋势）
GET /analytics/hot-topics      — 游客热门问题词云
GET /analytics/sentiment-trend — 满意度按天趋势
GET /analytics/conversations   — 历史对话列表（分页）
POST /analytics/report         — LLM 生成游客感受度报告（按需调用）
POST /analytics/event          — 游客端主动上报行为事件（画像/功能/到访/满意度）
GET /analytics/profile         — 客群画像（同行类型/语言/静态+动态兴趣/游览风格/未满足需求）
GET /analytics/feature-usage   — 功能使用率 + 满意度
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.database import get_db, save_event
from backend.llm.client import chat
from backend.analytics.crowd import scenic_crowd

router = APIRouter(prefix="/analytics", tags=["analytics"])

# 满意情绪：happy + excited；负面：apologetic
_POSITIVE = {"happy", "excited"}
_NEUTRAL  = {"neutral", "curious"}
_NEGATIVE = {"empathetic", "apologetic"}


def _date_range(days: int) -> str:
    """返回 SQLite 可用的最早日期字符串。"""
    start = datetime.now() - timedelta(days=days)
    return start.strftime("%Y-%m-%d %H:%M:%S")


# ── 客流热度感知（真实行为数据 + 时段模型，供导游错峰建议 & 数据大屏） ──
@router.get("/crowd")
def crowd(scenic_id: str = "lingshan"):
    """某景区当前客流热度：各景点拥挤档位 + 旺淡季 + 错峰时段。

    热门度/满意度/季节性来自真实游客行为数据（14 万行）；当前时段拥挤度为模型估计
    （原始数据无小时维度）。黄山/故宫不在数据中，返回 has_data=false。
    """
    return scenic_crowd(scenic_id)


# ── 1. 数据大屏核心数据 ────────────────────────────────────────────
@router.get("/dashboard")
def dashboard(scenic_id: str = "lingshan", days: int = 7):
    since = _date_range(days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE scenic_id=? AND created_at>=? ORDER BY created_at",
            (scenic_id, since),
        ).fetchall()

    total = len(rows)
    sessions = len({r["session_id"] for r in rows})

    emotion_dist = Counter(r["emotion"] for r in rows)
    context_hits = sum(1 for r in rows if r["context_used"])

    # 每日统计
    daily: dict[str, dict] = {}
    for r in rows:
        day = r["created_at"][:10]
        if day not in daily:
            daily[day] = {"date": day, "conversations": 0, "sessions": set()}
        daily[day]["conversations"] += 1
        daily[day]["sessions"].add(r["session_id"])
    daily_list = [
        {"date": d["date"], "conversations": d["conversations"], "sessions": len(d["sessions"])}
        for d in sorted(daily.values(), key=lambda x: x["date"])
    ]

    positive = sum(emotion_dist.get(e, 0) for e in _POSITIVE)
    satisfaction = round(positive / total, 3) if total else 0.0

    return {
        "scenic_id": scenic_id,
        "period_days": days,
        "total_conversations": total,
        "total_sessions": sessions,
        "satisfaction_rate": satisfaction,
        "context_hit_rate": round(context_hits / total, 3) if total else 0.0,
        "emotion_distribution": dict(emotion_dist),
        "daily_stats": daily_list,
    }


# ── 2. 热门话题（词频统计） ────────────────────────────────────────
@router.get("/hot-topics")
def hot_topics(scenic_id: str = "lingshan", days: int = 7, limit: int = 10):
    since = _date_range(days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_message FROM conversations WHERE scenic_id=? AND created_at>=?",
            (scenic_id, since),
        ).fetchall()

    # 中文 2-4 字 n-gram 词频（无需分词库）
    stop_chars = set("的了是我你他她它们吗呢啊哦哈嗯呀在有没有什么怎么哪里多少为什么吧好可以请问，。？！、：；""''…—～ ，,。.?!:;\"'()（）【】 \t\n")
    counter: Counter = Counter()
    for row in rows:
        msg = row["user_message"]
        for n in (2, 3, 4):
            for i in range(len(msg) - n + 1):
                gram = msg[i: i + n]
                if not any(c in stop_chars for c in gram):
                    counter[gram] += 1

    topics = [term for term, _ in counter.most_common(limit * 3) if len(set(term)) > 1]
    return {"topics": topics[:limit]}


# ── 2b. 话题意图分类（LLM 归类，替代 n-gram 碎片；带缓存） ──────────────
_TOPIC_CATS = ["景点介绍", "票价咨询", "交通方式", "开放时间", "餐饮推荐",
               "路线推荐", "设施服务", "住宿预订", "其他"]
# 缓存：{(scenic, days): (生成时刻, 结果)}，TTL 内复用，避免每次请求都打 LLM
_INTENT_CACHE: dict[tuple, tuple[datetime, dict]] = {}
_INTENT_TTL = timedelta(minutes=10)


@router.get("/topic-intents")
def topic_intents(scenic_id: str = "lingshan", days: int = 30, limit: int = 8):
    """游客提问的意图分类统计（LLM 归类，非 n-gram 碎片）。
    返回 [{intent, count}]，按 count 降序。结果缓存 10 分钟。"""
    key = (scenic_id, days)
    now = datetime.now()
    cached = _INTENT_CACHE.get(key)
    if cached and now - cached[0] < _INTENT_TTL:
        return {**cached[1], "cached": True}

    since = _date_range(days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_message FROM conversations WHERE scenic_id=? AND created_at>=? ORDER BY created_at DESC LIMIT 120",
            (scenic_id, since),
        ).fetchall()
    msgs = [r["user_message"][:40] for r in rows if r["user_message"]]
    if not msgs:
        out = {"scenic_id": scenic_id, "period_days": days, "topics": []}
        _INTENT_CACHE[key] = (now, out)
        return {**out, "cached": False}

    numbered = "\n".join(f"{i+1}. {m}" for i, m in enumerate(msgs))
    sys = "你是景区数据分析师。把游客问题按主题归类并计数。只输出 JSON，不要解释。"
    user = (
        f"把下面 {len(msgs)} 条游客问题归入这些类别之一：{('、').join(_TOPIC_CATS)}。\n"
        f"统计每个类别的条数，输出 JSON 对象 {{类别:条数}}（只含出现过的类别，条数之和={len(msgs)}）。\n\n{numbered}"
    )
    try:
        raw = chat(sys, [], user, fast=True).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        counts = json.loads(raw)
        topics = sorted(
            ({"intent": k, "count": int(v)} for k, v in counts.items() if int(v) > 0),
            key=lambda x: x["count"], reverse=True,
        )[:limit]
    except Exception:
        # LLM 失败兜底：返回空 topics（前端可降级用 /hot-topics 词云）
        topics = []
    out = {"scenic_id": scenic_id, "period_days": days, "sample_size": len(msgs), "topics": topics}
    _INTENT_CACHE[key] = (now, out)
    return {**out, "cached": False}


# ── 3. 满意度趋势 ──────────────────────────────────────────────────
@router.get("/sentiment-trend")
def sentiment_trend(scenic_id: str = "lingshan", days: int = 30):
    since = _date_range(days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DATE(created_at) as day, emotion FROM conversations "
            "WHERE scenic_id=? AND created_at>=? ORDER BY day",
            (scenic_id, since),
        ).fetchall()

    by_day: dict[str, list] = {}
    for r in rows:
        by_day.setdefault(r["day"], []).append(r["emotion"])

    trend = []
    for day in sorted(by_day):
        emotions = by_day[day]
        total = len(emotions)
        pos = sum(1 for e in emotions if e in _POSITIVE)
        trend.append({
            "date": day,
            "total": total,
            "happy_ratio": round(pos / total, 3) if total else 0.0,
            "emotion_counts": dict(Counter(emotions)),
        })

    all_emotions = [r["emotion"] for r in rows]
    overall = round(
        sum(1 for e in all_emotions if e in _POSITIVE) / len(all_emotions), 3
    ) if all_emotions else 0.0

    return {"overall_satisfaction": overall, "trend": trend}


# ── 4. 历史对话列表 ────────────────────────────────────────────────
@router.get("/conversations")
def conversations(
    scenic_id: str | None = None,
    session_id: str | None = None,
    days: int = 7,
    limit: int = 50,
    offset: int = 0,
):
    since = _date_range(days)
    conditions = ["created_at >= ?"]
    params: list = [since]

    if scenic_id:
        conditions.append("scenic_id = ?")
        params.append(scenic_id)
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)

    where = " AND ".join(conditions)

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM conversations WHERE {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM conversations WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(r) for r in rows],
    }


# ── 4.5 实时弹幕流（大屏/管理端「游客正在问」） ────────────────────
_DANMAKU_INTENT_RULES: list[tuple[tuple[str, ...], str]] = [
    (("走丢", "救命", "帮帮", "恐高", "害怕", "不舒服"), "empathy"),
    (("拍照", "机位", "拍", "角度", "朋友圈"), "photo"),
    (("推荐", "路线", "怎么安排", "怎么逛", "先看", "值得", "组合", "有什么好"), "recommend"),
    (("怎么走", "在哪", "哪里", "怎么去", "远吗", "方向", "出口", "入口", "地铁", "坐车", "哪路", "哪站"), "navigation"),
]

# 系统提示/兜底话术误入 user_message 的特征串（如 GPS 定位精度提示），弹幕直接丢弃
_DANMAKU_BLOCKLIST = ("定位精度", "位置可能有", "开阔", "无法获取", "位置信号", "抱歉", "系统繁忙")


def _danmaku_intent(text: str, emotion: str) -> str:
    if emotion in ("empathetic", "apologetic"):
        return "empathy"
    for keys, intent in _DANMAKU_INTENT_RULES:
        if any(k in text for k in keys):
            return intent
    return "qa"


def _danmaku_clean(raw: str) -> str | None:
    """弹幕文本清洗：去首尾杂质、脱敏长数字、超长截断；不合格返回 None。"""
    import re

    text = (raw or "").strip().strip("\"'“”")
    if not text or len(text) < 4:
        return None
    if text.startswith(("{", "[", "<")):        # 结构化/富文本误入库的行
        return None
    if any(b in text for b in _DANMAKU_BLOCKLIST):
        return None
    text = re.sub(r"\d{7,}", "****", text)       # 手机号等长数字脱敏
    if len(text) > 42:
        text = text[:40] + "…"
    return text


@router.get("/danmaku")
def danmaku(scenic_id: str = "lingshan", limit: int = 40, since: str | None = None):
    """弹幕数据流：近 24h 真实提问（清洗+去重），不足时用题库兜底补位。

    - since 传上次拿到的最新 created_at → 增量轮询（增量模式不做题库兜底，避免重复注水）；
    - 返回 real / bank_filled 计数，前端可判断当前是真数还是演示轮播。
    """
    import random

    from backend.data.danmaku_bank import bank_for

    limit = max(1, min(limit, 100))
    conditions = ["scenic_id = ?", "created_at >= ?"]
    params: list = [scenic_id, _date_range(1)]
    if since:
        conditions.append("created_at > ?")
        params.append(since)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT user_message, emotion, session_id, created_at FROM conversations "
            f"WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT 300",
            params,
        ).fetchall()

    items, seen = [], set()
    for r in rows:
        text = _danmaku_clean(r["user_message"])
        if not text:
            continue
        key = _normalize_q(text)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "text": text,
            "emotion": r["emotion"],
            "intent": _danmaku_intent(text, r["emotion"]),
            "ts": r["created_at"],
            "demo": r["session_id"].startswith("demo-"),
        })
        if len(items) >= limit:
            break

    filled = 0
    if len(items) < limit and not since:
        _BANK_EMOTION = {"empathy": "empathetic", "photo": "excited"}
        pool = bank_for(scenic_id)
        random.shuffle(pool)
        for text, intent in pool:
            if _normalize_q(text) in seen:
                continue
            seen.add(_normalize_q(text))
            items.append({
                "text": text,
                "emotion": _BANK_EMOTION.get(intent, random.choice(("happy", "curious", "neutral"))),
                "intent": intent,
                "ts": None,
                "demo": True,
            })
            filled += 1
            if len(items) >= limit:
                break

    return {"items": items, "real": len(items) - filled, "bank_filled": filled}


# ── 5. 知识盲区（闭环1：游客问了但知识库答不上来的问题） ──────────
def _normalize_q(q: str) -> str:
    """归一化问题文本，用于合并近似提问。"""
    return "".join(ch for ch in q if ch not in " \t\n，。？！、：；,.?!:;\"'").strip()


@router.get("/knowledge-gaps")
def knowledge_gaps(
    scenic_id: str = "lingshan",
    days: int = 30,
    limit: int = 20,
    cluster: bool = False,
):
    """
    返回知识库未命中的提问（context_used=0），按频次降序。
    这些是知识库的盲区——管理员据此补充文档，让知识库越用越准。

    cluster=True 时额外调用 LLM 把盲区聚成主题并给出补充建议（消耗 API）。
    """
    since = _date_range(days)
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE scenic_id=? AND created_at>=?",
            (scenic_id, since),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT user_message, created_at FROM conversations "
            "WHERE scenic_id=? AND created_at>=? AND context_used=0 "
            "ORDER BY created_at DESC",
            (scenic_id, since),
        ).fetchall()

    # 按归一化文本合并近似提问
    grouped: dict[str, dict] = {}
    for r in rows:
        key = _normalize_q(r["user_message"])
        if not key:
            continue
        if key not in grouped:
            grouped[key] = {"question": r["user_message"], "count": 0,
                            "last_asked": r["created_at"]}
        grouped[key]["count"] += 1

    gaps = sorted(grouped.values(), key=lambda x: x["count"], reverse=True)[:limit]

    result = {
        "scenic_id": scenic_id,
        "period_days": days,
        "total_conversations": total,
        "total_unanswered": len(rows),
        "unanswered_rate": round(len(rows) / total, 3) if total else 0.0,
        "gaps": gaps,
    }

    if cluster and gaps:
        gap_list = "\n".join(f"- {g['question']}（被问 {g['count']} 次）" for g in gaps)
        prompt = f"""你是景区知识库运营专家。以下是{scenic_id}景区数字人导游"答不上来"的游客提问（知识库未命中）：

{gap_list}

请把这些问题归纳成 2-4 个主题，每个主题给出：
1. **主题名**
2. **建议补充的知识内容**（具体到该写什么文档/资料）

输出用 Markdown，简洁，供管理员据此补充知识库。"""
        result["suggestions"] = chat(prompt, [], "请归纳并给出补充建议")

    return result


# ── 6. 实时负面情绪预警（闭环2） ──────────────────────────────────
def _hours_ago(hours: float) -> str:
    return (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


@router.get("/alerts")
def alerts(
    scenic_id: str | None = None,
    window_hours: float = 24,
    threshold: int = 3,
    min_rate: float = 0.3,
):
    """
    实时负面情绪预警：统计时间窗口内的负面情绪（empathetic/apologetic）。
    当负面对话数 ≥ threshold 且负面占比 ≥ min_rate 时触发告警。

    scenic_id 为空时扫描全部景区。返回告警状态 + 负面对话样本（供管理员定位）。
    """
    since = _hours_ago(window_hours)
    conditions = ["created_at >= ?"]
    params: list = [since]
    if scenic_id:
        conditions.append("scenic_id = ?")
        params.append(scenic_id)
    where = " AND ".join(conditions)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT scenic_id, user_message, ai_reply, emotion, created_at "
            f"FROM conversations WHERE {where} ORDER BY created_at DESC",
            params,
        ).fetchall()

    total = len(rows)
    negatives = [r for r in rows if r["emotion"] in _NEGATIVE]
    neg_count = len(negatives)
    neg_rate = round(neg_count / total, 3) if total else 0.0

    triggered = neg_count >= threshold and neg_rate >= min_rate

    # 负面情绪集中在哪些景区
    by_scenic = Counter(r["scenic_id"] for r in negatives)

    samples = [
        {
            "scenic_id":  r["scenic_id"],
            "question":   r["user_message"],
            "emotion":    r["emotion"],
            "asked_at":   r["created_at"],
        }
        for r in negatives[:10]
    ]

    return {
        "scenic_id":        scenic_id or "all",
        "window_hours":     window_hours,
        "alert_triggered":  triggered,
        "total_in_window":  total,
        "negative_count":   neg_count,
        "negative_rate":    neg_rate,
        "threshold":        threshold,
        "min_rate":         min_rate,
        "negative_by_scenic": dict(by_scenic),
        "samples":          samples,
    }


# ── 7. LLM 生成游客感受度报告（按需，会消耗 API） ─────────────────
class ReportRequest(BaseModel):
    scenic_id: str = "lingshan"
    days: int = 7


@router.post("/report")
def generate_report(req: ReportRequest):
    since = _date_range(req.days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_message, ai_reply, emotion FROM conversations "
            "WHERE scenic_id=? AND created_at>=? ORDER BY created_at DESC LIMIT 100",
            (req.scenic_id, since),
        ).fetchall()

    if not rows:
        return {"report": "暂无数据，无法生成报告。"}

    sample = "\n".join(
        f"游客：{r['user_message']}\n导游：{r['ai_reply'][:60]}…（情绪:{r['emotion']}）"
        for r in rows[:30]
    )
    emotion_dist = Counter(r["emotion"] for r in rows)

    prompt = f"""你是景区数字化运营分析师。以下是{req.scenic_id}景区近{req.days}天的游客对话样本（共{len(rows)}条），请生成一份简洁的游客感受度报告。

【对话样本】
{sample}

【情绪分布】
{dict(emotion_dist)}

请输出以下内容（用 Markdown 格式）：
1. **总体满意度评估**（一句话）
2. **游客最关注的3-5个话题**
3. **高频问题举例**（2-3条）
4. **运营改进建议**（2-3条）

报告须简洁，适合管理人员快速阅读。"""

    report = chat(prompt, [], "请生成报告")
    return {"scenic_id": req.scenic_id, "period_days": req.days, "report": report}


# ══════════════════════════════════════════════════════════════════
# 游客端「主动上报」半边：服务端从对话里看不到的信号（画像/功能/位置/满意度）
# ══════════════════════════════════════════════════════════════════

class EventIn(BaseModel):
    session_id: str
    scenic_id: str = "lingshan"
    type: str                              # session_start / feature_open / station_visit / photo_locate / milestone / session_end / rating
    group_type: str | None = None          # 画像：随 session_start 带
    lang: str | None = None
    payload: dict[str, Any] | None = None   # 随 type 不同的附加字段


@router.post("/event")
def ingest_event(e: EventIn):
    """游客端上报一条行为事件。容错落库，永不把错误抛回前端（埋点不能影响体验）。"""
    save_event(e.session_id, e.scenic_id, e.type, e.group_type, e.lang, e.payload)
    return {"ok": True}


def _payload(row) -> dict:
    try:
        return json.loads(row["payload"]) if row["payload"] else {}
    except (TypeError, ValueError):
        return {}


def _safe_json(s):
    """解析任意 JSON 字符串（列值），失败返回 None。"""
    try:
        return json.loads(s) if s else None
    except (TypeError, ValueError):
        return None


@router.get("/profile")
def profile(scenic_id: str = "lingshan", days: int = 7):
    """客群画像：同行类型 / 语言 / 兴趣 分布（来自 session_start 事件）。"""
    since = _date_range(days)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT group_type, lang, payload FROM events "
            "WHERE scenic_id=? AND type='session_start' AND created_at>=?",
            (scenic_id, since),
        ).fetchall()
    groups, langs, interests = Counter(), Counter(), Counter()
    # 自身情况标签 5 维分布（来自 session_start payload，零 DB 迁移）
    sit_counters = {d: Counter() for d in ("age", "pace", "mobility", "purpose", "first_time")}
    for r in rows:
        if r["group_type"]:
            groups[r["group_type"]] += 1
        if r["lang"]:
            langs[r["lang"]] += 1
        p = _payload(r)
        for it in (p.get("interests") or []):
            interests[it] += 1
        for dim, ctr in sit_counters.items():
            v = p.get(dim)
            if v:
                ctr[v] += 1

    # 游中画像聚合（🆕 P3）：动态兴趣 / 游览风格 / 未满足需求。
    # 静态 interests 来自 session_start（游客跳过开场快选就为空 → 稀疏）；
    # 动态画像来自对话在线推断，覆盖面广得多，是"稀疏"的根治。
    dyn_interests, styles, unmet = Counter(), Counter(), Counter()
    _INT_LABEL = {"history": "历史人文", "nature": "自然风光", "photo": "拍照打卡",
                  "food": "特色美食", "culture": "禅意文化"}
    profiled = 0
    try:
        with get_db() as conn:
            vrows = conn.execute(
                "SELECT interests, traits FROM visitor_profile WHERE scenic_id=? AND updated_at>=?",
                (scenic_id, since),
            ).fetchall()
        profiled = len(vrows)
        for r in vrows:
            for it in (_safe_json(r["interests"]) or []):
                dyn_interests[_INT_LABEL.get(it, it)] += 1
            tr = _safe_json(r["traits"]) or {}
            style = tr.get("style") or (tr.get("trajectory") or {}).get("style_hint")
            if style:
                styles[style] += 1
            for w in (tr.get("wishes") or []):
                unmet[str(w)] += 1
            for n in (tr.get("needs") or []):
                unmet[str(n)] += 1
    except Exception:
        pass

    return {
        "scenic_id": scenic_id,
        "period_days": days,
        "total_visitors": len(rows),
        "group_type": dict(groups),
        "lang": dict(langs),
        "interests": dict(interests.most_common(10)),
        "situation": {d: dict(ctr) for d, ctr in sit_counters.items()},
        # 🆕 P3 游中画像洞察
        "profiled_visitors": profiled,
        "dynamic_interests": dict(dyn_interests.most_common(10)),
        "styles": dict(styles.most_common()),
        "unmet_needs": dict(unmet.most_common(10)),
    }


@router.get("/feature-usage")
def feature_usage(scenic_id: str = "lingshan", days: int = 7):
    """功能使用率（feature_open 计数）+ 满意度（rating 均分）+ 活跃会话数。"""
    since = _date_range(days)
    with get_db() as conn:
        feats = conn.execute(
            "SELECT payload FROM events WHERE scenic_id=? AND type='feature_open' AND created_at>=?",
            (scenic_id, since),
        ).fetchall()
        ratings = conn.execute(
            "SELECT payload FROM events WHERE scenic_id=? AND type='rating' AND created_at>=?",
            (scenic_id, since),
        ).fetchall()
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) AS n FROM events WHERE scenic_id=? AND created_at>=?",
            (scenic_id, since),
        ).fetchone()["n"]
    usage = Counter()
    for r in feats:
        f = _payload(r).get("feature")
        if f:
            usage[f] += 1
    scores = [s for r in ratings if isinstance((s := _payload(r).get("score")), (int, float))]
    return {
        "scenic_id": scenic_id,
        "period_days": days,
        "active_sessions": sessions,
        "feature_open": dict(usage.most_common()),
        "rating_count": len(scores),
        "avg_rating": round(sum(scores) / len(scores), 2) if scores else None,
    }


@router.get("/reco-performance")
def reco_performance(scenic_id: str = "lingshan", days: int = 7):
    """个性化推荐「为你定制」效果：曝光 / 点击 / 点击率 + 热门推荐 + 动作分布。

    数据来自游客端埋点 reco_impression（推荐区曝光）/ reco_click（点了哪张卡）。
    双面闭环：游客端推荐产出数据 → 此端点供管理端大屏「推荐效果」展现。纯只读，additive。
    """
    since = _date_range(days)
    with get_db() as conn:
        imps = conn.execute(
            "SELECT payload FROM events WHERE scenic_id=? AND type='reco_impression' AND created_at>=?",
            (scenic_id, since),
        ).fetchall()
        clks = conn.execute(
            "SELECT payload FROM events WHERE scenic_id=? AND type='reco_click' AND created_at>=?",
            (scenic_id, since),
        ).fetchall()
    impressions = len(imps)
    clicks = len(clks)
    by_title, by_action = Counter(), Counter()
    for r in clks:
        p = _payload(r)
        if p.get("title"):
            by_title[p["title"]] += 1
        if p.get("action"):
            by_action[p["action"]] += 1
    return {
        "scenic_id": scenic_id,
        "period_days": days,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(clicks / impressions, 3) if impressions else None,
        "top_recommendations": dict(by_title.most_common(10)),
        "by_action": dict(by_action),
    }
