"""游中画像 profiler：从对话在线积累游客兴趣与关心点，供推荐/导航链路"懂他"。

红线（与 plan/CLAUDE 一致）：
- 画像只喂给生成性意图（recommend / navigation）与推荐卡；**绝不进 qa 事实问答链路**（守 97% 准确率）。
- 所有公开函数整体 try/except 静默——画像失败=没有画像，绝不把异常抛回主链路（同前端埋点纪律）。
- 匿名 / 大屏共享 / 占位 session 不建画像（多人共用会串人）；48h 惰性自清（人走画像消）。
"""
import datetime as _dt
import hashlib
import json
import random
import re
import threading
from functools import lru_cache

from backend.db.database import get_db
from backend.api.tour import TOURS
from backend.llm.client import chat as _default_chat

# LLM 注入点（测试替换为 fake，不花钱/不依赖网络）
_llm = _default_chat
# 正在异步摘要的 session，防重入（daemon 线程完成后清除）
_INFLIGHT: set[str] = set()

# 匿名 / 大屏共享 / 占位 session：不建画像
_SKIP_SESSIONS = {"", "anonymous", "0", "s_anon"}

# 兴趣关键词表（id 对齐 webapp 兴趣快选与后端 _INTEREST：history/nature/photo/food/culture）。
# 纯数据表，不写 if-else 分支（守"换库不换码"）。query 命中即累积对应兴趣 id。
_INTEREST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "food":    ("素斋", "斋饭", "斋菜", "美食", "小吃", "特产", "好吃", "餐厅", "吃饭", "面馆", "咖啡", "喝的"),
    "photo":   ("拍照", "拍摄", "机位", "出片", "合影", "打卡", "取景", "相机", "留念", "自拍"),
    "culture": ("历史", "典故", "由来", "传说", "文化", "故事", "禅", "祈福", "上香", "许愿", "菩萨", "寓意", "讲究", "为什么叫", "佛教"),
    "nature":  ("风景", "景色", "湖", "樱花", "赏花", "日出", "日落", "夜景", "自然", "园林", "绿"),
    "history": ("朝代", "年代", "古迹", "遗址", "文物", "皇帝", "建于", "多少年", "多久历史", "始建"),
}

# 关心点 → 画像标签（brief 的"特别关心"维度，非兴趣 id）。同样纯数据表。
_CARE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "无障碍出行": ("无障碍", "轮椅", "婴儿车", "推车", "台阶", "电梯", "坡道"),
    "带娃":      ("孩子", "小孩", "宝宝", "亲子", "遛娃", "儿童"),
    "需要休息":   ("累", "歇脚", "休息区", "坐一下", "走不动"),
}

_INTEREST_LABELS = {
    "history": "历史人文", "nature": "自然风光", "photo": "拍照打卡",
    "food": "特色美食", "culture": "禅意文化",
}


# ── JSON / 集合小工具 ────────────────────────────────────────────────
def _loads(s, default):
    try:
        v = json.loads(s) if s else default
        return v if isinstance(v, type(default)) else default
    except Exception:
        return default


def _union(a: list, b: list) -> list:
    out = list(a)
    for x in b:
        if x and x not in out:
            out.append(x)
    return out


@lru_cache(maxsize=32)
def _poi_names(scenic_id: str) -> tuple[str, ...]:
    """本景区真实站名（复用推荐链路同源 TOURS），用于识别对话问到的具体点位。"""
    names: list[str] = []
    for route in TOURS.get(scenic_id, []):
        for st in route.get("stations", []):
            n = st.get("name")
            if n and n not in names:
                names.append(n)
    return tuple(names)


def _scan_interests(query: str) -> list[str]:
    return [iid for iid, kws in _INTEREST_KEYWORDS.items() if any(k in query for k in kws)]


def _scan_care(query: str) -> list[str]:
    return [tag for tag, kws in _CARE_KEYWORDS.items() if any(k in query for k in kws)]


def _scan_pois(query: str, scenic_id: str) -> list[str]:
    return [n for n in _poi_names(scenic_id) if n and n in query]


