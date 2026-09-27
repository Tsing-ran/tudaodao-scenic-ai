"""拍照打卡核验接口：闭集 VL + 位置软门 + 融合决策 + 可信理由。

设计见记忆 route-map-feature。核心=不做开放识别，只在路线候选里闭集核对：
  ① 闭集 VL（backend/llm/checkin.verify_checkin）判别 + 结构化 evidence；
  ② 位置软门：若带 GPS（AMap 定位，GCJ-02，与景点坐标同基准），算到 matched 的距离做独立佐证，
     近则加信、远则减信；不带 GPS 则纯靠视觉+路线（演示/室内友好，不硬依赖定位）；
  ③ 融合置信 + 决策：confirmed / wrong_stop（认出的是别的站→建议调序）/ uncertain（再拍）；
  ④ 理由可信：点名具体特征 + 位置佐证 + 路线位置（绝不"我觉得"）。
"""

import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.checkin import verify_checkin
from backend.rag.pipeline import get_scenic_config

router = APIRouter(prefix="/checkin", tags=["checkin"])

# 各景区景点的标志性视觉特征（闭集核验用，越具体越准、越可信）。键 = 景点 id。
_FEATURES: dict[str, dict[str, str]] = {
    "lingshan": {
        "menlou": "恢弘的山门牌楼，多重檐顶，悬挂「灵山胜境」匾额",
        "wuyin": "金色藏式坛城（曼陀罗）造型建筑，方形多门、金顶",
        "jiulong": "巨大的莲花喷泉广场，中央一朵会开合的青铜大莲花，九条龙环绕喷水",
        "ayuwang": "一根高大独立的石柱，柱顶有狮子与法轮雕刻",
        "xiangfu": "传统汉传佛教寺院，黄墙、飞檐、背倚青山",
        "dafo": "一尊巨大的青铜立佛（约88米），右手施无畏印、左手与愿印，立于莲花座之上",
        "fangong": "宏伟的宫殿式建筑群，琉璃顶，内部有华丽的穹顶与壁画",
    },
}


class Cand(BaseModel):
    id: str
    name: str
    lng: float | None = None
    lat: float | None = None


class CheckinRequest(BaseModel):
    scenic_id: str = "lingshan"
    image_b64: str
    image_format: str = "jpeg"
    target_id: str | None = None       # 游客想打卡的当前站（你在这）
    candidates: list[Cand] = []        # 路线候选站（带坐标用于位置佐证）
    gps: list[float] | None = None     # [lng, lat] GCJ-02（AMap 定位），可选；不传则纯视觉+路线


class CheckinResponse(BaseModel):
    decision: str                       # confirmed / wrong_stop / uncertain
    matched_id: str | None = None
    matched_name: str | None = None
    confidence: float = 0.0
    evidence: list[str] = []
    distance_m: float | None = None
    reason: str = ""
    alt_id: str | None = None


def _haversine(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _build_reason(decision, name, evidence, distance_m) -> str:
    ev = "、".join(evidence[:2]) if evidence else ""
    feat = f"——我认出了{ev}" if ev else ""
    near = f"，而且你就在它旁边约 {int(distance_m)} 米" if (distance_m is not None and distance_m <= 120) else ""
    if decision == "uncertain":
        if name:
            return f"这张照片有点像{name}，但我还不太有把握。能离近一点、把景点拍清楚些再来一张吗？"
        return "这张照片我没认出是路线上的景点，能对准眼前的景点再拍一张吗？"
    if decision == "wrong_stop":
        return f"这看起来是{name}{feat}{near}。你是先到了这一站吗？我帮你把路线顺序调一下。"
    return f"到啦，确认你在「{name}」{feat}{near}，打卡成功！"


@router.post("", response_model=CheckinResponse)
@router.post("/", response_model=CheckinResponse)
async def checkin_endpoint(req: CheckinRequest) -> CheckinResponse:
    if not req.image_b64:
        raise HTTPException(status_code=400, detail="image_b64 不能为空")
    if not req.candidates:
        raise HTTPException(status_code=400, detail="candidates 不能为空")

    cfg = get_scenic_config(req.scenic_id)
    feat_map = _FEATURES.get(req.scenic_id, {})
    cands = [{"id": c.id, "name": c.name, "features": feat_map.get(c.id)} for c in req.candidates]

    try:
        vl = verify_checkin(req.image_b64, cands, scenic_name=cfg["name"], image_format=req.image_format)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"核验失败: {e}")

    mid, conf, evidence = vl["matched_id"], vl["confidence"], vl["evidence"]
    by_id = {c.id: c for c in req.candidates}
    matched_name = by_id[mid].name if mid in by_id else None

    # 位置软门：GPS 到 matched 的距离作独立证据，近加信 / 远减信（不带 GPS 则跳过）
    distance_m = None
    if mid and req.gps and len(req.gps) == 2 and mid in by_id and by_id[mid].lng is not None:
        c = by_id[mid]
        distance_m = round(_haversine(req.gps[0], req.gps[1], c.lng, c.lat), 1)
        if distance_m <= 80:
            conf = min(1.0, conf + 0.15)
        elif distance_m >= 300:
            conf = max(0.0, conf - 0.35)
    conf = round(conf, 2)

    # 决策：有近距佐证可放宽阈值
    thresh = 0.6 if (distance_m is not None and distance_m <= 120) else 0.7
    if not mid or conf < thresh:
        decision = "uncertain"
    elif req.target_id and mid != req.target_id:
        decision = "wrong_stop"
    else:
        decision = "confirmed"

    reason = _build_reason(decision, matched_name, evidence, distance_m)
    return CheckinResponse(
        decision=decision, matched_id=mid, matched_name=matched_name,
        confidence=conf, evidence=evidence, distance_m=distance_m,
        reason=reason, alt_id=vl["alt_id"],
    )
