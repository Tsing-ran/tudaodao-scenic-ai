from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.wanxiang_service import generate_avatar_image, generate_scene_background
from config import SCENE_THEMES

router = APIRouter(prefix="/api/image", tags=["形象生成"])


class GenerateAvatarRequest(BaseModel):
    scene_type: str
    custom_prompt: Optional[str] = None


@router.post("/avatar/generate")
def generate_avatar(req: GenerateAvatarRequest):
    """
    调用通义万相生成景区数字人导览员形象图片

    scene_type: buddhist / nature / ancient_town / historical / modern
    """
    if req.scene_type not in SCENE_THEMES:
        raise HTTPException(status_code=400, detail=f"不支持的景区类型: {req.scene_type}")
    try:
        result = generate_avatar_image(req.scene_type, req.custom_prompt)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/background/generate")
def generate_background(scene_type: str):
    """调用通义万相生成景区背景图"""
    if scene_type not in SCENE_THEMES:
        raise HTTPException(status_code=400, detail=f"不支持的景区类型: {scene_type}")
    try:
        result = generate_scene_background(scene_type)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes")
def get_themes():
    """获取所有景区主题配置（供前端渲染主题选择器）"""
    themes = {}
    for key, val in SCENE_THEMES.items():
        themes[key] = {
            "name": val["name"],
            "example": val["example"],
            "colors": val["colors"],
            "decoration": val["decoration"],
            "greeting": val["greeting"],
        }
    return {"code": 0, "data": themes}
