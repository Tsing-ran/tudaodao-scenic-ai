"""扫码接力 / 同游：把一台设备上的「对话 + 个性化画像」打成短时快照，
另一台设备扫码即接着逛——大屏→手机（带走导览）、手机→手机（家人同游）双向通用。

设计要点（详见 API_DOC「扫码接力」节）：
- create 由源端提供它已渲染的对话 + 画像快照；也可只给 source_session_id，由服务端
  从 conversations 表回读历史（源端不便序列化时的兜底）。
- 快照本体不进 URL，只发不透明 token；TTL 默认 5min、过期即焚（save_handoff 惰性 GC）。
- 二维码由 /handoff/qr.png?data=<完整claim_url> 渲染：源端用自己的 origin 拼 claim_url，
  服务端不必知道公网地址，跨网关/局域网都正确。
"""
import io
import json
import secrets

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from backend.db.database import claim_handoff, get_db, save_handoff

router = APIRouter(prefix="/handoff", tags=["handoff"])

_MAX_MSGS = 40  # 接力只带最近 N 轮，够续上下文、不让快照膨胀


class HandoffMsg(BaseModel):
    role: str = "user"          # user | assistant
    text: str = ""
    emotion: str | None = None
    intent: str | None = None


class CreateReq(BaseModel):
    scenic_id: str = "lingshan"
    group_type: str = "adult"
    lang: str = "zh"
    interests: list[str] = []
    avatar_id: str | None = None
    voice_id: str | None = None
    messages: list[HandoffMsg] = []
    trace: dict | None = None            # 足迹/明信片状态（手机→手机时携带，可空）
    source_session_id: str | None = None  # 源会话 id：messages 为空时由服务端回读历史
    poi: str | None = None               # 深链接：接力后定位到某景点
    source: str = "kiosk"                # kiosk | phone
    situation: dict | None = None        # 自身情况标签 5 维（手机→手机时携带，可空）
    ttl: int = 300


class ClaimReq(BaseModel):
    token: str
    session_id: str = ""   # 领取方自己的业务会话 id；用于把源画像复制过来（换设备"还认识你"）


def _read_profile_summary(session_id: str | None) -> str:
    """源会话的一句话游中画像（无则空串）。用于接力后展示"还认识你"。"""
    if not session_id:
        return ""
    try:
        from backend.agent.profiler import profile_brief
        return profile_brief(session_id)
    except Exception:
        return ""


