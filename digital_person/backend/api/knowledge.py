import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import chromadb

from backend.rag.indexer import index_documents, clear_scenic
from backend.core.config import settings

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("/upload")
async def upload_documents(
    scenic_id: str = Form(...),
    files: list[UploadFile] = File(...),
    replace: bool = Form(False),
):
    """上传文档并入库。replace=True 时先清空该景区知识库。"""
    save_dir = settings.knowledge_base_dir / scenic_id
    save_dir.mkdir(parents=True, exist_ok=True)

    if replace:
        clear_scenic(scenic_id)

    saved_paths: list[Path] = []
    for file in files:
        dest = save_dir / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_paths.append(dest)

    # 逐文件入库 + 登记到 uploaded_docs（前端文档列表查 GET /kb/docs，得真实 chunk 数/状态）
    from backend.db.database import get_db
    total = 0
    results = []
    with get_db() as conn:
        for p in saved_paths:
            chunks = index_documents([p], scenic_id)   # 按后缀分派 docx/pdf/txt/md
            total += chunks
            status = "indexed" if chunks > 0 else "unsupported"  # 不支持的格式：存档但未入 RAG
            size = p.stat().st_size if p.exists() else 0
            conn.execute(
                """INSERT INTO uploaded_docs (scenic_id, filename, size_bytes, chunks, status)
                   VALUES (?,?,?,?,?)""",
                (scenic_id, p.name, size, chunks, status),
            )
            results.append({"filename": p.name, "chunks": chunks, "status": status})
    return {"scenic_id": scenic_id, "files": len(saved_paths), "chunks_indexed": total, "items": results}


@router.get("/list")
async def list_knowledge_bases():
    """查询所有景区知识库的 chunk 数量。"""
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    result = {}
    for col in client.list_collections():
        scenic_id = col.name.removeprefix("scenic_")
        result[scenic_id] = col.count()
    return result


@router.delete("/{scenic_id}")
async def delete_knowledge_base(scenic_id: str):
    clear_scenic(scenic_id)
    return {"deleted": scenic_id}