# ── 主链路调用点 ─────────────────────────────────────────────────────
def note_turn(session_id: str, scenic_id: str, query: str,
              intent_value: str, static_interests=None) -> None:
    """记一轮对话进画像：扫兴趣/关心点/问到的 POI + intent 计数 + 静态兴趣并入。整体静默容错。"""
    if not session_id or session_id in _SKIP_SESSIONS:
        return
    try:
        query = query or ""
        new_interests = _scan_interests(query)
        new_care = _scan_care(query)
        new_pois = _scan_pois(query, scenic_id)
        static = [i for i in (static_interests or []) if isinstance(i, str)]
        with get_db() as conn:
            r = conn.execute(
                "SELECT interests, asked_pois, intent_stats, traits, turn_count "
                "FROM visitor_profile WHERE session_id=?",
                (session_id,),
            ).fetchone()
            if r:
                interests = _loads(r["interests"], [])
                asked = _loads(r["asked_pois"], [])
                stats = _loads(r["intent_stats"], {})
                traits = _loads(r["traits"], {})
                turn = int(r["turn_count"] or 0)
            else:
                interests, asked, stats, traits, turn = [], [], {}, {}, 0

            interests = _union(interests, new_interests + static)
            asked = _union(asked, new_pois)
            care = _union(traits.get("care") or [], new_care)
            if care:
                traits["care"] = care
            stats[intent_value] = int(stats.get(intent_value, 0)) + 1
            turn += 1

            # ON CONFLICT DO UPDATE 只改列出的列 → 保留 visited / summary（P2/P3 写入的字段不被抹掉）
            conn.execute(
                """INSERT INTO visitor_profile
                     (session_id, scenic_id, interests, asked_pois, intent_stats, traits, turn_count, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
                   ON CONFLICT(session_id) DO UPDATE SET
                     scenic_id=excluded.scenic_id, interests=excluded.interests,
                     asked_pois=excluded.asked_pois, intent_stats=excluded.intent_stats,
                     traits=excluded.traits, turn_count=excluded.turn_count, updated_at=excluded.updated_at""",
                (session_id, scenic_id,
                 json.dumps(interests, ensure_ascii=False), json.dumps(asked, ensure_ascii=False),
                 json.dumps(stats, ensure_ascii=False), json.dumps(traits, ensure_ascii=False), turn),
            )
        maybe_summarize(session_id, scenic_id, turn)  # 每 6 轮异步 LLM 摘要（自判条件）
        if turn % 5 == 0:  # 每 5 轮刷新轨迹推断（读现有 events，一次索引查询）
            update_trajectory(session_id, scenic_id)
        _maybe_gc()
    except Exception:
        pass