def _read_history(session_id: str, scenic_id: str) -> list[dict]:
    """从 conversations 表回读某会话历史，拼成接力 messages（含拍照定位标记的原文）。"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_message, ai_reply, emotion FROM conversations "
            "WHERE session_id=? AND scenic_id=? ORDER BY created_at LIMIT ?",
            (session_id, scenic_id, _MAX_MSGS),
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        if r["user_message"]:
            out.append({"role": "user", "text": r["user_message"]})
        if r["ai_reply"]:
            out.append({"role": "assistant", "text": r["ai_reply"], "emotion": r["emotion"]})
    return out


@router.post("/create")
def create(req: CreateReq):
    """生成一条接力快照，返回 token + claim 相对路径 + 有效期。"""
    msgs = [
        {"role": m.role, "text": m.text, "emotion": m.emotion, "intent": m.intent}
        for m in req.messages
        if (m.text or "").strip()
    ][-_MAX_MSGS:]
    # 源端没给对话但给了源会话 id → 服务端回读（权威兜底）
    if not msgs and req.source_session_id:
        msgs = _read_history(req.source_session_id, req.scenic_id)

    snapshot = {
        "scenic_id": req.scenic_id,
        "group_type": req.group_type,
        "lang": req.lang,
        "interests": req.interests,
        "avatar_id": req.avatar_id,
        "voice_id": req.voice_id,
        "messages": msgs,
        "trace": req.trace,
        "poi": req.poi,
        "source": req.source,
        # 游中画像接力：记源会话 id（claim 时按它把画像复制到领取方）+ 一句话画像（前端可显示"还认识你"）
        "source_session_id": req.source_session_id,
        "profile_summary": _read_profile_summary(req.source_session_id),
    }
    # 自身情况标签平铺进快照顶层（claim 平铺返回 → 前端 importHandoff 按 snap.<dim> 注水）；仅带有值的维度
    for k in ("age", "pace", "mobility", "purpose", "first_time"):
        v = (req.situation or {}).get(k)
        if v:
            snapshot[k] = v
    token = secrets.token_urlsafe(8)
    ttl = max(30, min(int(req.ttl or 300), 1800))
    save_handoff(token, req.scenic_id, snapshot, source=req.source, ttl_seconds=ttl)
    return {
        "ok": True,
        "token": token,
        "expires_in": ttl,
        "claim_path": f"/?h={token}",     # 源端用 origin + claim_path 拼完整 URL 给二维码
        "msg_count": len(msgs),
    }


@router.post("/claim")
def claim(req: ClaimReq):
    """凭 token 取回快照（领取后标记 claimed，TTL 内可重复领取以容忍扫码重试）。"""
    res = claim_handoff(req.token)
    if res is None:
        return JSONResponse({"ok": False, "reason": "not_found"}, status_code=404)
    if res.get("expired"):
        return JSONResponse({"ok": False, "reason": "expired"}, status_code=410)
    if res.get("claimed"):
        return JSONResponse({"ok": False, "reason": "claimed"}, status_code=409)
    snap = res["snapshot"]
    # 游中画像接力：把源会话画像复制到领取方会话（换设备继续"懂他"）；失败静默不影响接力
    _copy_profile(snap.get("source_session_id"), req.session_id)
    return {"ok": True, **snap}


def _copy_profile(src: str | None, dst: str) -> None:
    """把 src 画像并入 dst（UPSERT 合并 interests/asked_pois，不覆盖 dst 既有）。全静默。"""
    try:
        from backend.agent.profiler import _SKIP_SESSIONS, _loads, _union
        if not src or not dst or dst in _SKIP_SESSIONS or src == dst:
            return
        with get_db() as conn:
            s = conn.execute(
                "SELECT scenic_id, interests, visited, asked_pois, intent_stats, traits, summary, turn_count "
                "FROM visitor_profile WHERE session_id=?", (src,),
            ).fetchone()
            if not s:
                return
            d = conn.execute(
                "SELECT interests, visited, asked_pois FROM visitor_profile WHERE session_id=?", (dst,),
            ).fetchone()
            if d:
                interests = _union(_loads(d["interests"], []), _loads(s["interests"], []))
                visited = _union(_loads(d["visited"], []), _loads(s["visited"], []))
                asked = _union(_loads(d["asked_pois"], []), _loads(s["asked_pois"], []))
                conn.execute(
                    "UPDATE visitor_profile SET interests=?, visited=?, asked_pois=?, "
                    "summary=CASE WHEN summary='' THEN ? ELSE summary END, "
                    "traits=?, updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE session_id=?",
                    (json.dumps(interests, ensure_ascii=False), json.dumps(visited, ensure_ascii=False),
                     json.dumps(asked, ensure_ascii=False), s["summary"] or "", s["traits"], dst),
                )
            else:
                conn.execute(
                    "INSERT INTO visitor_profile "
                    "(session_id, scenic_id, interests, visited, asked_pois, intent_stats, traits, summary, turn_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (dst, s["scenic_id"], s["interests"], s["visited"], s["asked_pois"],
                     s["intent_stats"], s["traits"], s["summary"] or "", s["turn_count"] or 0),
                )
    except Exception:
        pass


@router.get("/qr.png")
def qr_png(data: str = Query(..., description="二维码承载的完整文本（通常是 claim_url）")):
    """把任意文本渲染成二维码 PNG（纯 Python segno，0 系统依赖）。
    源端传它自己 origin 拼好的 claim_url → 跨公网网关/局域网都扫得通。"""
    import segno
    qr = segno.make(data, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=9, border=2, dark="#1b1b2f", light="#ffffff")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )
