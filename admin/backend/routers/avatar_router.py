from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.avatar_service import (
    start_avatar_session,
    send_text_to_avatar,
    stop_avatar_session,
    query_avatar_list,
    submit_text_to_video,
    get_video_task_info,
)

router = APIRouter(prefix="/api/avatar", tags=["数字人会话"])


class SendTextRequest(BaseModel):
    session_id: str
    text: str


class StopSessionRequest(BaseModel):
    session_id: str


class VideoTaskRequest(BaseModel):
    avatar_id: str
    text: str
    title: str = "景区导览视频"


@router.post("/session/start")
def start_session(user_id: str = None):
    """启动数字人实时会话，返回前端渲染所需凭证"""
    try:
        result = start_avatar_session(user_id)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/send")
def send_text(req: SendTextRequest):
    """向数字人发送播报文本（由Q&A模块调用）"""
    try:
        ok = send_text_to_avatar(req.session_id, req.text)
        return {"code": 0, "data": {"success": ok}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stop")
def stop_session(req: StopSessionRequest):
    """停止数字人会话"""
    try:
        ok = stop_avatar_session(req.session_id)
        return {"code": 0, "data": {"success": ok}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_avatars():
    """查询可用的数字人形象列表"""
    try:
        avatars = query_avatar_list()
        return {"code": 0, "data": {"avatars": avatars}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/submit")
def submit_video(req: VideoTaskRequest):
    """提交离线文字转数字人视频任务"""
    try:
        result = submit_text_to_video(req.avatar_id, req.text, req.title)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/status/{task_id}")
def get_video_status(task_id: str):
    """查询视频合成任务状态"""
    try:
        result = get_video_task_info(task_id)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
