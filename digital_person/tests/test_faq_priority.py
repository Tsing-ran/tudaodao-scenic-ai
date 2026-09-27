"""FAQ 最高优先级命中层回归（纯逻辑 + SQLite roundtrip，无 LLM/网络）：
  1. 归一化与高阈值近似匹配：精确/近似命中、无关不命中、过短不命中
  2. faq_items 增删 → invalidate → match 生效/失效
跑法：.venv/bin/python tests/test_faq_priority.py（服务器：/root/miniconda3/bin/python）
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


from backend.rag import faq_priority
from backend.db.database import get_db

SC = "test_faqp"


def _seed(question, answer, category=""):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO faq_items (scenic_id, question, answer, category) VALUES (?,?,?,?)",
            (SC, question, answer, category),
        )
        return cur.lastrowid


def _cleanup():
    with get_db() as conn:
        conn.execute("DELETE FROM faq_items WHERE scenic_id=?", (SC,))
    faq_priority.invalidate(SC)


_cleanup()

# ── 1. 归一化 ────────────────────────────────────────
check("归一化去标点空白", faq_priority._norm("门票，多少 钱？") == "门票多少钱")

# ── 2. 命中逻辑 ──────────────────────────────────────
fid = _seed("门票多少钱", "成人票 120 元，1.4 米以下儿童免票。", "票务信息")
faq_priority.invalidate(SC)

check("精确命中", (faq_priority.match_faq(SC, "门票多少钱") or {}).get("faq_id") == fid)
check("带标点命中", (faq_priority.match_faq(SC, "门票多少钱？") or {}).get("faq_id") == fid)
check("语气词近似命中", (faq_priority.match_faq(SC, "门票多少钱呀") or {}).get("faq_id") == fid)
check("命中返回权威答案", "120" in (faq_priority.match_faq(SC, "门票多少钱") or {}).get("answer", ""))
check("无关问句不命中", faq_priority.match_faq(SC, "灵山大佛有多高") is None)
check("过短问句不命中", faq_priority.match_faq(SC, "嗯") is None)
check("弱相关不误命中", faq_priority.match_faq(SC, "最近的厕所在哪里") is None)

# ── 3. invalidate 生效 ───────────────────────────────
with get_db() as conn:
    conn.execute("DELETE FROM faq_items WHERE id=?", (fid,))
check("删后未失效仍读旧缓存", (faq_priority.match_faq(SC, "门票多少钱") or {}).get("faq_id") == fid)
faq_priority.invalidate(SC)
check("invalidate 后不再命中", faq_priority.match_faq(SC, "门票多少钱") is None)

_cleanup()

print(f"\n{'='*40}\n通过 {passed} / {passed + failed}")
sys.exit(0 if failed == 0 else 1)
