"""拍照打卡·闭集核验（qwen-vl）。

不做开放世界识别（"这是什么"→易幻觉），而是给 VL **候选景点 + 各自标志性特征**，
让它判别照片是候选里的哪一个（或都不是），并**强制结构化输出它真实看到的 evidence**。
闭集 + 特征锚定 → 准确率高；evidence（具体特征）→ 理由可信、可人工复核、防编造。
"""

import json
import re

import dashscope
from dashscope import MultiModalConversation

from backend.core.config import settings

dashscope.api_key = settings.dashscope_api_key

_JSON_RE = re.compile(r"\{.*\}", re.S)


def verify_checkin(
    image_b64: str,
    candidates: list[dict],
    scenic_name: str = "灵山胜境",
    image_format: str = "jpeg",
) -> dict:
    """闭集核验。candidates: [{"id","name","features"(可选 str)}]。

    返回 {"matched_id": str|None, "confidence": float(0~1), "evidence": list[str], "alt_id": str|None}。
    matched_id 一定是候选 id 之一或 None；非候选/解析失败一律归 None（不放过幻觉）。
    """
    ids = [c["id"] for c in candidates]
    lines = []
    for i, c in enumerate(candidates, 1):
        feat = c.get("features") or "（暂无特征描述，按名称判断）"
        lines.append(f'{i}. [id={c["id"]}] {c["name"]}：{feat}')
    cand_block = "\n".join(lines)

    system = (
        f"你在{scenic_name}，要核验游客拍的这张照片是不是某个景点。下面是候选景点及其标志性视觉特征：\n"
        f"{cand_block}\n\n"
        f"请判断照片里是哪一个候选景点——只能从上面候选的 id 里选，或 none。\n"
        f"严格只输出一段 JSON（不要 markdown、不要任何多余文字）：\n"
        f'{{"matched_id":"<候选id或none>","confidence":<0到1的小数>,'
        f'"evidence":["照片里真实看到、支撑该判断的具体特征"],"alt_id":"<次可能候选id或none>"}}\n'
        f"要求：matched_id 必须是 {ids} 之一或 none；confidence 是你对 matched_id 的把握；"
        f"evidence 必须是照片里**真实可见**的特征，不许编造、不许照抄上面的描述；"
        f"若照片明显不是任何候选景点（随手拍的人/食物/天空/别处地标/看不清），matched_id 给 none、confidence 给低值。"
    )
    image_url = f"data:image/{image_format};base64,{image_b64}"
    messages = [
        {"role": "system", "content": [{"text": system}]},
        {"role": "user", "content": [{"image": image_url}, {"text": "请核验，并只输出 JSON。"}]},
    ]
    resp = MultiModalConversation.call(model=settings.vl_model, messages=messages)
    if resp.status_code != 200 or resp.output is None:
        raise RuntimeError(f"DashScope 多模态调用失败 [{resp.status_code} {resp.code}]: {resp.message}")

    raw = resp.output.choices[0].message.content[0]["text"]
    return _parse(raw, ids)


def _parse(raw: str, ids: list[str]) -> dict:
    empty = {"matched_id": None, "confidence": 0.0, "evidence": [], "alt_id": None}
    m = _JSON_RE.search(raw or "")
    if not m:
        return empty
    try:
        data = json.loads(m.group(0))
    except Exception:
        return empty

    mid = data.get("matched_id")
    if mid in ("none", "None", "", None) or mid not in ids:
        mid = None
    alt = data.get("alt_id")
    if alt not in ids:
        alt = None
    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    ev = data.get("evidence") or []
    if isinstance(ev, str):
        ev = [ev]
    ev = [str(x).strip() for x in ev if str(x).strip()][:5]
    return {"matched_id": mid, "confidence": conf, "evidence": ev, "alt_id": alt}
