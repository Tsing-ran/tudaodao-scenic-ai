"""
游中画像 profiler · 单元 + qa 防回归测试（P1）。

运行：cd <项目根> && .venv/bin/python tests/test_visitor_profile.py
覆盖：note_turn 兴趣/POI/intent 累积、profile_brief 输出、匿名 session 跳过、
     UPSERT 幂等、**qa 意图 prompt 不含画像（红线）**、navigation/recommend 含画像。
用真实 SQLite，测试行用 test_vp_* 前缀并清理。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import get_db, init_db
from backend.agent import profiler
from backend.agent.profiler import note_turn, profile_brief, profile_digest
from backend.agent.intents import Intent
from backend.rag.pipeline import _directive_with_context
from backend.api.tour import TOURS

init_db()

passed = failed = 0


def check(name: str, cond: bool, detail: str = ""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  OK  {name}")
    else:
        failed += 1
        print(f"  XX  {name}  {detail}")


def cleanup():
    with get_db() as conn:
        conn.execute("DELETE FROM visitor_profile WHERE session_id LIKE 'test_vp_%'")


cleanup()

# 取灵山一个真实站名做 POI 匹配测试（避免硬编码脆化）
_lingshan_pois = [st["name"] for r in TOURS.get("lingshan", []) for st in r.get("stations", []) if st.get("name")]
POI = _lingshan_pois[0] if _lingshan_pois else "大佛"

SID = "test_vp_sess1"

# 1) note_turn 累积兴趣（素斋=food、拍照=photo）+ POI + intent 计数
note_turn(SID, "lingshan", "这里有素斋吗，想尝尝斋饭", "qa")
note_turn(SID, "lingshan", "哪里适合拍照出片", "recommend")
note_turn(SID, "lingshan", f"{POI}怎么走", "navigation")

brief = profile_brief(SID)
check("brief 反映美食兴趣", "特色美食" in brief, brief)
check("brief 反映拍照兴趣", "拍照打卡" in brief, brief)
check("brief 记录问过的 POI", POI in brief, f"POI={POI} brief={brief}")

with get_db() as conn:
    row = conn.execute("SELECT interests, asked_pois, intent_stats, turn_count FROM visitor_profile WHERE session_id=?", (SID,)).fetchone()
interests = json.loads(row["interests"])
stats = json.loads(row["intent_stats"])
check("interests 含 food/photo", "food" in interests and "photo" in interests, str(interests))
check("turn_count=3", row["turn_count"] == 3, str(row["turn_count"]))
check("intent_stats 计数正确", stats.get("qa") == 1 and stats.get("recommend") == 1 and stats.get("navigation") == 1, str(stats))

# 2) 匿名 / 大屏共享 session 不建画像
for anon in ("anonymous", "0", "", "s_anon"):
    note_turn(anon, "lingshan", "素斋在哪", "qa")
    check(f"匿名 session '{anon}' brief 为空", profile_brief(anon) == "", repr(profile_brief(anon)))

# 3) 静态兴趣并入 + UPSERT 幂等（重复不翻倍）
note_turn(SID, "lingshan", "随便逛逛", "chitchat", static_interests=["culture", "culture", "history"])
note_turn(SID, "lingshan", "随便逛逛", "chitchat", static_interests=["culture"])
with get_db() as conn:
    row = conn.execute("SELECT interests FROM visitor_profile WHERE session_id=?", (SID,)).fetchone()
interests = json.loads(row["interests"])
check("静态兴趣并入", "culture" in interests and "history" in interests, str(interests))
check("UPSERT 幂等·culture 不重复", interests.count("culture") == 1, str(interests))

# 4) 红线：qa 意图 prompt 不含游中画像
qa_directive = _directive_with_context(Intent.QA, "lingshan", session_id=SID)
check("【红线】qa 意图不含游中画像", "游中画像" not in qa_directive, qa_directive[-120:])

# 5) navigation / recommend 意图含游中画像
nav_directive = _directive_with_context(Intent.NAVIGATION, "lingshan", session_id=SID)
reco_directive = _directive_with_context(Intent.RECOMMEND, "lingshan", session_id=SID)
check("navigation 意图含游中画像", "游中画像" in nav_directive, nav_directive[-160:])
check("recommend 意图含游中画像", "游中画像" in reco_directive, reco_directive[-160:])

# 6) 无画像 session：navigation 也不注入（brief 空 → 不加块）
nav_empty = _directive_with_context(Intent.NAVIGATION, "lingshan", session_id="test_vp_nobody")
check("无画像 session·navigation 不注入", "游中画像" not in nav_empty, nav_empty[-120:])

# 7) profile_digest 稳定且随 brief（被消费内容）变化
d1 = profile_digest(SID)
note_turn(SID, "lingshan", "带着轮椅方便吗，有无障碍通道吗", "qa")  # 新增 care 维度 → brief 必变
d2 = profile_digest(SID)
check("digest 非空", bool(d1), d1)
check("brief 新增关心维度后 digest 变化", d1 != d2, f"{d1} vs {d2} brief={profile_brief(SID)}")
check("空画像 digest 为空", profile_digest("test_vp_nobody") == "", profile_digest("test_vp_nobody"))

# ════════════════════════════════════════════════════════════════════
# P2：LLM 异步摘要 + 未了心愿 + 画像接力
# ════════════════════════════════════════════════════════════════════
import types
from backend.db.database import save_conversation
from backend.agent import profiler as P

# 造对话记录供摘要读取（_summarize_worker 读 conversations 表）
save_conversation(SID, "lingshan", "有素斋吗", "有的，灵山精舍提供素斋", "neutral", True)
save_conversation(SID, "lingshan", "想看九龙灌浴表演", "九龙灌浴每天多场", "neutral", True)

# 假线程：同步执行 target、记录 spawn（去掉线程时序不确定性）
_spawned = []


class _FakeThread:
    def __init__(self, target=None, args=(), daemon=None):
        self._t, self._a = target, args

    def start(self):
        _spawned.append(1)
        if self._t:
            self._t(*self._a)


P.threading = types.SimpleNamespace(Thread=_FakeThread)

# 8) 摘要 gating：turn=5 不触发、turn=6 触发
P._llm = lambda **kw: '好的 {"summary":"爱美食、想看九龙灌浴的悠闲游客","style":"悠闲型","needs":["就近餐饮"],"wishes":["想看九龙灌浴"],"avoid":[]} 完'
_spawned.clear()
P.maybe_summarize(SID, "lingshan", 5)
check("turn=5 不触发摘要", len(_spawned) == 0, str(len(_spawned)))
P.maybe_summarize(SID, "lingshan", 6)
check("turn=6 触发摘要", len(_spawned) == 1, str(len(_spawned)))

b = profile_brief(SID)
check("LLM summary 领衔 brief", "爱美食" in b or "悠闲游客" in b, b)
check("未了心愿进 brief", "未了心愿" in b and "九龙灌浴" in b, b)
check("_INFLIGHT 已清空(worker finally)", SID not in P._INFLIGHT, str(P._INFLIGHT))

# 9) 垃圾输出静默、不破坏既有画像
P._llm = lambda **kw: "这根本不是JSON文本"
before = profile_brief(SID)
P.maybe_summarize(SID, "lingshan", 6)
check("垃圾 LLM 输出不破坏画像", "九龙灌浴" in profile_brief(SID), profile_brief(SID))
check("垃圾输出后 _INFLIGHT 仍清空", SID not in P._INFLIGHT, str(P._INFLIGHT))

# 10) 画像接力：_copy_profile 并入领取方
from backend.api.handoff import _copy_profile, _read_profile_summary

DST = "test_vp_dst"
with get_db() as conn:
    conn.execute("DELETE FROM visitor_profile WHERE session_id=?", (DST,))
check("源画像摘要非空(接力可显示)", bool(_read_profile_summary(SID)), _read_profile_summary(SID))
_copy_profile(SID, DST)
check("接力后新会话画像非空", profile_brief(DST) != "", profile_brief(DST))
with get_db() as conn:
    dst_int = json.loads(conn.execute("SELECT interests FROM visitor_profile WHERE session_id=?", (DST,)).fetchone()["interests"])
check("接力复制了兴趣(food)", "food" in dst_int, str(dst_int))
_copy_profile(SID, "0")  # 匿名 dst 不复制
check("匿名 dst 不建画像", profile_brief("0") == "", profile_brief("0"))

# 11) 隐私：48h 前画像被清理规则删除（直接验 SQL，不依赖随机门）
OLD = "test_vp_old"
with get_db() as conn:
    conn.execute("INSERT OR REPLACE INTO visitor_profile (session_id, scenic_id, updated_at) "
                 "VALUES (?, 'lingshan', datetime('now','localtime','-50 hours'))", (OLD,))
    conn.execute("DELETE FROM visitor_profile WHERE updated_at < datetime('now','localtime','-48 hours')")
    gone = conn.execute("SELECT 1 FROM visitor_profile WHERE session_id=?", (OLD,)).fetchone() is None
check("50h 前画像被 48h 清理规则删除", gone)

# ════════════════════════════════════════════════════════════════════
# P3：轨迹推断 + 管理端客群洞察
# ════════════════════════════════════════════════════════════════════
import datetime as _dtt
from backend.agent.profiler import infer_trajectory, update_trajectory


def _seed_geo(session_id, scenic, names, interval_min, hours_ago=3):
    base = _dtt.datetime.now().replace(microsecond=0) - _dtt.timedelta(hours=hours_ago)
    with get_db() as conn:
        conn.execute("DELETE FROM events WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM visitor_profile WHERE session_id=?", (session_id,))
        for i, nm in enumerate(names):
            ts = (base + _dtt.timedelta(minutes=interval_min * i)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO events (session_id, scenic_id, type, payload, created_at) VALUES (?,?,?,?,?)",
                (session_id, scenic, "geo_arrival", json.dumps({"name": nm}, ensure_ascii=False), ts))


# 12) 深度型：4 点 × 20 分钟间隔
TSID = "test_vp_traj"
_seed_geo(TSID, "lingshan", ["A广场", "B殿", "C塔", "D馆"], 20)
traj = infer_trajectory(TSID)
check("轨迹 walked_pois=4", traj.get("walked_pois") == 4, str(traj))
check("轨迹深度型(间隔20min)", traj.get("style_hint") == "深度型", str(traj))
check("轨迹 elapsed=60min", traj.get("elapsed_min") == 60, str(traj))
update_trajectory(TSID, "lingshan")
check("轨迹写入 brief(已到访)", "已到访" in profile_brief(TSID), profile_brief(TSID))

# 13) 打卡型：4 点 × 4 分钟间隔
TSID2 = "test_vp_traj2"
_seed_geo(TSID2, "lingshan", ["A", "B", "C", "D"], 4)
check("轨迹打卡型(间隔4min)", infer_trajectory(TSID2).get("style_hint") == "打卡型", str(infer_trajectory(TSID2)))

# 14) 体力提示：5 点 × 40 分钟（elapsed=160>150）
TSID3 = "test_vp_traj3"
_seed_geo(TSID3, "lingshan", ["A", "B", "C", "D", "E"], 40)
t3 = infer_trajectory(TSID3)
check("长时游览触发体力提示", "fatigue_hint" in t3, str(t3))

# 15) analytics /profile 三个新字段 + 旧字段不变
from backend.api.analytics import profile as analytics_profile
PS = "test_vp_scenic"
with get_db() as conn:
    conn.execute("DELETE FROM visitor_profile WHERE scenic_id=?", (PS,))
    conn.execute(
        "INSERT INTO visitor_profile (session_id, scenic_id, interests, traits, updated_at) "
        "VALUES (?,?,?,?,strftime('%Y-%m-%d %H:%M:%S','now','localtime'))",
        ("test_vp_ana1", PS, json.dumps(["food", "photo"]),
         json.dumps({"style": "打卡型", "wishes": ["想看九龙灌浴"], "needs": ["就近餐饮"]}, ensure_ascii=False)))
res = analytics_profile(scenic_id=PS, days=7)
check("/profile 含 dynamic_interests", bool(res.get("dynamic_interests")), str(res.get("dynamic_interests")))
check("/profile 动态兴趣映射标签", "特色美食" in res.get("dynamic_interests", {}), str(res.get("dynamic_interests")))
check("/profile styles 计数", res.get("styles", {}).get("打卡型") == 1, str(res.get("styles")))
check("/profile unmet_needs 含心愿", "想看九龙灌浴" in res.get("unmet_needs", {}), str(res.get("unmet_needs")))
check("/profile 旧字段仍在", all(k in res for k in ("group_type", "lang", "interests", "situation")), str(list(res.keys())))

# 清理 P3 造的数据
with get_db() as conn:
    for s in (TSID, TSID2, TSID3, "test_vp_ana1"):
        conn.execute("DELETE FROM events WHERE session_id=?", (s,))
        conn.execute("DELETE FROM visitor_profile WHERE session_id=?", (s,))
    conn.execute("DELETE FROM visitor_profile WHERE scenic_id=?", (PS,))

# 清理 P2 造的数据
with get_db() as conn:
    conn.execute("DELETE FROM visitor_profile WHERE session_id IN (?, ?)", (DST, "0"))
    conn.execute("DELETE FROM conversations WHERE session_id=?", (SID,))

cleanup()
print(f"\n结果：{passed} 通过 / {failed} 失败")
sys.exit(1 if failed else 0)
