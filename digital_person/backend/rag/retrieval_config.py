"""管理端「检索设置」的按景区参数覆盖。

原则：无配置行 = 完全沿用 settings 默认（97.1% 准确率基线零扰动）；
管理员显式保存后才覆盖对应景区。进程内缓存，PUT 时失效。

strategy: hybrid（稠密+BM25 混合，默认）| semantic（仅稠密）| keyword（仅 BM25）
top_k:    最终返回 chunk 数（覆盖 settings.rerank_top_k），1-10
threshold: 置信度门控阈值（覆盖 settings.ea_gate_threshold，仅 local 模式生效），0-1
"""
from dataclasses import dataclass

from backend.db.database import get_db

STRATEGIES = ("hybrid", "semantic", "keyword")


@dataclass(frozen=True)
class RetrievalOverrides:
    strategy: str = "hybrid"
    top_k: int | None = None
    threshold: float | None = None


_DEFAULT = RetrievalOverrides()
_cache: dict[str, RetrievalOverrides] = {}


def get_overrides(scenic_id: str) -> RetrievalOverrides:
    if scenic_id in _cache:
        return _cache[scenic_id]
    with get_db() as conn:
        row = conn.execute(
            "SELECT strategy, top_k, threshold FROM kb_retrieval_config WHERE scenic_id=?",
            (scenic_id,),
        ).fetchone()
    ov = RetrievalOverrides(row[0], row[1], row[2]) if row else _DEFAULT
    _cache[scenic_id] = ov
    return ov


def set_overrides(scenic_id: str, strategy: str, top_k: int | None, threshold: float | None) -> None:
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy 必须是 {STRATEGIES} 之一")
    with get_db() as conn:
        conn.execute(
            """INSERT INTO kb_retrieval_config (scenic_id, strategy, top_k, threshold,
                                                updated_at)
               VALUES (?,?,?,?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
               ON CONFLICT(scenic_id) DO UPDATE SET
                 strategy=excluded.strategy, top_k=excluded.top_k,
                 threshold=excluded.threshold, updated_at=excluded.updated_at""",
            (scenic_id, strategy, top_k, threshold),
        )
    _cache.pop(scenic_id, None)


def reset_overrides(scenic_id: str) -> None:
    """恢复默认：删行 + 清缓存，检索回到 settings 基线。"""
    with get_db() as conn:
        conn.execute("DELETE FROM kb_retrieval_config WHERE scenic_id=?", (scenic_id,))
    _cache.pop(scenic_id, None)