def profile_brief(session_id: str) -> str:
    """一行中文画像摘要（供 recommend/navigation 注入）。空画像/匿名 session → ""。"""
    if not session_id or session_id in _SKIP_SESSIONS:
        return ""
    try:
        with get_db() as conn:
            r = conn.execute(
                "SELECT interests, asked_pois, traits, summary, visited "
                "FROM visitor_profile WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if not r:
            return ""
        interests = _loads(r["interests"], [])
        asked = _loads(r["asked_pois"], [])
        traits = _loads(r["traits"], {})
        summary = (r["summary"] or "").strip()
        visited = _loads(r["visited"], [])

        parts: list[str] = []
        # P2：LLM 一句话画像优先领衔；否则用规则兴趣标签
        if summary:
            parts.append(summary)
        else:
            labels = [_INTEREST_LABELS.get(i, i) for i in interests][:4]
            if labels:
                parts.append("游客兴趣：" + "、".join(labels))
        care = traits.get("care") or []
        if care:
            parts.append("特别关心：" + "、".join(care[:2]))
        if asked:
            parts.append("对话中问过：" + "、".join(asked[:4]))
        if visited:  # P3 轨迹
            parts.append("已到访：" + "、".join(visited[:5]))
        wishes = traits.get("wishes") or []  # P2 未了心愿
        if wishes:
            parts.append("未了心愿：" + "、".join(wishes[:2]))
        traj = traits.get("trajectory") or {}  # P3 节奏/体力
        if traj.get("fatigue_hint"):
            parts.append(traj["fatigue_hint"])
        return "；".join(parts)
    except Exception:
        return ""


def profile_digest(session_id: str) -> str:
    """brief 的短哈希，供 recommend 缓存键（画像变则卡片重算）。空画像 → ""。"""
    b = profile_brief(session_id)
    if not b:
        return ""
    return hashlib.md5(b.encode("utf-8")).hexdigest()[:8]


def _maybe_gc() -> None:
    """惰性清理 48h 前的画像行（~1/50 概率触发，均摊无感）。"""
    try:
        if random.random() < 0.02:
            with get_db() as conn:
                conn.execute(
                    "DELETE FROM visitor_profile "
                    "WHERE updated_at < datetime('now','localtime','-48 hours')"
                )
    except Exception:
        pass


# ── P2：LLM 异步画像摘要（后置、不占问答延迟预算） ────────────────────
_SUMMARY_PROMPT = (
    "你是景区导览系统的游客画像分析助手。依据这位游客今天在景区的真实对话，"
    "总结一份简洁的游中画像，帮助导游更懂他。**严格只输出一个 JSON 对象**，无任何多余文字：\n"
    '{{"summary":"一句话画像(≤40字，第三人称，如\'带孩子、爱拍照、体力一般的家庭游客\')",'
    '"style":"打卡型|深度型|亲子型|悠闲型|摄影型 里选一个最贴切的",'
    '"needs":["实际需求，如 无障碍、就近餐饮；没有则空数组"],'
    '"wishes":["他明确提过想做/想看但还没实现的事，如 想看九龙灌浴；没有则空数组"],'
    '"avoid":["他明确表示不感兴趣或想避开的；没有则空数组"]}}\n\n'
    "已有画像（可能为空）：{profile}\n\n对话记录（时间从早到晚）：\n{history}"
)


def _recent_conversations(session_id: str, scenic_id: str, limit: int = 12) -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_message, ai_reply FROM conversations "
            "WHERE session_id=? AND scenic_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, scenic_id, limit),
        ).fetchall()
    lines: list[str] = []
    for r in reversed(rows):
        if r["user_message"]:
            lines.append("游客：" + r["user_message"][:80])
        if r["ai_reply"]:
            lines.append("导游：" + r["ai_reply"][:80])
    return "\n".join(lines)


def _summarize_worker(session_id: str, scenic_id: str) -> None:
    """daemon 线程体：读近期对话 → qwen-flash 出画像 JSON → 合并写回 summary/traits。全静默。"""
    try:
        with get_db() as conn:
            r = conn.execute(
                "SELECT interests, asked_pois, traits, summary FROM visitor_profile WHERE session_id=?",
                (session_id,),
            ).fetchone()
        prof = {}
        if r:
            prof = {
                "interests": _loads(r["interests"], []),
                "asked_pois": _loads(r["asked_pois"], []),
                "traits": _loads(r["traits"], {}),
                "summary": r["summary"] or "",
            }
        history = _recent_conversations(session_id, scenic_id)
        if not history:
            return
        prompt = _SUMMARY_PROMPT.format(
            profile=json.dumps(prof, ensure_ascii=False)[:800], history=history[:2000],
        )
        raw = _llm(system_prompt=prompt, history=[], user_message="请输出画像 JSON。", fast=True)
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            return
        data = json.loads(m.group(0))
        if not isinstance(data, dict):
            return
        # 合并写回：只覆盖 summary + traits 的 LLM 字段，保留规则积累的 care/trajectory
        with get_db() as conn:
            row = conn.execute("SELECT traits FROM visitor_profile WHERE session_id=?", (session_id,)).fetchone()
            if not row:
                return
            traits = _loads(row["traits"], {})
            for k in ("style", "needs", "wishes", "avoid"):
                v = data.get(k)
                if isinstance(v, list):
                    v = [str(x).strip()[:20] for x in v if str(x).strip()][:5]
                if v:
                    traits[k] = v
            summary = str(data.get("summary") or "").strip()[:60]
            conn.execute(
                "UPDATE visitor_profile SET summary=?, traits=?, "
                "updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE session_id=?",
                (summary, json.dumps(traits, ensure_ascii=False), session_id),
            )
    except Exception:
        pass
    finally:
        _INFLIGHT.discard(session_id)


