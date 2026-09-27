"""
管理端 BI 分析接口 · roundtrip 测试。

运行：cd /home/jiale/Desktop/Digital_Person && .venv/bin/python tests/test_analytics_bi.py
覆盖：4 个数据端点 + scenics 清单的字段契约、数值合理性、scenic 过滤、managed_only 作用域、
     空景区优雅降级。只挂载 analytics_bi 路由（不拉起 RAG 全栈），数据源=合成 csv + 赛题 xlsx。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.analytics_bi import router

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


# ---- scenics 清单 ----
print("【scenics 清单】")
r = client.get("/analytics/bi/scenics").json()
check("返回 8 个景区", len(r.get("scenics", [])) == 8, str(len(r.get("scenics", []))))
check("每项含 scenic_id/name/samples",
      all({"scenic_id", "name", "samples"} <= set(s) for s in r["scenics"]))
check("灵山有样本", next(s["samples"] for s in r["scenics"] if s["scenic_id"] == "lingshan") > 0)

# ---- overview ----
print("【overview】")
ov = client.get("/analytics/bi/overview?scenic_id=lingshan").json()
check("含核心 KPI 字段",
      {"visitors", "avg_spend_per_capita", "total_revenue", "avg_satisfaction",
       "avg_stay_hours", "avg_group_size"} <= set(ov), str(ov.keys()))
check("游客数 > 0", ov["visitors"] > 0, str(ov["visitors"]))
check("满意度在 1-5", 1 <= ov["avg_satisfaction"] <= 5, str(ov["avg_satisfaction"]))
check("客单价合理(>0)", ov["avg_spend_per_capita"] > 0, str(ov["avg_spend_per_capita"]))
ov_all = client.get("/analytics/bi/overview?scenic_id=all").json()
check("all 作用域游客数 ≥ 单景区", ov_all["visitors"] >= ov["visitors"],
      f"{ov_all['visitors']} vs {ov['visitors']}")
ov_empty = client.get("/analytics/bi/overview?scenic_id=__nope__").json()
check("未知景区优雅降级 visitors=0", ov_empty.get("visitors") == 0, str(ov_empty))

# ---- spending ----
print("【spending】")
sp = client.get("/analytics/bi/spending?scenic_id=lingshan").json()
check("含 structure/histogram", {"structure", "histogram"} <= set(sp))
check("消费 5 类", len(sp["structure"]) == 5, str(len(sp["structure"])))
check("占比之和≈1", abs(sum(c["ratio"] for c in sp["structure"]) - 1) < 0.02,
      str(sum(c["ratio"] for c in sp["structure"])))
check("直方图分桶非空", len(sp["histogram"]) > 0)

# ---- demographics ----
print("【demographics】")
dm = client.get("/analytics/bi/demographics?scenic_id=lingshan").json()
check("含 age/gender/group_size", {"age", "gender", "group_size"} <= set(dm))
check("年龄分 7 段", len(dm["age"]) == 7, str(len(dm["age"])))
check("性别分布非空", len(dm["gender"]) > 0)
age_total = sum(a["count"] for a in dm["age"])
check("年龄总数≈游客数", abs(age_total - ov["visitors"]) <= ov["visitors"] * 0.02,
      f"{age_total} vs {ov['visitors']}")

# ---- attractions ----
print("【attractions】")
at = client.get("/analytics/bi/attractions?limit=8").json()
check("含 ranking/by_type", {"ranking", "by_type"} <= set(at))
check("排名按访问量降序",
      all(at["ranking"][i]["visitors"] >= at["ranking"][i + 1]["visitors"]
          for i in range(len(at["ranking"]) - 1)))
mng = client.get("/analytics/bi/attractions?managed_only=true&limit=8").json()
managed_names = {"灵山胜境", "拈花湾", "西湖", "黄山", "故宫", "张家界", "兵马俑", "莫高窟"}
check("managed_only 仅含 8 景区",
      all(r["attraction"] in managed_names for r in mng["ranking"]),
      str([r["attraction"] for r in mng["ranking"]]))

print(f"\n{'='*40}\n通过 {passed} / {passed + failed}")
sys.exit(0 if failed == 0 else 1)
