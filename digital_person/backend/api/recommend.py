"""个性化推荐接口：游客端「为你定制」首页推荐区的后端。

把后台已有的个性化信号（同行人 group_type × 兴趣 interests × 此刻时间天气客流）
组装成**主动**的结构化推荐卡——每张带「为什么推荐你」理由 + 依据标签。
推荐**只落到本景区真实景点/活动/设施**（喂给 LLM 的候选来自 tour.TOURS / FACILITIES），
讲解事实仍由游客点开后的 RAG 链路约束 → 不幻觉。

两端共用：本接口产出游客端体验；游客点了哪些卡经埋点回流 → 管理端大屏「推荐效果」。
"""

import json
import re
import time

from fastapi import APIRouter
from pydantic import BaseModel

from backend.llm.client import chat
from backend.rag.pipeline import get_scenic_config, _situation_dict, _situation_key
from backend.agent.profiler import profile_brief, profile_digest
from backend.api.tour import TOURS, FACILITIES
from backend.analytics.env_context import env_brief
from backend.analytics.crowd import crowd_brief
from backend.rag.scenic_types import type_reco_guideline

router = APIRouter(prefix="/recommend", tags=["recommend"])

_GROUP = {"adult": "独自/朋友出游", "family_kids": "亲子家庭（带孩子）", "senior": "老年长辈", "couple": "情侣出游"}
_INTEREST = {"history": "历史人文", "nature": "自然风光", "photo": "拍照打卡", "food": "特色美食", "culture": "禅意文化"}
# 自身情况标签 → 人话短语（仅非默认值入推荐 prompt / basis）
_SIT_LABELS = {
    "age": {"teen": "青少年", "middle": "中年", "elder": "长辈"},
    "pace": {"half": "半天精华", "deep": "深度慢游"},
    "mobility": {"stroller": "推婴儿车", "wheelchair": "需无障碍", "hiker": "爱徒步"},
    "purpose": {"photo": "拍照打卡", "kids_fun": "遛娃", "pray": "祈福参拜", "study": "研学"},
    "first_time": {"return": "故地重游"},
}
_SIT_DIMS = ("age", "pace", "mobility", "purpose", "first_time")


def _sit_labels(situation: dict | None) -> list[str]:
    """非默认自身情况 → 人话标签列表（顺序固定）。全默认/None → []。"""
    if not situation:
        return []
    return [lbl for d in _SIT_DIMS if (lbl := _SIT_LABELS.get(d, {}).get(situation.get(d)))]
_FACILITY_LABEL = {"toilet": "卫生间", "food": "餐饮", "rest": "休息点", "medical": "医务点", "baby": "母婴室", "accessible": "无障碍设施"}

_JSON_ARR = re.compile(r"\[.*\]", re.S)
_cache: dict[tuple, tuple[float, list]] = {}   # key -> (ts, cards)
_TTL = 20 * 60


class RecoRequest(BaseModel):
    scenic_id: str = "lingshan"
    group_type: str = "adult"
    interests: list[str] = []
    lang: str = "zh"
    situation: dict | None = None   # 自身情况标签（age/pace/mobility/purpose/first_time）
    session_id: str = ""            # 游中画像来源；空=无画像个性化（向后兼容）


class RecoCard(BaseModel):
    icon: str = "star"            # theater/photo/food/walk/temple/rest/star，前端映射图标
    title: str
    reason: str                   # 一句「为什么推荐你」
    basis: list[str] = []         # 依据标签（亲子/历史/傍晚/人少）
    action: str = "ask"           # ask（问导游）/ route（开跟我游）/ facility（开设施）
    query: str | None = None      # action=ask 时携带的问题


class RecoResponse(BaseModel):
    cards: list[RecoCard]
    basis: list[str] = []         # 整体依据（画像 + 此刻）


def _real_spots(scenic_id: str) -> list[str]:
    out: list[str] = []
    for route in TOURS.get(scenic_id, []):
        for st in route["stations"]:
            line = st["name"] + (f"（{st['hint']}）" if st.get("hint") else "")
            if st["name"] not in [o.split("（")[0] for o in out]:
                out.append(line)
    return out[:14]


def _facilities(scenic_id: str) -> list[str]:
    fac = FACILITIES.get(scenic_id, {})
    return [_FACILITY_LABEL.get(k, k) for k in fac.keys()]


