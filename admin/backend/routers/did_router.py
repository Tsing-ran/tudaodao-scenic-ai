from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.did_service import (
    create_stream, send_sdp_answer, send_ice_candidate,
    send_talk, close_stream, list_presenters,
)
from config import settings

router = APIRouter(prefix="/api/did", tags=["D-ID数字人"])


class SDPRequest(BaseModel):
    stream_id: str
    session_id: str
    answer: dict


class ICERequest(BaseModel):
    stream_id: str
    session_id: str
    candidate: str
    sdpMid: str
    sdpMLineIndex: int


class TalkRequest(BaseModel):
    stream_id: str
    session_id: str
    text: str


class CloseRequest(BaseModel):
    stream_id: str
    session_id: str


@router.get("/presenters")
async def get_presenters():
    """查询 D-ID 可用主播列表"""
    try:
        data = await list_presenters()
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stream/create")
async def create(avatar_url: str = None):
    """
    创建 D-ID 流会话，返回 WebRTC offer 供浏览器连接
    avatar_url 为空时使用管理端最后生成的万相图片
    """
    url = avatar_url or settings.DID_AVATAR_URL
    if not url:
        raise HTTPException(400, "请先在管理端生成数字人形象，或传入 avatar_url")
    try:
        data = await create_stream(url)
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stream/sdp")
async def sdp(req: SDPRequest):
    """浏览器完成 WebRTC 协商后，把 Answer SDP 发给 D-ID"""
    try:
        data = await send_sdp_answer(req.stream_id, req.answer, req.session_id)
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stream/ice")
async def ice(req: ICERequest):
    """转发 ICE Candidate"""
    try:
        data = await send_ice_candidate(
            req.stream_id,
            {"candidate": req.candidate, "sdpMid": req.sdpMid, "sdpMLineIndex": req.sdpMLineIndex},
            req.session_id,
        )
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stream/talk")
async def talk(req: TalkRequest):
    """驱动数字人说话（每句回答调用一次）"""
    try:
        data = await send_talk(req.stream_id, req.text, req.session_id)
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stream/close")
async def close(req: CloseRequest):
    """关闭流，释放 D-ID credits"""
    try:
        await close_stream(req.stream_id, req.session_id)
        return {"code": 0}
    except Exception as e:
        raise HTTPException(500, str(e))
