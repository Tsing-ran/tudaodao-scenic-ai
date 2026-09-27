import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/scenic", tags=["scenic"])

API_BASE = "http://127.0.0.1:6006/rag"


@router.get("/theme")
async def get_theme(scenic_id: str = Query("lingshan")):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/scenic/theme", params={"scenic_id": scenic_id})
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


@router.get("/themes")
async def get_themes():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/scenic/themes")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


class ThemeBody(BaseModel):
    scenic_id: str
    primary: Optional[str] = None
    sweet: Optional[str] = None
    name: Optional[str] = None
    guide_name: Optional[str] = None


@router.put("/theme")
async def update_theme(body: ThemeBody):
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{API_BASE}/scenic/theme", json=payload)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}
