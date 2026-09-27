"""
数字人形象「艺名 + 欢迎语 + 按景区发布」· API roundtrip 测试。

运行：cd E:\\Digital_Person && .venv/bin/python tests/test_dh_avatar_meta.py
     （服务器：cd /root/autodl-tmp/Digital_Person && .venv/bin/python tests/test_dh_avatar_meta.py）
覆盖：presets 无参全量兼容 / visitor 景区过滤（本景区专属可见·他景区专属隐藏·legacy/coming_soon 隐藏）/
     publish 开关强制显隐 / stage_name_override 按景区覆盖 / avatar-meta 艺名 roundtrip /
     非法艺名与非法 avatar_id 400 / config 附 stage_name。
仅挂载 digital-human 路由；用真实 SQLite，测试行用 test_meta_* 前缀清理（meta 全局按 avatar_id 清）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.digital_human import router
from backend.db.database import get_db, init_db

TEST_SCENIC = "test_meta_scenic"
META_AVATARS = ("F5_ethnic", "F6_mature", "F2_hanfu")  # 测试会改这些的 meta，跑完清掉

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
        conn.execute("DELETE FROM dh_avatar_publish WHERE scenic_id LIKE 'test_meta%'")
        qs = ",".join("?" * len(META_AVATARS))
        conn.execute(f"DELETE FROM dh_avatar_meta WHERE avatar_id IN ({qs})", META_AVATARS)


cleanup()


def ids(resp_json):
    return {a["id"] for a in resp_json["avatars"]}


# 1) 无参 presets = 全量（向后兼容），每项带增量字段 stage_name/welcome_text
r = client.get("/digital-human/presets").json()
allids = ids(r)
check("无参 presets 含 dh_lingshan 与 dh_gugong（全量）",
      "dh_lingshan" in allids and "dh_gugong" in allids, str(sorted(allids)))
check("无参 presets 含 legacy 占位（全量行为不变）", "female_elegant" in allids)
check("每项形象带 stage_name", all("stage_name" in a for a in r["avatars"]))
check("每项形象带 welcome_text", all("welcome_text" in a for a in r["avatars"]))
check("dh_lingshan 默认艺名=云岫",
      next(a["stage_name"] for a in r["avatars"] if a["id"] == "dh_lingshan") == "云岫")

# 2) visitor + lingshan：本景区专属可见、他景区专属隐藏、legacy/coming_soon 隐藏
r = client.get("/digital-human/presets",
               params={"scenic_id": "lingshan", "audience": "visitor"}).json()
vis = ids(r)
check("visitor(lingshan) 含 dh_lingshan", "dh_lingshan" in vis, str(sorted(vis)))
check("visitor(lingshan) 不含 dh_gugong（他景区专属）", "dh_gugong" not in vis)
check("visitor(lingshan) 不含 legacy", "female_elegant" not in vis)
check("visitor(lingshan) 不含 coming_soon(outfit_qipao)", "outfit_qipao" not in vis)
check("visitor(lingshan) 含通用推荐(F1_modern)", "F1_modern" in vis)
check("visitor 首个是本景区专属(dh_lingshan 浮顶)",
      r["avatars"][0]["id"] == "dh_lingshan" if r["avatars"] else False,
      r["avatars"][0]["id"] if r["avatars"] else "empty")

# 3) admin + scenic：全量 + published 字段
r = client.get("/digital-human/presets",
               params={"scenic_id": "lingshan", "audience": "admin"}).json()
by = {a["id"]: a for a in r["avatars"]}
check("admin 视角 dh_gugong 存在但 published=False",
      "dh_gugong" in by and by["dh_gugong"]["published"] is False)
check("admin 视角 dh_lingshan published=True",
      by.get("dh_lingshan", {}).get("published") is True)

# 4) publish 开关：test 景区默认隐藏他景区专属 dh_gugong → enabled=true 后可见
r = client.get("/digital-human/presets",
               params={"scenic_id": TEST_SCENIC, "audience": "visitor"}).json()
check(f"visitor({TEST_SCENIC}) 默认不含 dh_gugong", "dh_gugong" not in ids(r))
r = client.put("/digital-human/avatar-publish",
               json={"scenic_id": TEST_SCENIC, "avatar_id": "dh_gugong", "enabled": True})
check("publish dh_gugong enabled=true 成功", r.status_code == 200, r.text)
r = client.get("/digital-human/presets",
               params={"scenic_id": TEST_SCENIC, "audience": "visitor"}).json()
check("publish 后 visitor 含 dh_gugong", "dh_gugong" in ids(r))

# 5) publish enabled=false 强制隐藏一个通用推荐形象
r = client.put("/digital-human/avatar-publish",
               json={"scenic_id": TEST_SCENIC, "avatar_id": "F1_modern", "enabled": False})
check("publish F1_modern enabled=false 成功", r.status_code == 200, r.text)
r = client.get("/digital-human/presets",
               params={"scenic_id": TEST_SCENIC, "audience": "visitor"}).json()
check("enabled=false 后 visitor 不含 F1_modern", "F1_modern" not in ids(r))

# 6) stage_name_override 按景区覆盖，仅作用该景区
r = client.put("/digital-human/avatar-publish",
               json={"scenic_id": TEST_SCENIC, "avatar_id": "F2_hanfu",
                     "enabled": True, "stage_name_override": "测试艺名"})
check("publish F2_hanfu 带 override 成功", r.status_code == 200, r.text)
r = client.get("/digital-human/presets",
               params={"scenic_id": TEST_SCENIC, "audience": "visitor"}).json()
f2 = next((a for a in r["avatars"] if a["id"] == "F2_hanfu"), {})
check(f"visitor({TEST_SCENIC}) F2_hanfu 艺名=测试艺名", f2.get("stage_name") == "测试艺名", str(f2))
r = client.get("/digital-human/presets",
               params={"scenic_id": "lingshan", "audience": "admin"}).json()
f2l = next((a for a in r["avatars"] if a["id"] == "F2_hanfu"), {})
check("lingshan 景区 F2_hanfu 不受 override 影响(=默认绾云)", f2l.get("stage_name") == "绾云", str(f2l))

# 7) avatar-meta 艺名 roundtrip（全局）
r = client.put("/digital-human/avatar-meta",
               json={"avatar_id": "F5_ethnic", "stage_name": "澜心", "welcome_text": "欢迎光临"})
check("PUT avatar-meta 成功", r.status_code == 200, r.text)
r = client.get("/digital-human/presets").json()
f5 = next((a for a in r["avatars"] if a["id"] == "F5_ethnic"), {})
check("全局艺名生效(F5_ethnic=澜心)", f5.get("stage_name") == "澜心", str(f5))
check("全局欢迎语生效", f5.get("welcome_text") == "欢迎光临")
r = client.get("/digital-human/avatar-meta", params={"scenic_id": "lingshan"}).json()
f5m = next((x for x in r if x["avatar_id"] == "F5_ethnic"), {})
check("avatar-meta 列表 source=db", f5m.get("source") == "db", str(f5m))

# 8) 只改欢迎语（不传艺名）不丢已有艺名
r = client.put("/digital-human/avatar-meta",
               json={"avatar_id": "F5_ethnic", "welcome_text": "再次欢迎"})
check("只改欢迎语成功", r.status_code == 200, r.text)
r = client.get("/digital-human/presets").json()
f5 = next((a for a in r["avatars"] if a["id"] == "F5_ethnic"), {})
check("艺名保留(仍=澜心)", f5.get("stage_name") == "澜心", str(f5))
check("欢迎语更新(=再次欢迎)", f5.get("welcome_text") == "再次欢迎")

# 9) 非法输入 400
r = client.put("/digital-human/avatar-meta",
               json={"avatar_id": "F6_mature", "stage_name": "一二三四五六七八九"})  # 9 字
check("超长艺名(9字) 返回 400", r.status_code == 400, f"got {r.status_code}")
r = client.put("/digital-human/avatar-meta",
               json={"avatar_id": "F6_mature", "stage_name": "   "})  # 纯空白
check("纯空白艺名 返回 400", r.status_code == 400, f"got {r.status_code}")
r = client.put("/digital-human/avatar-meta",
               json={"avatar_id": "no_such_avatar", "stage_name": "谁"})
check("非法 avatar_id 返回 400", r.status_code == 400, f"got {r.status_code}")

# 10) config 附 stage_name
r = client.get("/digital-human/config", params={"scenic_id": "lingshan"}).json()
check("config 含 stage_name", bool(r.get("stage_name")), str(r))

cleanup()
print(f"\n结果：{passed} 通过 / {failed} 失败")
sys.exit(1 if failed else 0)
