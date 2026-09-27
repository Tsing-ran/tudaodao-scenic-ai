"""管理端知识库编辑：FAQ / 文本段落 的逐条 CRUD（持久化到 SQLite）+ 实时同步进 RAG 向量库。

与 /kb/upload（整文档上传）互补：这里是管理员手填的细粒度知识条目，新增/编辑即时
以稳定 id upsert 进对应景区的 ChromaDB collection，删除即时移除——游客问答立刻能检索到。
契约见 API_DOC「知识库内容管理」节。供队友管理端前端直接调（经 /rag/kb/... 公网网关）。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db.database import get_db
from backend.rag.indexer import upsert_item, delete_item
from backend.rag.cache import answer_cache
from backend.rag import faq_priority

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _flush_answer_cache(scenic_id: str) -> None:
    """知识内容变更后清该景区答案缓存——否则旧问句短时间仍命中改前答案。"""
    answer_cache.invalidate(scenic_id)
    faq_priority.invalidate(scenic_id)   # FAQ 优先级层缓存同步失效


# ───────────────────────── FAQ ─────────────────────────
class FaqIn(BaseModel):
    scenic_id: str = "lingshan"
    question: str
    answer: str
    category: str = ""


def _faq_text(question: str, answer: str) -> str:
    return f"问：{question}\n答：{answer}"


@router.get("/faq")
def list_faq(scenic_id: str | None = None):
    """列出 FAQ（可按 scenic_id 过滤）。"""
    with get_db() as conn:
        if scenic_id:
            rows = conn.execute("SELECT * FROM faq_items WHERE scenic_id=? ORDER BY updated_at DESC", (scenic_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM faq_items ORDER BY updated_at DESC").fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/faq")
def create_faq(body: FaqIn):
    """新增 FAQ → 落库 + 同步进 RAG。"""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO faq_items (scenic_id, question, answer, category) VALUES (?,?,?,?)",
            (body.scenic_id, body.question, body.answer, body.category),
        )
        new_id = cur.lastrowid
    upsert_item(body.scenic_id, f"faq_{new_id}", _faq_text(body.question, body.answer),
                {"source": "faq", "faq_id": new_id, "category": body.category})
    _flush_answer_cache(body.scenic_id)
    return {"id": new_id, "scenic_id": body.scenic_id, "synced": True}


@router.put("/faq/{item_id}")
def update_faq(item_id: int, body: FaqIn):
    """编辑 FAQ → 更新库 + 重新同步进 RAG（旧景区若变更则从旧库移除）。"""
    with get_db() as conn:
        old = conn.execute("SELECT scenic_id FROM faq_items WHERE id=?", (item_id,)).fetchone()
        if not old:
            raise HTTPException(404, "FAQ 不存在")
        conn.execute(
            """UPDATE faq_items SET scenic_id=?, question=?, answer=?, category=?,
               updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE id=?""",
            (body.scenic_id, body.question, body.answer, body.category, item_id),
        )
    if old["scenic_id"] != body.scenic_id:
        delete_item(old["scenic_id"], f"faq_{item_id}")
        faq_priority.invalidate(old["scenic_id"])
    upsert_item(body.scenic_id, f"faq_{item_id}", _faq_text(body.question, body.answer),
                {"source": "faq", "faq_id": item_id, "category": body.category})
    _flush_answer_cache(body.scenic_id)
    return {"id": item_id, "synced": True}


@router.delete("/faq/{item_id}")
def remove_faq(item_id: int):
    """删除 FAQ → 删库 + 从 RAG 移除。"""
    with get_db() as conn:
        row = conn.execute("SELECT scenic_id FROM faq_items WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "FAQ 不存在")
        conn.execute("DELETE FROM faq_items WHERE id=?", (item_id,))
    delete_item(row["scenic_id"], f"faq_{item_id}")
    _flush_answer_cache(row["scenic_id"])
    return {"deleted": item_id}


# ─────────────────────── 文本段落 ───────────────────────
class TextIn(BaseModel):
    scenic_id: str = "lingshan"
    title: str = ""
    content: str
    category: str = ""


def _text_doc(title: str, content: str) -> str:
    return f"{title}\n{content}".strip() if title else content


@router.get("/text")
def list_text(scenic_id: str | None = None):
    with get_db() as conn:
        if scenic_id:
            rows = conn.execute("SELECT * FROM text_items WHERE scenic_id=? ORDER BY updated_at DESC", (scenic_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM text_items ORDER BY updated_at DESC").fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/text")
def create_text(body: TextIn):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO text_items (scenic_id, title, content, category) VALUES (?,?,?,?)",
            (body.scenic_id, body.title, body.content, body.category),
        )
        new_id = cur.lastrowid
    upsert_item(body.scenic_id, f"text_{new_id}", _text_doc(body.title, body.content),
                {"source": "text", "text_id": new_id, "category": body.category})
    _flush_answer_cache(body.scenic_id)
    return {"id": new_id, "scenic_id": body.scenic_id, "synced": True}


@router.put("/text/{item_id}")
def update_text(item_id: int, body: TextIn):
    with get_db() as conn:
        old = conn.execute("SELECT scenic_id FROM text_items WHERE id=?", (item_id,)).fetchone()
        if not old:
            raise HTTPException(404, "文本段落不存在")
        conn.execute(
            """UPDATE text_items SET scenic_id=?, title=?, content=?, category=?,
               updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE id=?""",
            (body.scenic_id, body.title, body.content, body.category, item_id),
        )
    if old["scenic_id"] != body.scenic_id:
        delete_item(old["scenic_id"], f"text_{item_id}")
    upsert_item(body.scenic_id, f"text_{item_id}", _text_doc(body.title, body.content),
                {"source": "text", "text_id": item_id, "category": body.category})
    _flush_answer_cache(body.scenic_id)
    return {"id": item_id, "synced": True}


@router.delete("/text/{item_id}")
def remove_text(item_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT scenic_id FROM text_items WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "文本段落不存在")
        conn.execute("DELETE FROM text_items WHERE id=?", (item_id,))
    delete_item(row["scenic_id"], f"text_{item_id}")
    _flush_answer_cache(row["scenic_id"])
    return {"deleted": item_id}


# ─────────────────── 上传文档列表（真实记录） ───────────────────
@router.get("/docs")
def list_docs(scenic_id: str | None = None):
    """已上传文档的真实清单（文件名/大小/chunk数/状态/时间）。供前端文档列表，告别假文件名。"""
    with get_db() as conn:
        if scenic_id:
            rows = conn.execute("SELECT * FROM uploaded_docs WHERE scenic_id=? ORDER BY created_at DESC", (scenic_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM uploaded_docs ORDER BY created_at DESC").fetchall()
    return {"docs": [dict(r) for r in rows]}


@router.delete("/docs/{doc_id}")
def remove_doc(doc_id: int):
    """删除文档：登记行 + 该文档在向量库中的全部 chunk（按 source=文件名精准删除）。

    注意：同名文件多次上传共享同一 source，删除会移除该文件名的所有 chunk。
    """
    with get_db() as conn:
        row = conn.execute("SELECT scenic_id, filename FROM uploaded_docs WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "文档记录不存在")
        conn.execute("DELETE FROM uploaded_docs WHERE id=?", (doc_id,))
    from backend.rag.retriever import get_collection, invalidate_entity_cache
    try:
        get_collection(row["scenic_id"]).delete(where={"source": row["filename"]})
    except Exception:
        pass
    invalidate_entity_cache(row["scenic_id"])
    _flush_answer_cache(row["scenic_id"])
    return {"deleted": doc_id, "chunks_removed": True}


@router.post("/docs/{doc_id}/reindex")
def reindex_doc(doc_id: int):
    """重建文档索引：删旧 chunk（按 source）→ 重新解析原文件 → 重新分块向量化入库。

    适用场景：分块参数调整后刷新、入库异常修复、原文件被替换后重灌。
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM uploaded_docs WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "文档记录不存在")
    from backend.core.config import settings
    path = settings.knowledge_base_dir / row["scenic_id"] / row["filename"]
    if not path.exists():
        raise HTTPException(410, f"原始文件已不存在：{row['filename']}，请重新上传")

    from backend.rag.indexer import index_documents
    from backend.rag.retriever import get_collection, invalidate_entity_cache
    try:
        get_collection(row["scenic_id"]).delete(where={"source": row["filename"]})
    except Exception:
        pass
    chunks = index_documents([path], row["scenic_id"])
    status = "indexed" if chunks > 0 else "unsupported"
    with get_db() as conn:
        conn.execute("UPDATE uploaded_docs SET chunks=?, status=? WHERE id=?",
                     (chunks, status, doc_id))
    invalidate_entity_cache(row["scenic_id"])
    _flush_answer_cache(row["scenic_id"])
    return {"id": doc_id, "filename": row["filename"], "chunks": chunks, "status": status}