def _generate(scenic_id: str, group_type: str, interests: list[str], situation: dict | None = None,
              profile_ctx: str = "") -> list[dict]:
    cfg = get_scenic_config(scenic_id)
    guide = cfg.get("guide_name") or cfg.get("name") or "导游"
    group_label = _GROUP.get(group_type, "游客")
    interest_labels = [_INTEREST.get(i, i) for i in interests]
    sit_labels = _sit_labels(situation)
    spots = _real_spots(scenic_id)
    facs = _facilities(scenic_id)
    env = env_brief(scenic_id) or ""
    crowd = crowd_brief(scenic_id) or ""
    reco_guide = type_reco_guideline(scenic_id)  # 景区类型推荐准则（禅意慢行/博物精选/体力分配…）
    reco_line = f"\n本景区类型偏好：{reco_guide}" if reco_guide else ""

    system = (
        f"你是{cfg.get('name','本景区')}的金牌导游{guide}。任务：为一位游客在首页主动挑 3 张最贴合的推荐卡，"
        f"像真人导游一样'懂他'。务必结合：同行人、兴趣、自身情况、此刻时间/天气/客流。{reco_line}\n"
        f"硬规则：①只推荐下面列出的**真实景点/活动/设施**，不许编造；②每张要有一句具体的'为什么推荐你'（第二人称'你'，≤28字）；"
        f"③basis 给 2~3 个依据短标签（如 亲子/历史/傍晚/人少/避晒）；④action 取 ask/route/facility 之一，"
        f"ask 时 query 写一句游客可直接问导游的话；⑤icon 从 theater/photo/food/walk/temple/rest/star 里选最贴切的。\n"
        f"严格只输出一个 JSON 数组，无任何多余文字：\n"
        f'[{{"icon":"...","title":"≤12字","reason":"...","basis":["..."],"action":"ask","query":"..."}}]'
    )
    profile_line = (
        f"游中动态画像（他今天在这问过/流露的）：{profile_ctx}"
        "（**若含'未了心愿'（他明确提过想做/想看还没实现的），优先安排一张卡兑现它**，"
        "如'您上午提过想看九龙灌浴'；含'问过素斋'等兴趣线索时至少一张卡自然呼应，"
        "如'记得您想尝素斋'；已问过/已到访的点位不必再重点推荐）。\n"
        if profile_ctx else ""
    )
    user = (
        f"游客画像：同行人={group_label}；兴趣={('、'.join(interest_labels)) or '未指定'}；"
        f"自身情况={('、'.join(sit_labels)) or '常规'}。\n"
        f"{profile_line}"
        f"此刻：{env}　{crowd}\n"
        f"本景区真实景点/活动：{'；'.join(spots)}\n"
        f"可用设施：{('、'.join(facs)) or '无'}\n"
        f"请给 3 张推荐卡（JSON 数组）。"
    )
    raw = chat(system_prompt=system, history=[], user_message=user, fast=False)
    m = _JSON_ARR.search(raw or "")
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    cards = []
    for c in arr[:4]:
        if not isinstance(c, dict) or not c.get("title"):
            continue
        act = c.get("action") if c.get("action") in ("ask", "route", "facility") else "ask"
        cards.append({
            "icon": str(c.get("icon", "star"))[:16],
            "title": str(c["title"])[:18],
            "reason": str(c.get("reason", ""))[:40],
            "basis": [str(b)[:8] for b in (c.get("basis") or [])][:3],
            "action": act,
            "query": (str(c.get("query"))[:60] if c.get("query") else None),
        })
    return cards


@router.post("", response_model=RecoResponse)
@router.post("/", response_model=RecoResponse)
async def recommend(req: RecoRequest) -> RecoResponse:
    interests = [i for i in req.interests if isinstance(i, str)][:6]
    sit = _situation_dict(req.situation)
    sit_key = _situation_key(sit)   # 非默认情境进缓存键，避免不同情境串卡；全默认→""不改键
    profile_ctx = profile_brief(req.session_id)  # 游中画像；空=无个性化，键与旧状一致
    prof_key = profile_digest(req.session_id)
    bucket = int(time.time() // _TTL)
    key = (req.scenic_id, req.group_type, tuple(sorted(interests)), sit_key, prof_key, bucket)
    cached = _cache.get(key)
    if cached and cached[0] == bucket:
        cards = cached[1]
    else:
        try:
            cards = _generate(req.scenic_id, req.group_type, interests, sit, profile_ctx)
        except Exception:
            cards = []
        if cards:
            _cache[key] = (bucket, cards)

    # 整体依据（画像 + 自身情况 + 此刻），给前端「为你定制」标题旁的依据 chip
    basis = []
    if req.group_type in _GROUP:
        basis.append(_GROUP[req.group_type].split("（")[0])
    basis += [_INTEREST[i] for i in interests if i in _INTEREST][:2]
    basis += _sit_labels(sit)[:2]

    return RecoResponse(cards=[RecoCard(**c) for c in cards], basis=basis)
