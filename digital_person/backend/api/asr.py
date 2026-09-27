"""
语音识别接口：游客上传音频 → 转写为文字（云端 qwen3-asr 优先，本地 faster-whisper 兜底）。
转写结果可直接喂给 /chat 或桥接层 /live/ask，构成"语音问答"链路第一环。
"""
import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.asr.transcriber import transcribe

router = APIRouter(prefix="/asr", tags=["asr"])


@router.post("")
async def asr_endpoint(
    file: UploadFile = File(...),
    scenic_id: str = Form("lingshan"),
    language: str = Form("zh"),
):
    """
    上传音频文件（wav/mp3/m4a/webm…）→ 返回转写文字。
    scenic_id 用于注入对应景区术语热词，提升专名识别。
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="音频为空")

    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        # 放入线程池执行：转写要 1~2 秒，不能阻塞事件循环拖慢并发的问答请求
        return await run_in_threadpool(transcribe, path, scenic_id, language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR 转写失败: {e}")
    finally:
        os.unlink(path)