# ─────────────────── 检索设置（管理端「检索参数」真实生效） ───────────────────
class RetrievalConfigIn(BaseModel):
    scenic_id: str = "lingshan"
    strategy: str = "hybrid"                    # hybrid | semantic | keyword
    top_k: int | None = Field(default=None, ge=1, le=10)     # 最终返回 chunk 数
    threshold: float | None = Field(default=None, ge=0, le=1)  # 置信度门控（local 模式生效）


@router.get("/retrieval-config")
def get_retrieval_config(scenic_id: str = "lingshan"):
    """当前检索参数。configured=False 表示未配置过、走系统默认基线。"""
    from backend.rag.retrieval_config import get_overrides
    from backend.core.config import settings
    ov = get_overrides(scenic_id)
    return {
        "scenic_id": scenic_id,
        "configured": ov.top_k is not None or ov.threshold is not None or ov.strategy != "hybrid",
        "strategy": ov.strategy,
        "top_k": ov.top_k or settings.rerank_top_k,
        "threshold": ov.threshold if ov.threshold is not None else settings.ea_gate_threshold,
        "defaults": {"strategy": "hybrid", "top_k": settings.rerank_top_k,
                     "threshold": settings.ea_gate_threshold},
    }


@router.put("/retrieval-config")
def put_retrieval_config(body: RetrievalConfigIn):
    """保存检索参数（立即生效于该景区后续检索）。改动会清答案缓存以免新旧参数混答。"""
    from backend.rag.retrieval_config import set_overrides, STRATEGIES
    if body.strategy not in STRATEGIES:
        raise HTTPException(422, f"strategy 必须是 {STRATEGIES} 之一")
    set_overrides(body.scenic_id, body.strategy, body.top_k, body.threshold)
    _flush_answer_cache(body.scenic_id)
    return {"scenic_id": body.scenic_id, "saved": True}


@router.delete("/retrieval-config")
def delete_retrieval_config(scenic_id: str = "lingshan"):
    """恢复系统默认检索参数（删除该景区覆盖行）。"""
    from backend.rag.retrieval_config import reset_overrides
    reset_overrides(scenic_id)
    _flush_answer_cache(scenic_id)
    return {"scenic_id": scenic_id, "reset": True}
