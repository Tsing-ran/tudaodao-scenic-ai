"""
通义万相数字人形象生成服务
调用 DashScope 万相文生图 API，根据景区类型生成匹配的数字人导览员形象
"""
import dashscope
from dashscope import ImageSynthesis
from config import settings, SCENE_THEMES


def generate_avatar_image(scene_type: str, custom_prompt: str = None, size: str = "768*1024") -> dict:
    """
    调用通义万相生成数字人形象图片

    Args:
        scene_type: 景区类型 (buddhist/nature/ancient_town/historical/modern)
        custom_prompt: 自定义提示词，为空则使用预设主题提示词
        size: 图片尺寸，默认 768*1024（竖版人像最佳）

    Returns:
        {"url": "...", "scene_type": "...", "prompt": "..."}
    """
    dashscope.api_key = settings.DASHSCOPE_API_KEY

    theme = SCENE_THEMES.get(scene_type, SCENE_THEMES["buddhist"])
    prompt = custom_prompt or theme["avatar_prompt"]
    negative_prompt = theme.get("avatar_negative", "低质量，模糊，变形")

    response = ImageSynthesis.call(
        model="wanx2.1-t2i-turbo",
        prompt=prompt,
        negative_prompt=negative_prompt,
        n=1,
        size=size,
        style="<photography>",
    )

    if response.status_code == 200:
        result_url = response.output.results[0].url
        return {
            "url": result_url,
            "scene_type": scene_type,
            "theme_name": theme["name"],
            "prompt": prompt,
        }
    else:
        raise RuntimeError(f"通义万相调用失败: {response.code} - {response.message}")


def generate_scene_background(scene_type: str) -> dict:
    """
    生成景区背景图（用于前端主题背景）

    Args:
        scene_type: 景区类型

    Returns:
        {"url": "...", "scene_type": "..."}
    """
    dashscope.api_key = settings.DASHSCOPE_API_KEY

    background_prompts = {
        "buddhist": (
            "灵山胜境全景，金色大佛耸立，莲花池倒映，太湖碧波，"
            "佛教建筑群，晨光霞彩，庄严神圣，超广角，8K风景大片"
        ),
        "nature": (
            "壮阔自然山水，云海翻涌，奇峰林立，绿意盎然，"
            "日出金光，仙境意境，超广角，8K风景大片"
        ),
        "ancient_town": (
            "江南水乡古镇，白墙黛瓦，小桥流水，烟雨朦胧，"
            "古色古香，诗情画意，超广角，8K风景大片"
        ),
        "historical": (
            "宏伟历史遗址，古城墙巍峨，斜阳金辉，历史厚重，"
            "文明印记，超广角，8K风景大片"
        ),
        "modern": (
            "现代科技展馆，蓝色光效，几何建筑，科技感十足，"
            "未来感，超广角，8K风景大片"
        ),
    }

    prompt = background_prompts.get(scene_type, background_prompts["buddhist"])

    response = ImageSynthesis.call(
        model="wanx2.1-t2i-turbo",
        prompt=prompt,
        n=1,
        size="1920*1080",
    )

    if response.status_code == 200:
        return {
            "url": response.output.results[0].url,
            "scene_type": scene_type,
        }
    else:
        raise RuntimeError(f"背景图生成失败: {response.code} - {response.message}")
