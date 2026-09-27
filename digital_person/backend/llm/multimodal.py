"""
多模态问答：qwen-vl-max。
满足赛题"至少使用 1 个多模态大模型"的硬性要求。

不只是"看图答题"，而是**视觉定位 + 口语指路**的随身导游（创新三 / AR-lite）：
游客举起手机拍下眼前景物 → 模型像真人导游一样：
  ① 定位：判断这是本景区哪个地标，先告诉游客"您正站在 X"
  ② 讲解：以会讲故事的导游口吻介绍文化背景与看点
  ③ 指路：主动推荐邻近景点并给方向性指引（往…方向，步行约几分钟）

程序解析两个标签：[位置:X]（给前端显示 📍 当前位置）、[情绪:X]（驱动数字人表情）。
"""

import base64
import re
from pathlib import Path

import dashscope
from dashscope import MultiModalConversation

from backend.core.config import settings
from backend.llm.client import extract_emotion

dashscope.api_key = settings.dashscope_api_key

# [位置:X] 标签：X 为识别到的景区地标名；未识别景区地标时为"未识别"
_LOCATION_RE = re.compile(r'\[位置[：:]\s*([^\]]+?)\s*\]')


def _build_vl_system(scenic_name: str) -> str:
    return f"""你是{scenic_name}的随身AI导游。游客此刻**人就在{scenic_name}景区内**，举起手机拍下了眼前的景物，请像一位热情、会讲故事的真人导游那样，按下面的顺序回答：

① 定位：判断画面里是{scenic_name}的哪个地标或景点。
   - 游客就在本景区，所以只要画面像是{scenic_name}的景物，就优先判断它是本景区的哪个具体景点，第一句明确告诉游客所在位置，例如"您现在正站在大佛广场，眼前就是灵山大佛"。
   - 只有当画面明显不是景区景物（随手拍的人、食物、天空，或一眼看出是别处的地标）时，才说明暂时无法据此定位，并礼貌引导游客对准景点再拍。
② 讲解：用生动、会讲故事的导游口吻，介绍这个景点的文化背景、最值得看的地方，再讲一个有意思的小故事或细节，别干巴巴罗列事实。
③ 指路：主动为游客推荐接下来最值得去的 1~2 个邻近景点，并给出方向性指引。
   方向用"往……方向，步行大约几分钟"这种相对描述即可；不要编造精确的米数或门牌号。

严格遵守以下格式（供程序解析，游客看不到标签本身）：
- 正文最前面单独一行标注识别到的位置：[位置:大佛广场]；若无法识别为景区地标，则写 [位置:未识别]。
- 正文最后单独一行标注情绪：[情绪:开心] 或 [情绪:兴奋] 或 [情绪:平静] 或 [情绪:好奇] 或 [情绪:关切] 或 [情绪:抱歉]。
中间正文用自然口语连贯成段，不要出现"①②③"这类编号。"""


def _extract_location(text: str) -> tuple[str, str | None]:
    """解析 [位置:X] 标签。返回 (去掉标签的正文, location 或 None)。'未识别' 归一为 None。"""
    m = _LOCATION_RE.search(text)
    if not m:
        return text, None
    loc = m.group(1).strip()
    clean = (text[:m.start()] + text[m.end():]).strip()
    if loc in ("未识别", "无", "未知", ""):
        return clean, None
    return clean, loc


def locate_landmark(
    image_b64: str,
    scenic_name: str = "灵山胜境",
    image_format: str = "jpeg",
) -> str | None:
    """视觉定位（两段式第一段）：只识别这是本景区的哪个地标，返回地标名或 None。

    只让 qwen-vl 做它最擅长的"认地标"，讲解/指路交给 RAG（事实由知识库约束，压幻觉）。
    """
    system = (
        f"游客此刻人在{scenic_name}景区内，拍了这张照片。请只判断这是{scenic_name}的哪个景点。"
        f"规则：能确定就只输出景点名称（例如：大佛广场），不要任何多余文字、标点或解释；"
        f"若画面明显不是景区景物（人、食物、天空）或一眼看出是别处地标，就只输出两个字：未识别。"
    )
    image_url = f"data:image/{image_format};base64,{image_b64}"
    messages = [
        {"role": "system", "content": [{"text": system}]},
        {"role": "user", "content": [{"image": image_url}, {"text": "这是哪个景点？"}]},
    ]
    response = MultiModalConversation.call(model=settings.vl_model, messages=messages)
    if response.status_code != 200 or response.output is None:
        raise RuntimeError(
            f"DashScope 多模态调用失败 [{response.status_code} {response.code}]: {response.message}"
        )
    raw = response.output.choices[0].message.content[0]["text"].strip()
    # 清掉可能的标点/换行/标签残留，只留景点名
    loc = raw.strip().strip("。.！!，,、：:").splitlines()[0].strip() if raw else ""
    if not loc or loc in ("未识别", "无", "未知") or len(loc) > 20:
        return None
    return loc


def answer_with_image(
    image_b64: str,
    question: str,
    scenic_name: str = "灵山胜境",
    image_format: str = "jpeg",
) -> tuple[str, str, str | None]:
    """
    输入 base64 图片 + 文字问题，返回 (reply, emotion, location)。
    location 为识别到的景区地标名（如"大佛广场"），无法定位时为 None。
    image_format: jpeg / png / webp / gif
    """
    image_url = f"data:image/{image_format};base64,{image_b64}"
    messages = [
        {"role": "system", "content": [{"text": _build_vl_system(scenic_name)}]},
        {
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": question or "我面前是什么？请帮我定位、讲解，并指引我接下来去哪。"},
            ],
        },
    ]
    response = MultiModalConversation.call(
        model=settings.vl_model,
        messages=messages,
    )
    if response.status_code != 200 or response.output is None:
        raise RuntimeError(
            f"DashScope 多模态调用失败 [{response.status_code} {response.code}]: {response.message}"
        )
    raw = response.output.choices[0].message.content[0]["text"]
    # 先剥位置标签，再剥情绪标签
    body, location = _extract_location(raw)
    reply, emotion = extract_emotion(body)
    return reply, emotion, location


def answer_with_image_file(
    image_path: str | Path,
    question: str,
    scenic_name: str = "灵山胜境",
) -> tuple[str, str, str | None]:
    """便捷函数：从本地文件读取图片。"""
    path = Path(image_path)
    fmt = path.suffix.lstrip(".").lower()
    fmt = "jpeg" if fmt in ("jpg", "jpeg") else fmt
    b64 = base64.b64encode(path.read_bytes()).decode()
    return answer_with_image(b64, question, scenic_name, fmt)