def maybe_summarize(session_id: str, scenic_id: str, turn_count: int) -> None:
    """每 6 轮触发一次 LLM 摘要（daemon 线程，不阻塞主链路）。防重入、匿名跳过、静默容错。"""
    try:
        if not session_id or session_id in _SKIP_SESSIONS:
            return
        if turn_count <= 0 or turn_count % 6 != 0:
            return
        if session_id in _INFLIGHT:
            return
        _INFLIGHT.add(session_id)
        threading.Thread(target=_summarize_worker, args=(session_id, scenic_id), daemon=True).start()
    except Exception:
        _INFLIGHT.discard(session_id)


# ── P3：轨迹推断（读现有 geo_arrival/station_visit 事件，零新采集） ──────
def _parse_dt(s: str):
    try:
        return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def infer_trajectory(session_id: str) -> dict:
    """从到访事件序列推断：到访 POI / 平均停留 / 游览风格 / 已游时长 / 体力提示。空则 {}。"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT payload, created_at FROM events "
                "WHERE session_id=? AND type IN ('geo_arrival','station_visit') ORDER BY created_at",
                (session_id,),
            ).fetchall()
        # 去连续重复（同一点反复触发围栏）后的到访序列
        seq: list[tuple[str, str]] = []
        for r in rows:
            name = (_loads(r["payload"], {}) or {}).get("name")
            if name and (not seq or seq[-1][0] != name):
                seq.append((name, r["created_at"]))
        if not seq:
            return {}
        visited: list[str] = []
        for name, _ts in seq:
            if name not in visited:
                visited.append(name)
        stays = []
        for i in range(len(seq) - 1):
            a, b = _parse_dt(seq[i][1]), _parse_dt(seq[i + 1][1])
            if a and b:
                mins = (b - a).total_seconds() / 60.0
                if 0 < mins < 240:  # 丢弃跨天/异常间隔
                    stays.append(mins)
        avg_stay = round(sum(stays) / len(stays), 1) if stays else 0.0
        first, last = _parse_dt(seq[0][1]), _parse_dt(seq[-1][1])
        elapsed = int((last - first).total_seconds() / 60) if (first and last) else 0
        traj: dict = {"visited": visited, "avg_stay_min": avg_stay,
                      "walked_pois": len(visited), "elapsed_min": elapsed}
        if avg_stay and avg_stay < 6:
            traj["style_hint"] = "打卡型"
        elif avg_stay and avg_stay > 15:
            traj["style_hint"] = "深度型"
        if elapsed > 150 and len(visited) >= 4:
            traj["fatigue_hint"] = "游客已连续游览较久，路线推荐宜就近收尾、多提休息点"
        return traj
    except Exception:
        return {}


def update_trajectory(session_id: str, scenic_id: str) -> None:
    """把轨迹推断写入画像（traits.trajectory + visited 列）。匿名跳过、静默。"""
    try:
        if not session_id or session_id in _SKIP_SESSIONS:
            return
        traj = infer_trajectory(session_id)
        if not traj:
            return
        with get_db() as conn:
            row = conn.execute("SELECT traits FROM visitor_profile WHERE session_id=?", (session_id,)).fetchone()
            traits = _loads(row["traits"], {}) if row else {}
            traits["trajectory"] = traj
            visited_json = json.dumps(traj.get("visited", []), ensure_ascii=False)
            if row:
                conn.execute(
                    "UPDATE visitor_profile SET traits=?, visited=?, "
                    "updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE session_id=?",
                    (json.dumps(traits, ensure_ascii=False), visited_json, session_id),
                )
            else:
                conn.execute(
                    "INSERT INTO visitor_profile (session_id, scenic_id, traits, visited) VALUES (?, ?, ?, ?)",
                    (session_id, scenic_id, json.dumps(traits, ensure_ascii=False), visited_json),
                )
    except Exception:
        pass
