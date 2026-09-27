"""
DashScope CosyVoice 语音合成服务
文档：https://help.aliyun.com/zh/model-studio/cosyvoice-tts-api
"""
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
from config import settings

# 景区主题 → 推荐音色
VOICE_MAP = {
    "buddhist":    "longxiaochun",   # 温柔女声，适合佛教文化
    "nature":      "longxiaoxia",    # 清新女声，适合自然山水
    "ancient_town":"longmiaomiao",   # 亲切女声，适合古镇民俗
    "historical":  "longshuo",       # 沉稳女声，适合历史遗址
    "modern":      "longxiaochun",   # 专业女声，适合现代主题
}


def synthesize_speech(text: str, scene_type: str = "buddhist") -> bytes:
    """
    调用 CosyVoice 将文字合成为语音，返回 MP3 音频字节

    Args:
        text:       要合成的文本
        scene_type: 景区类型，决定音色选择

    Returns:
        MP3 音频字节数据
    """
    dashscope.api_key = settings.DASHSCOPE_API_KEY

    voice = VOICE_MAP.get(scene_type, "longxiaochun")

    synthesizer = SpeechSynthesizer(
        model="cosyvoice-v1",
        voice=voice,
        format=AudioFormat.MP3_22050HZ_MONO_256KBPS,
    )

    audio = synthesizer.call(text)
    if audio is None:
        raise RuntimeError("CosyVoice 合成失败，返回空数据")
    return audio
