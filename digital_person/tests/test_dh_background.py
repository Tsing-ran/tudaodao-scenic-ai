"""
数字人场景背景配置 · API roundtrip 测试。

运行：cd /home/jiale/Desktop/Digital_Person && .venv/bin/python tests/test_dh_background.py
覆盖：presets 含 backgrounds / PUT-GET roundtrip / 旧 payload 兼容 / 非法 background_id 400 /
     未配置景区回落 / 上传登记→pending→ready 流转。
仅挂载 digital-human 路由（不拉起 RAG 全栈）；用真实 SQLite，测试行用 test_bg_* 前缀并清理。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.digital_human import router
from backend.db.database import get_db, init_db

SCENIC = "test_bg_scenic"

init_db()
app = FastAPI()
app.include_router(router)
client = TestClient(app)

passed = failed = 0


def check(name: str, cond: bool, detail: str = ""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {detail}")


def cleanup():
    with get_db() as conn:
        conn.execute("DELETE FROM digital_human_config WHERE scenic_id LIKE 'test_bg_%'")
        conn.execute("DELETE FROM dh_background WHERE name LIKE 'test_bg_%'")


cleanup()

# 1) presets 含 backgrounds
r = client.get("/digital-human/presets").json()
check("presets 含 backgrounds 列表", isinstance(r.get("backgrounds"), list) and
      any(b["id"] == "bg_lingshan" for b in r["backgrounds"]))

# 2) PUT 带 background → GET 一致
body = {"scenic_id": SCENIC, "avatar_id": "female_sweet", "avatar_name": "甜美波波头",
        "voice_id": "voice_gentle_f", "voice_name": "知性温柔",
        "background_id": "bg_lingshan", "background_name": "灵山·禅意佛境"}
r = client.put("/digital-human/config", json=body)
check("PUT 带 background_id 成功", r.status_code == 200, r.text)
r = client.get("/digital-human/config", params={"scenic_id": SCENIC}).json()
check("GET 返回 background_id", r.get("background_id") == "bg_lingshan", str(r))
check("GET 返回 background_name", r.get("background_name") == "灵山·禅意佛境")

# 3) 旧 payload（不带 background 字段）仍兼容，且会清掉旧背景（excluded 语义）
legacy = {k: v for k, v in body.items() if not k.startswith("background")}
r = client.put("/digital-human/config", json=legacy)
check("旧 payload PUT 兼容", r.status_code == 200, r.text)
r = client.get("/digital-human/config", params={"scenic_id": SCENIC}).json()
check("旧 payload 后 background 为空", r.get("background_id") == "")

# 4) 非法 background_id → 400
bad = {**body, "background_id": "bg_not_exist"}
r = client.put("/digital-human/config", json=bad)
check("非法 background_id 返回 400", r.status_code == 400, f"got {r.status_code}")

# 5) 未配置景区回落（fallback 路径带出 background 字段不报错）
r = client.get("/digital-human/config", params={"scenic_id": "test_bg_nonexist"}).json()
check("未配置景区回落含 background 字段", "background_id" in r and r.get("fallback") is True, str(r))

# 6) 上传登记 → pending → ready 流转
files = {"file": ("test_bg_demo.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 100), "image/png")}
r = client.post("/digital-human/background/upload", files=files,
                data={"name": "test_bg_自定义", "scenic_id": SCENIC})
check("上传登记成功", r.status_code == 200, r.text)
bg_id = r.json().get("bg_id", "")
r = client.get("/digital-human/background/pending").json()
check("pending 列表含新上传", any(x["bg_id"] == bg_id for x in r))
r = client.get(f"/digital-human/background/file/{bg_id}")
check("可下载原图", r.status_code == 200)
r = client.post(f"/digital-human/background/{bg_id}/ready")
check("置 ready 成功", r.status_code == 200, r.text)
r = client.put("/digital-human/config", json={**body, "background_id": bg_id,
                                              "background_name": "test_bg_自定义"})
check("ready 后可被 PUT 引用", r.status_code == 200, r.text)

cleanup()
print(f"\n结果：{passed} 通过 / {failed} 失败")
sys.exit(1 if failed else 0)
