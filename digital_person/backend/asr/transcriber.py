"""
本地 ASR：基于 faster-whisper(CTranslate2)的中文景区语音识别模块（自研封装）。

相对裸用 faster-whisper 的改造点（答辩可讲的技术增量）：
  1. 景区术语增强：注入各景区专有名词作热词(hotwords)，显著提升
     "九龙灌浴""阿育王柱"等生僻景点名的识别率——whisper 原生对这类专名易错。
  2. VAD 静音过滤：切除静音段，加速推理并抑制噪声误识别。
  3. CPU int8 运行：0 显存占用，不与本机 MuseTalk 抢 4080 的显存。
  4. 中文后处理：去首尾空白、规整。

懒加载：import 本模块不触发模型加载；首次 transcribe 才加载模型
（∴ 无 GPU/未装 faster-whisper 的 ECS 即便注册了路由也不会在启动时崩）。
"""
import os
import re
from functools import lru_cache

# 去掉中文字符之间的空格（small 模型偶尔把"九龙灌浴"切成"九龙 灌浴"）
_CJK_SPACE = re.compile(r"(?<=[一-鿿])\s+(?=[一-鿿])")

# 各景区专有名词热词表（提升 ASR 对生僻景点名的识别；新增景区时在此补充）
SCENIC_HOTWORDS: dict[str, str] = {
    "lingshan":  "灵山胜境 灵山大佛 九龙灌浴 阿育王柱 五印坛城 梵宫 降魔成道 百子戏弥勒 祥符禅寺 天下第一掌 五智门",
    "nihuawan":  "拈花湾 禅意小镇 香月花街 五灯湖 拈花塔 半山衔日 鹿鸣谷 波罗蜜广场",
    "xihu":      "西湖 断桥残雪 雷峰塔 三潭印月 苏堤春晓 曲院风荷 花港观鱼 平湖秋月 灵隐寺 六和塔",
    "huangshan": "黄山 迎客松 光明顶 莲花峰 天都峰 飞来石 始信峰 西海大峡谷 鳌鱼峰 一线天",
    "gugong":    "故宫 紫禁城 太和殿 乾清宫 养心殿 御花园 角楼 午门 神武门 保和殿",
}


@lru_cache(maxsize=1)
def get_model():
    """懒加载 WhisperModel，进程内单例。首次调用需几秒加载（或下载）模型。"""
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from faster_whisper import WhisperModel
    from backend.core.config import settings

    return WhisperModel(
        settings.asr_model,
        device=settings.asr_device,
        compute_type=settings.asr_compute,
        cpu_threads=settings.asr_cpu_threads,
    )


def transcribe(audio_path: str, scenic_id: str = "lingshan",
               language: str = "zh") -> dict:
    """
    转写音频文件为文字（统一入口）。
    识别引擎按 settings.asr_provider 调度：
      auto  —— 云端 qwen3-asr 优先（口音普通话/方言/专名识别显著更强），
               超时或失败自动落回本地 faster-whisper，游客侧永不失败；
      cloud —— 仅云端；local —— 仅本地。
    language: "zh" 强制中文；"auto" 自动检测。
    返回: { text, language, duration, hotwords_used, engine }
    """
    from backend.core.config import settings

    provider = settings.asr_provider
    if provider in ("auto", "cloud"):
        try:
            from backend.asr.cloud_asr import transcribe_cloud
            return transcribe_cloud(
                audio_path, scenic_id, language,
                model=settings.asr_cloud_model,
                timeout=settings.asr_cloud_timeout,
            )
        except Exception:
            if provider == "cloud":
                raise                     # 强制云端时如实报错
            # auto：静默落回本地引擎
    return _transcribe_local(audio_path, scenic_id, language)


def _transcribe_local(audio_path: str, scenic_id: str = "lingshan",
                      language: str = "zh") -> dict:
    """本地 faster-whisper 转写（0 显存 CPU 档，云端不可用时的兜底）。"""
    from backend.core.config import settings

    model = get_model()
    # 景区热词是中文专名，只在中文/自动识别时注入；英文等其它语言注入会把发音带偏
    # （如 Lingshan→Lingsang），故非中文时不加热词。
    hotwords = SCENIC_HOTWORDS.get(scenic_id, "") if language in ("zh", "auto", None) else ""
    segments, info = model.transcribe(
        audio_path,
        language=None if language == "auto" else language,
        hotwords=hotwords or None,        # 景区术语增强
        vad_filter=True,                  # VAD 静音过滤
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=settings.asr_beam_size,
    )
    text = "".join(seg.text for seg in segments).strip()
    text = _CJK_SPACE.sub("", text)       # 修复中文专名被切开的空格

    return {
        "text": text,
        "language": info.language,
        "duration": round(info.duration, 2),
        "hotwords_used": bool(hotwords),
        "engine": "local",
    }
