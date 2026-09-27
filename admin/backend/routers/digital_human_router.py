import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/digital-human", tags=["digital-human"])

API_BASE = "http://127.0.0.1:6006/rag"


@router.get("/presets")
async def get_presets():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/digital-human/presets")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


@router.get("/config")
async def get_config(scenic_id: str = "lingshan"):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/digital-human/config", params={"scenic_id": scenic_id})
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


@router.get("/config/all")
async def get_config_all():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/digital-human/config/all")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}


class ConfigBody(BaseModel):
    scenic_id: str
    avatar_id: str
    avatar_name: str
    voice_id: str
    voice_name: str
    background_id: Optional[str] = ""
    background_name: Optional[str] = ""


@router.put("/config")
async def save_config(body: ConfigBody):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{API_BASE}/digital-human/config", json=body.model_dump())
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"code": 0, "data": r.json()}
