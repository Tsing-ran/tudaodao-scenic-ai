"""扫码接力 roundtrip：create → claim → 校验快照；qr.png；源会话回读；错误码。

跑法：.venv/bin/python tests/test_handoff.py
不依赖 GPU / RAG，只打 handoff 路由 + SQLite。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DEPLOY_MODE", "cloud")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.db.database import get_db, init_db, save_handoff
from backend.api.handoff import router

init_db()
app = FastAPI()
app.include_router(router)
c = TestClient(app)

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✓ {name}")
    else:
        _failed += 1
        print(f"  ✗ {name}")


print("[1] create 带对话+画像 → claim 还原")
payload = {
    "scenic_id": "lingshan", "group_type": "family_kids", "lang": "zh",
    "interests": ["history", "photo"], "voice_id": "voice_x", "avatar_id": "av_x",
    "messages": [
        {"role": "user", "text": "灵山大佛有多高"},
        {"role": "assistant", "text": "灵山大佛高88米。", "emotion": "happy", "intent": "qa"},
        {"role": "user", "text": ""},  # 空文本应被过滤
    ],
    "trace": {"visited": ["大佛广场"]},
    "poi": "dafo", "source": "phone",
}
r = c.post("/handoff/create", json=payload)
check("create 200", r.status_code == 200)
d = r.json()
check("create ok", d.get("ok") is True)
check("有 token", bool(d.get("token")))
check("claim_path 形如 /?h=token", d.get("claim_path") == f"/?h={d.get('token')}")
check("空文本被过滤 msg_count=2", d.get("msg_count") == 2)
token = d["token"]

r2 = c.post("/handoff/claim", json={"token": token})
check("claim 200", r2.status_code == 200)
s = r2.json()
check("claim ok", s.get("ok") is True)
check("景区还原", s.get("scenic_id") == "lingshan")
check("同行人还原", s.get("group_type") == "family_kids")
check("兴趣还原", s.get("interests") == ["history", "photo"])
check("画像音色/形象还原", s.get("voice_id") == "voice_x" and s.get("avatar_id") == "av_x")
check("trace 还原", (s.get("trace") or {}).get("visited") == ["大佛广场"])
check("poi 深链接还原", s.get("poi") == "dafo")
check("对话 2 条且文本对", len(s.get("messages", [])) == 2
      and s["messages"][0]["text"] == "灵山大佛有多高"
      and s["messages"][1]["emotion"] == "happy")

print("[2] TTL 内可重复 claim（容忍扫码重试）")
r3 = c.post("/handoff/claim", json={"token": token})
check("二次 claim 仍 200", r3.status_code == 200 and r3.json().get("ok") is True)

print("[3] 未知 token → 404")
r4 = c.post("/handoff/claim", json={"token": "nope-not-real"})
check("未知 token 404", r4.status_code == 404 and r4.json().get("reason") == "not_found")

print("[4] 过期 token → 410（直接写一条已过期行）")
save_handoff("expired_tok", "lingshan", {"scenic_id": "lingshan"}, ttl_seconds=-10)
r5 = c.post("/handoff/claim", json={"token": "expired_tok"})
check("过期 410", r5.status_code == 410 and r5.json().get("reason") == "expired")
# 过期行应被惰性删除
with get_db() as conn:
    gone = conn.execute("SELECT 1 FROM session_handoffs WHERE token='expired_tok'").fetchone()
check("过期行已 GC", gone is None)

print("[5] source_session_id 回读历史（源端未给 messages）")
with get_db() as conn:
    conn.execute(
        "INSERT INTO conversations (session_id, scenic_id, user_message, ai_reply, emotion) "
        "VALUES (?,?,?,?,?)",
        ("kiosk_sess_1", "xihu", "断桥在哪", "断桥在白堤东端。", "neutral"),
    )
r6 = c.post("/handoff/create", json={"scenic_id": "xihu", "source_session_id": "kiosk_sess_1"})
check("create 回读 200", r6.status_code == 200)
check("回读出 2 条 msg", r6.json().get("msg_count") == 2)
s6 = c.post("/handoff/claim", json={"token": r6.json()["token"]}).json()
check("回读内容正确", s6["messages"][0]["text"] == "断桥在哪"
      and s6["messages"][1]["text"] == "断桥在白堤东端。")

print("[6] qr.png 返回 PNG 图片")
r7 = c.get("/handoff/qr.png", params={"data": "https://example.com/?h=abc"})
check("qr 200", r7.status_code == 200)
check("qr 是 PNG", r7.headers.get("content-type") == "image/png"
      and r7.content[:8] == b"\x89PNG\r\n\x1a\n")

print(f"\n=== {_passed} passed, {_failed} failed ===")
sys.exit(1 if _failed else 0)
