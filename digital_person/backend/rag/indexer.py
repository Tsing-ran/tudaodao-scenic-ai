"""
知识库入库：把文档分块、向量化、存入对应景区的 ChromaDB collection。
"""

from pathlib import Path
from typing import List
import uuid
import chromadb

from backend.rag.loader import load_file_as_chunks
from backend.rag.retriever import get_collection
from backend.core.config import settings


def _embed(texts):
    if settings.deploy_mode == "cloud":
        from backend.rag.embedder_dashscope import embed_texts_cloud
        return embed_texts_cloud(texts)
    from backend.rag.embedder import embed_texts
    return embed_texts(texts)


def index_documents(file_paths: List[Path], scenic_id: str) -> int:
    """
    将文档列表入库到指定景区的 collection。
    返回本次入库的 chunk 总数。
    """
    collection = get_collection(scenic_id)

    all_chunks: List[dict] = []
    for path in file_paths:
        chunks = load_file_as_chunks(
            path,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    texts = [c["text"] for c in all_chunks]
    embeddings = _embed(texts)

    collection.add(
        ids=[str(uuid.uuid4()) for _ in texts],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"source": c["source"]} for c in all_chunks],
    )
    return len(texts)


def upsert_item(scenic_id: str, item_id: str, text: str, metadata: dict | None = None) -> None:
    """把管理端单条 FAQ/文本以稳定 id 增量写入 RAG（先删同 id 再加 = upsert）。"""
    from backend.rag.retriever import invalidate_entity_cache
    collection = get_collection(scenic_id)
    try:
        collection.delete(ids=[item_id])
    except Exception:
        pass
    collection.add(
        ids=[item_id],
        documents=[text],
        embeddings=_embed([text]),
        metadatas=[metadata or {"source": item_id}],
    )
    invalidate_entity_cache(scenic_id)


def delete_item(scenic_id: str, item_id: str) -> None:
    """从 RAG 删除单条（按稳定 id）。"""
    from backend.rag.retriever import invalidate_entity_cache
    try:
        get_collection(scenic_id).delete(ids=[item_id])
    except Exception:
        pass
    invalidate_entity_cache(scenic_id)


def clear_scenic(scenic_id: str) -> None:
    """清空某景区的知识库（重新上传时先清空）。"""
    from backend.rag.retriever import invalidate_entity_cache
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    try:
        client.delete_collection(f"scenic_{scenic_id}")
    except Exception:
        pass
    invalidate_entity_cache(scenic_id)  # EA-RAG 景点名缓存随知识库失效
