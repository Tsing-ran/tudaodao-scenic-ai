"""知识库管理端能力回归（纯逻辑，无 LLM/网络调用）：
  1. self-test 的确定性关键词抽取与均匀采样
  2. retrieval-config 的 SQLite 读写/缓存失效/恢复默认
跑法：.venv/bin/python tests/test_kb_admin.py（服务器：/root/miniconda3/bin/python）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}")


# ── 1. self-test 出题逻辑 ─────────────────────────────
from backend.api.kb_selftest import _extract_numbers, _extract_terms, pick_fact_chunks

check("数字抽取：88米/39.8/1997", _extract_numbers("大佛高88米，照壁长39.8米，1997年落成") == ["88", "39.8", "1997"])
check("数字抽取：过滤单位数噪声", _extract_numbers("排名第1，共5个") == [])
check("专名抽取：书名号+引号", _extract_terms("被誉为“东方佛国”，源自《华严经》") == ["东方佛国", "华严经"])
check("专名抽取：超长不抽", _extract_terms("「这是一段超过十二个字的很长很长的内容」") == [])

docs = [
    "灵山大佛通高88米，1997年落成",          # 有数字
    "这里风景优美，游客络绎不绝",              # 无事实 → 应被过滤
    "梵宫被誉为“东方卢浮宫”",                 # 有专名
    "九龙灌浴每天上午10:00和下午15:30各一场",  # 有数字
]
cases = pick_fact_chunks(docs, 10)
check("事实 chunk 筛选：4 选 3", len(cases) == 3)
check("无事实 chunk 被剔除", all("络绎不绝" not in c["chunk"] for c in cases))
check("关键词数字优先", cases[0]["keywords"][0] == "88")
check("采样可复现（两次一致）", pick_fact_chunks(docs, 2) == pick_fact_chunks(docs, 2))
check("超量采样不越界", len(pick_fact_chunks(docs, 2)) == 2)
check("空库返回空", pick_fact_chunks(["纯闲聊内容"], 5) == [])

# ── 2. retrieval-config 读写 ──────────────────────────
from backend.db.database import init_db
from backend.rag.retrieval_config import get_overrides, set_overrides, reset_overrides, STRATEGIES

init_db()
_SID = "_selftest_unit"
reset_overrides(_SID)

ov = get_overrides(_SID)
check("无配置 = 默认基线（strategy=hybrid, top_k/threshold=None）",
      ov.strategy == "hybrid" and ov.top_k is None and ov.threshold is None)

set_overrides(_SID, "keyword", 3, 0.5)
ov = get_overrides(_SID)
check("保存后读回一致", ov.strategy == "keyword" and ov.top_k == 3 and ov.threshold == 0.5)

set_overrides(_SID, "semantic", None, None)
ov = get_overrides(_SID)
check("upsert 覆盖（含置空）", ov.strategy == "semantic" and ov.top_k is None)

try:
    set_overrides(_SID, "magic", None, None)
    check("非法 strategy 应拒绝", False)
except ValueError:
    check("非法 strategy 应拒绝", True)

reset_overrides(_SID)
ov = get_overrides(_SID)
check("恢复默认后回到基线", ov.strategy == "hybrid" and ov.top_k is None and ov.threshold is None)
check("策略枚举完备", STRATEGIES == ("hybrid", "semantic", "keyword"))

print(f"\n{'✅' if failed == 0 else '❌'} test_kb_admin: {passed}/{passed + failed} 通过")
sys.exit(0 if failed == 0 else 1)
