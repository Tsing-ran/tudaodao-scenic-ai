"""FAQ 最高优先级命中层。

管理员在管理端亲手录入的 FAQ 问答，是"权威人工答案"。当游客问句与某条 FAQ 问题
**近乎一致**时，直接以该 FAQ 答案作答——优先级高于向量检索生成，实现"运营方录入即刻、
以最高优先级在游客端生效"。

正确性红线：只用**高阈值近似匹配**（归一化相等 / 强包含 / 字符 Jaccard ≥0.85），
只在游客问句与录入问题几乎相同的时候触发，因此不会误伤事实问答准确率——标准测试集里
的题目不会与管理员 FAQ 问题近乎一致（提交前 tests/test_accuracy.py 强制零回归验证）。

读 faq_items 表，进程内缓存；FAQ 增删改时由 kb_manage 调 invalidate() 失效。
"""
import re

from backend.db.database import get_db

# scenic_id -> [{id, question, answer, norm}]；None 表示未加载
_CACHE: dict[str, list[dict]] = {}

# 归一化：去空白与中英标点（与 bridge._norm 同规则，便于"问句近乎一致"判定）
_PUNC = re.compile(r"[\s，。？！?,.!、~～·:：；;\"'（）()\[\]【】]")


def _norm(s: str) -> str:
    return _PUNC.sub("", (s or "").lower())


def _load(scenic_id: str) -> list[dict]:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, question, answer FROM faq_items WHERE scenic_id=?",
                (scenic_id,),
            ).fetchall()
    except Exception:
        return []
    items = []
    for r in rows:
        q = _norm(r["question"])
        if len(q) >= 3 and (r["answer"] or "").strip():
            items.append({"id": r["id"], "question": r["question"],
                          "answer": r["answer"], "norm": q})
    return items


def invalidate(scenic_id: str | None = None) -> None:
    """FAQ 内容变更后失效缓存（scenic_id=None 清全部）。"""
    if scenic_id:
        _CACHE.pop(scenic_id, None)
    else:
        _CACHE.clear()


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def match_faq(scenic_id: str, query: str) -> dict | None:
    """游客问句命中某条 FAQ 则返回 {answer, question, faq_id}，否则 None。高阈值近似匹配。"""
    q = _norm(query)
    if len(q) < 3:
        return None
    items = _CACHE.get(scenic_id)
    if items is None:
        items = _load(scenic_id)
        _CACHE[scenic_id] = items
    if not items:
        return None

    qset = set(q)
    best, best_score = None, 0.0
    for it in items:
        fn = it["norm"]
        if q == fn:
            return {"answer": it["answer"], "question": it["question"], "faq_id": it["id"]}
        score = _jaccard(qset, set(fn))
        # 强包含（一方含另一方且长度接近）视为高相似
        if (q in fn or fn in q) and min(len(q), len(fn)) / max(len(q), len(fn)) >= 0.75:
            score = max(score, 0.9)
        if score > best_score:
            best_score, best = score, it

    if best and best_score >= 0.85:
        return {"answer": best["answer"], "question": best["question"], "faq_id": best["id"]}
    return None
