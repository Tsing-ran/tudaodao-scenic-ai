from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from services.tts_service import synthesize_speech

router = APIRouter(prefix="/api/tts", tags=["语音合成"])


class TTSRequest(BaseModel):
    text: str
    scene_type: str = "buddhist"


@router.post("/synthesize")
def tts(req: TTSRequest):
    """
    文字转语音（CosyVoice），返回 MP3 音频流
    前端收到后直接用 Audio 播放
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    try:
        audio_bytes = synthesize_speech(req.text, req.scene_type)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
