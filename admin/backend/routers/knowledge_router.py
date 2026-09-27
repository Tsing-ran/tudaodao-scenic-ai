import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

RAG_BASE = "http://127.0.0.1:6006/rag"


@router.get("/docs")
async def list_docs(scenic_id: Optional[str] = Query(None)):
    params = {}
    if scenic_id:
        params["scenic_id"] = scenic_id
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{RAG_BASE}/kb/docs", params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


@router.post("/upload")
async def upload_doc(
    scenic_id: str = Form(...),
    replace: bool = Form(False),
    files: list[UploadFile] = File(...),
):
    allowed = {".txt", ".pdf", ".docx", ".md"}
    for f in files:
        from pathlib import Path
        if Path(f.filename).suffix.lower() not in allowed:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{f.filename}")
        content = await f.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"文件超过 20MB：{f.filename}")
        await f.seek(0)

    async with httpx.AsyncClient(timeout=60) as client:
        file_tuples = [
            ("files", (f.filename, await f.read(), f.content_type or "application/octet-stream"))
            for f in files
        ]
        r = await client.post(
            f"{RAG_BASE}/kb/upload",
            data={"scenic_id": scenic_id, "replace": str(replace).lower()},
            files=file_tuples,
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


@router.delete("/docs/{doc_id}")
async def delete_doc(doc_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.delete(f"{RAG_BASE}/kb/docs/{doc_id}")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0}


@router.get("/list")
async def list_kb():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{RAG_BASE}/kb/list")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


# ── FAQ ──────────────────────────────────────────

class FaqBody(BaseModel):
    scenic_id: str
    question: str
    answer: str
    category: str = ""

@router.get("/faq")
async def list_faq(scenic_id: Optional[str] = Query(None)):
    params = {}
    if scenic_id:
        params["scenic_id"] = scenic_id
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{RAG_BASE}/kb/faq", params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.post("/faq")
async def add_faq(body: FaqBody):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{RAG_BASE}/kb/faq", json=body.model_dump())
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.put("/faq/{item_id}")
async def edit_faq(item_id: int, body: FaqBody):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{RAG_BASE}/kb/faq/{item_id}", json=body.model_dump())
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.delete("/faq/{item_id}")
async def delete_faq(item_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.delete(f"{RAG_BASE}/kb/faq/{item_id}")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0}


# ── 文本段落 ─────────────────────────────────────

class TextBody(BaseModel):
    scenic_id: str
    title: str = ""
    content: str
    category: str = ""

@router.get("/text")
async def list_text(scenic_id: Optional[str] = Query(None)):
    params = {}
    if scenic_id:
        params["scenic_id"] = scenic_id
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{RAG_BASE}/kb/text", params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.post("/text")
async def add_text(body: TextBody):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{RAG_BASE}/kb/text", json=body.model_dump())
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.put("/text/{item_id}")
async def edit_text(item_id: int, body: TextBody):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{RAG_BASE}/kb/text/{item_id}", json=body.model_dump())
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}

@router.delete("/text/{item_id}")
async def delete_text(item_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.delete(f"{RAG_BASE}/kb/text/{item_id}")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0}
