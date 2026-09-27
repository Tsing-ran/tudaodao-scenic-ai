"""
多模态聊天接口：游客上传图片提问，用 qwen-vl-max 回答。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.multimodal import answer_with_image, locate_landmark
from backend.db.database import save_conversation
from backend.rag.pipeline import get_scenic_config, answer as rag_answer
from backend.core.config import settings

router = APIRouter(prefix="/chat", tags=["multimodal"])


class ImageChatRequest(BaseModel):
    session_id: str = "anonymous"
    scenic_id: str = "lingshan"
    image_b64: str              # base64 编码的图片
    image_format: str = "jpeg"  # jpeg / png / webp
    question: str = "请介绍一下图片里的内容"
    group_type: str = "adult"   # adult/family_kids/senior/couple，切换讲解人格
    lang: str = "auto"
    ground: bool = True         # True=两段式（VL 定位 + RAG 接地讲解，压幻觉）；False=单次 VL


class ImageChatResponse(BaseModel):
    reply: str
    emotion: str
    location: str | None = None   # 识别到的景区地标（如"大佛广场"），无法定位时为 null
    model_used: str = "qwen3-vl-plus"


@router.post("/image", response_model=ImageChatResponse)
async def image_chat_endpoint(req: ImageChatRequest):
    if not req.image_b64:
        raise HTTPException(status_code=400, detail="image_b64 不能为空")

    cfg = get_scenic_config(req.scenic_id)

    try:
        # 两段式：① VL 只认地标 ② 认出则交 RAG 做接地讲解+指路（事实由知识库约束，压幻觉）
        location = None
        if req.ground:
            location = locate_landmark(
                image_b64=req.image_b64,
                scenic_name=cfg["name"],
                image_format=req.image_format,
            )
        if location:
            # 复用 97.7% 准确的 RAG 链路（自动走 navigation 意图 + group_type 人格）
            nav_query = (
                f"游客正站在{location}。请先用一句话确认所在位置，"
                f"再生动讲解{location}的文化背景与看点，"
                f"最后推荐接下来最值得去的1~2个邻近景点，并给出步行方向指引"
                f"（用相对方向，不要编造精确米数）。"
            )
            res = rag_answer(
                query=nav_query,
                scenic_id=req.scenic_id,
                session_id=req.session_id,
                lang=req.lang,
                group_type=req.group_type,
            )
            reply, emotion = res["reply"], res["emotion"]
        else:
            # 未识别（或 ground=False）：单次 VL，礼貌引导/直接看图作答
            reply, emotion, location = answer_with_image(
                image_b64=req.image_b64,
                question=req.question,
                scenic_name=cfg["name"],
                image_format=req.image_format,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"多模态模型调用失败: {e}")

    loc_note = f"（定位：{location}）" if location else ""
    save_conversation(
        session_id=req.session_id,
        scenic_id=req.scenic_id,
        user_message=f"[拍照] {req.question}{loc_note}",
        ai_reply=reply,
        emotion=emotion,
        context_used=bool(location),
    )

    return ImageChatResponse(reply=reply, emotion=emotion, location=location,
                             model_used=settings.vl_model)
