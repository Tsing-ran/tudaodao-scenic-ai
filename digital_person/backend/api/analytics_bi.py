"""管理端「传统文旅 BI」分析接口（数据源=赛题行为数据 xlsx + 合成补充数据）。
与会话类 analytics（情感/热点/盲区/预警，数据源 SQLite）互补：本模块挖人口/消费/景点/满意度。
供队友数据大屏 ECharts 直接 fetch（CORS 已全开）。契约见 API_DOC.md「数据大屏 BI」节。
"""
from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import APIRouter

router = APIRouter(prefix="/analytics/bi", tags=["analytics-bi"])

_ROOT = Path(__file__).resolve().parents[2]
_PKG = _ROOT / "示范景区公开资料包"
_XLSX = _PKG / "景点景区旅游数据行为分析数据.xlsx"
_XLSX_PKL = _PKG / "behavior_data.pkl"   # 派生缓存：140k 行 xlsx 用 openpyxl 读要 ~24s，缓存后 <0.02s
_SYNTH = _PKG / "synthetic_behavior.csv"

# scenic_id → 行为数据里的景点名（与造数脚本/前端 SCENICS 一致）
SCENIC_NAME = {
    "lingshan": "灵山胜境", "nihuawan": "拈花湾", "xihu": "西湖", "huangshan": "黄山",
    "gugong": "故宫", "zhangjiajie": "张家界", "bingmayong": "兵马俑", "mogaoku": "莫高窟",
}
_COLS = ["age", "gender", "attraction_name", "attraction_type", "visit_date",
         "stay_duration", "ticket_cost", "food_cost", "shopping_cost",
         "transport_cost", "entertainment_cost", "total_cost", "group_size", "satisfaction"]


_NUMCOLS = ["age", "stay_duration", "ticket_cost", "food_cost", "shopping_cost",
            "transport_cost", "entertainment_cost", "total_cost", "group_size", "satisfaction"]


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    for c in _NUMCOLS:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _read_xlsx_raw() -> pd.DataFrame:
    """读赛题真实 xlsx。优先派生 pickle 缓存（新于 xlsx 时）：openpyxl 读 140k 行要 ~24s、
    且并发首调会各跑一次读挤爆线程池；pickle <0.02s 且首调即热，根治首次卡死/堆积。"""
    if _XLSX_PKL.exists() and (not _XLSX.exists() or _XLSX_PKL.stat().st_mtime >= _XLSX.stat().st_mtime):
        try:
            return pd.read_pickle(_XLSX_PKL)
        except Exception:
            pass
    if _XLSX.exists():
        try:
            df = pd.read_excel(_XLSX, usecols=lambda c: c in _COLS + ["attraction_name"])
            try:
                df.to_pickle(_XLSX_PKL)   # 落缓存，后续进程/重启即热
            except Exception:
                pass
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=_COLS)


@lru_cache(maxsize=1)
def _xlsx_only() -> pd.DataFrame:
    """仅赛题真实 xlsx（消费分析默认口径：可对评委证明「基于此资料」）。"""
    return _coerce(_read_xlsx_raw().copy())


@lru_cache(maxsize=1)
def _data() -> pd.DataFrame:
    """合并真实 xlsx + 合成数据，缓存。合成仅为大屏补量，消费分析走 _xlsx_only。"""
    frames = []
    if _SYNTH.exists():
        frames.append(pd.read_csv(_SYNTH))
    xdf = _read_xlsx_raw()
    if not xdf.empty:
        frames.append(xdf)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_COLS)
    return _coerce(df)


def _scope(scenic_id: str | None, days: int = 0, real_only: bool = False) -> pd.DataFrame:
    """按景区（+可选近 days 天）切片。days<=0 取全部。日期相对数据集内最新 visit_date。
    real_only=True 时只用赛题真实 xlsx（消费分析口径，不掺合成补量）。"""
    df = _xlsx_only() if real_only else _data()
    if scenic_id and scenic_id != "all":
        name = SCENIC_NAME.get(scenic_id, scenic_id)
        df = df[df["attraction_name"] == name]
    if days and days > 0 and "visit_date" in df.columns and not df.empty:
        dt = pd.to_datetime(df["visit_date"], errors="coerce")
        latest = dt.max()
        if pd.notna(latest):
            df = df[dt >= latest - pd.Timedelta(days=days - 1)]
    return df


@router.get("/overview")
def overview(scenic_id: str = "lingshan", days: int = 0, real_only: bool = False):
    """核心 KPI：游客数 / 客单价 / 总营收 / 平均满意度 / 平均停留 / 人均同行。
    days>0 仅统计近 N 天（1=今日 / 7=本周 / 30=本月，相对数据集最新日期）。
    real_only=True 仅用赛题真实 xlsx（消费分析口径）。"""
    d = _scope(scenic_id, days, real_only)
    if d.empty:
        return {"scenic_id": scenic_id, "visitors": 0}
    return {
        "scenic_id": scenic_id,
        "source": "赛题《景点景区旅游数据行为分析数据》" if real_only else "赛题数据+演示补充",
        "visitors": int(len(d)),
        "avg_spend_per_capita": round(float(d["total_cost"].mean()), 1),    # 客单价
        "total_revenue": round(float(d["total_cost"].sum()), 0),            # 总营收
        "avg_satisfaction": round(float(d["satisfaction"].mean()), 2),
        "avg_stay_hours": round(float(d["stay_duration"].mean()), 1),
        "avg_group_size": round(float(d["group_size"].mean()), 1),
    }


@router.get("/spending")
def spending(scenic_id: str = "lingshan", days: int = 0, real_only: bool = False):
    """消费结构（6 类均值+占比）+ 客单价分布直方。days>0 仅近 N 天。real_only=真实 xlsx 口径。"""
    d = _scope(scenic_id, days, real_only)
    if d.empty:
        return {"scenic_id": scenic_id, "structure": [], "histogram": []}
    cats = [("门票", "ticket_cost"), ("餐饮", "food_cost"), ("购物", "shopping_cost"),
            ("交通", "transport_cost"), ("娱乐", "entertainment_cost")]
    means = {label: float(d[col].mean()) for label, col in cats}
    tot = sum(means.values()) or 1
    structure = [{"category": k, "avg": round(v, 1), "ratio": round(v / tot, 3)} for k, v in means.items()]
    bins = [0, 500, 1000, 1500, 2000, 1e9]
    labels = ["<500", "500-1000", "1000-1500", "1500-2000", "2000+"]
    hist = pd.cut(d["total_cost"], bins=bins, labels=labels, right=False).value_counts().sort_index()
    return {
        "scenic_id": scenic_id,
        "avg_total": round(float(d["total_cost"].mean()), 1),
        "structure": structure,
        "histogram": [{"range": str(k), "count": int(v)} for k, v in hist.items()],
    }


@router.get("/demographics")
def demographics(scenic_id: str = "lingshan", days: int = 0, real_only: bool = False):
    """人口画像：年龄段 / 性别 / 同行规模分布。days>0 仅近 N 天。real_only=真实 xlsx 口径。"""
    d = _scope(scenic_id, days, real_only)
    if d.empty:
        return {"scenic_id": scenic_id, "age": [], "gender": [], "group_size": []}
    abins = [0, 18, 26, 36, 46, 56, 66, 200]
    alabels = ["<18", "18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
    age = pd.cut(d["age"], bins=abins, labels=alabels, right=False).value_counts().sort_index()
    gender = d["gender"].value_counts()
    grp = d["group_size"].value_counts().sort_index()
    return {
        "scenic_id": scenic_id,
        "age": [{"range": str(k), "count": int(v)} for k, v in age.items()],
        "gender": [{"gender": str(k), "count": int(v)} for k, v in gender.items()],
        "group_size": [{"size": int(k), "count": int(v)} for k, v in grp.items()],
    }


@router.get("/scenics")
def scenics(managed_only: bool = False):
    """可选景区/景点清单（供前端下拉），含样本量。
    默认列出**数据集里所有景点**（赛题 xlsx 全部景区 + 我方 8 个），`managed`=是否本产品接入。
    其余 BI 端点的 `scenic_id` 既接受我方 8 个 id（lingshan…），也直接接受 xlsx 里的景点名
    （如 `同里古镇`），故此处返回的 `scenic_id` 拿去查 overview/spending/demographics 都通。
    `managed_only=true` 时只返回我方 8 个。"""
    d = _data()
    counts = d["attraction_name"].value_counts().to_dict() if not d.empty else {}
    managed_names = set(SCENIC_NAME.values())
    items = [{"scenic_id": sid, "name": name, "samples": int(counts.get(name, 0)), "managed": True}
             for sid, name in SCENIC_NAME.items()]
    if not managed_only:
        # 追加 xlsx 里其余所有景点（非我方 8 个），scenic_id 就用景点名本身
        others = [{"scenic_id": str(name), "name": str(name), "samples": int(cnt), "managed": False}
                  for name, cnt in counts.items()
                  if name not in managed_names and str(name) != "nan"]
        others.sort(key=lambda x: x["samples"], reverse=True)
        items = items + others
    return {"scenics": items, "count": len(items)}


@router.get("/attractions")
def attractions(limit: int = 10, managed_only: bool = False):
    """景点热度排名（访问量）+ 各景点客单价/满意度/停留 + 类型偏好。
    managed_only=True 时仅统计本产品接入的 8 个景区（演示用，名称可辨识）；
    默认 False 为数据集全域视图。"""
    d = _data()
    if managed_only and not d.empty:
        d = d[d["attraction_name"].isin(SCENIC_NAME.values())]
    if d.empty:
        return {"ranking": [], "by_type": []}
    g = d.groupby("attraction_name").agg(
        visitors=("attraction_name", "size"),
        avg_spend=("total_cost", "mean"),
        avg_satisfaction=("satisfaction", "mean"),
        avg_stay=("stay_duration", "mean"),
    ).reset_index().sort_values("visitors", ascending=False)
    ranking = [{"attraction": r["attraction_name"], "visitors": int(r["visitors"]),
                "avg_spend": round(float(r["avg_spend"]), 1),
                "avg_satisfaction": round(float(r["avg_satisfaction"]), 2),
                "avg_stay": round(float(r["avg_stay"]), 1)} for _, r in g.head(limit).iterrows()]
    by_type = d["attraction_type"].value_counts()
    return {
        "ranking": ranking,
        "by_type": [{"type": str(k), "count": int(v)} for k, v in by_type.items() if str(k) != "nan"],
    }


# ── 消费分析（管理端「消费分析→营销决策」；默认 real_only 真实 xlsx 口径）─────────
def _src(real_only: bool, n: int) -> str:
    return f"赛题《景点景区旅游数据行为分析数据》· {n} 条" if real_only else "赛题数据+演示补充"


@router.get("/spend-tiers")
def spend_tiers(scenic_id: str = "lingshan", real_only: bool = True):
    """客单价分层（低/中/高）人群占比 + 各层画像（年龄/满意度/停留）。识别高价值客群。"""
    d = _scope(scenic_id, 0, real_only).dropna(subset=["total_cost"]).copy()
    if d.empty:
        return {"scenic_id": scenic_id, "tiers": []}
    bins = [0, 600, 1200, 1e12]
    labels = ["低消费(<600)", "中消费(600-1200)", "高消费(1200+)"]
    d["tier"] = pd.cut(d["total_cost"], bins=bins, labels=labels, right=False)
    n = len(d)
    tiers = []
    for lb in labels:
        sub = d[d["tier"] == lb]
        if len(sub) == 0:
            tiers.append({"name": lb, "count": 0, "ratio": 0.0})
            continue
        tiers.append({
            "name": lb, "count": int(len(sub)), "ratio": round(len(sub) / n, 3),
            "avg_spend": round(float(sub["total_cost"].mean()), 1),
            "revenue_share": round(float(sub["total_cost"].sum() / d["total_cost"].sum()), 3),
            "avg_age": round(float(sub["age"].mean()), 1) if sub["age"].notna().any() else None,
            "avg_satisfaction": round(float(sub["satisfaction"].mean()), 2) if sub["satisfaction"].notna().any() else None,
            "avg_stay": round(float(sub["stay_duration"].mean()), 1) if sub["stay_duration"].notna().any() else None,
        })
    return {"scenic_id": scenic_id, "total": n, "tiers": tiers, "source": _src(real_only, n)}


@router.get("/spend-drivers")
def spend_drivers(scenic_id: str = "lingshan", real_only: bool = True):
    """消费驱动因子：停留时长×客单价、同行规模×客单价（分桶均值），支撑「延长停留/家庭套票」决策。"""
    d = _scope(scenic_id, 0, real_only).dropna(subset=["total_cost"])
    if d.empty:
        return {"scenic_id": scenic_id, "stay": [], "group": []}
    ds = d.dropna(subset=["stay_duration"]).copy()
    sbins, slabels = [0, 2, 4, 6, 1e9], ["<2h", "2-4h", "4-6h", "6h+"]
    ds["b"] = pd.cut(ds["stay_duration"], bins=sbins, labels=slabels, right=False)
    stay = [{"range": lb,
             "avg_spend": round(float(ds[ds.b == lb]["total_cost"].mean()), 1) if len(ds[ds.b == lb]) else 0,
             "count": int(len(ds[ds.b == lb]))} for lb in slabels]
    dg = d.dropna(subset=["group_size"]).copy()

    def _gb(x):
        if x <= 1: return "独自"
        if x == 2: return "两人"
        if x <= 4: return "3-4人"
        return "5人+"
    dg["g"] = dg["group_size"].apply(_gb)
    gorder = ["独自", "两人", "3-4人", "5人+"]
    group = [{"range": g,
              "avg_spend": round(float(dg[dg.g == g]["total_cost"].mean()), 1) if len(dg[dg.g == g]) else 0,
              "count": int(len(dg[dg.g == g]))} for g in gorder]
    return {"scenic_id": scenic_id, "stay": stay, "group": group}


@router.get("/satisfaction-value")
def satisfaction_value(scenic_id: str = "lingshan", real_only: bool = True):
    """满意度×消费四象限（以中位数为轴）+ 散点样本。定位「高消费低满意」营收风险区。"""
    d = _scope(scenic_id, 0, real_only).dropna(subset=["total_cost", "satisfaction"])
    if d.empty:
        return {"scenic_id": scenic_id, "scatter": [], "quadrants": {}}
    ms, msat = float(d["total_cost"].median()), float(d["satisfaction"].median())
    q = {"high_spend_high_sat": 0, "high_spend_low_sat": 0, "low_spend_high_sat": 0, "low_spend_low_sat": 0}
    for _, r in d.iterrows():
        hs, hsat = r["total_cost"] >= ms, r["satisfaction"] >= msat
        if hs and hsat: q["high_spend_high_sat"] += 1
        elif hs: q["high_spend_low_sat"] += 1
        elif hsat: q["low_spend_high_sat"] += 1
        else: q["low_spend_low_sat"] += 1
    scatter = [{"spend": round(float(r["total_cost"]), 0), "sat": float(r["satisfaction"])}
               for _, r in d.head(150).iterrows()]
    return {"scenic_id": scenic_id, "median_spend": round(ms, 0), "median_sat": round(msat, 1),
            "quadrants": q, "scatter": scatter, "source": _src(real_only, len(d))}


@router.get("/spend-trend")
def spend_trend(scenic_id: str = "lingshan", real_only: bool = True, by: str = "month"):
    """按 visit_date 的消费/客流/营收趋势（月或周），支撑淡旺季营销节奏。"""
    d = _scope(scenic_id, 0, real_only).dropna(subset=["total_cost"]).copy()
    if d.empty or "visit_date" not in d.columns:
        return {"scenic_id": scenic_id, "trend": []}
    d["dt"] = pd.to_datetime(d["visit_date"], errors="coerce")
    d = d.dropna(subset=["dt"])
    if d.empty:
        return {"scenic_id": scenic_id, "trend": []}
    d["period"] = d["dt"].dt.strftime("%Y-%m") if by == "month" else d["dt"].dt.strftime("%Y-W%U")
    g = d.groupby("period").agg(visitors=("total_cost", "size"), avg_spend=("total_cost", "mean"),
                                revenue=("total_cost", "sum")).reset_index().sort_values("period")
    trend = [{"period": r["period"], "visitors": int(r["visitors"]),
              "avg_spend": round(float(r["avg_spend"]), 1), "revenue": round(float(r["revenue"]), 0)}
             for _, r in g.iterrows()]
    return {"scenic_id": scenic_id, "trend": trend}


@router.get("/marketing-advice")
def marketing_advice(scenic_id: str = "lingshan", real_only: bool = True):
    """规则化营销决策（确定性、可溯源到真实数字）：消费结构/停留杠杆/高价值客群/满意度风险。
    每条含 洞察→建议→预期。管理端 AI 运营代理可在此之上再做自然语言润色。"""
    d = _scope(scenic_id, 0, real_only).dropna(subset=["total_cost"])
    if d.empty:
        return {"scenic_id": scenic_id, "advice": []}
    n = len(d)
    cats = [("门票", "ticket_cost"), ("餐饮", "food_cost"), ("购物", "shopping_cost"),
            ("交通", "transport_cost"), ("娱乐", "entertainment_cost")]
    means = {k: float(d[c].mean()) for k, c in cats if c in d and d[c].notna().any()}
    tot = sum(means.values()) or 1
    advice = []
    if means:
        top_cat = max(means, key=means.get)
        low_cat = min(means, key=means.get)
        advice.append({
            "insight": f"消费结构中「{top_cat}」占比最高，约 {round(means[top_cat] / tot * 100)}%（人均 ¥{round(means[top_cat])}），而「{low_cat}」最低",
            "action": f"围绕{top_cat}做组合套餐/会员权益放大主力消费，同时用体验活动补强{low_cat}环节",
            "expected": "提升连带消费、拉高客单价"})
    ds = d.dropna(subset=["stay_duration"])
    lg = ds[ds["stay_duration"] >= 4]["total_cost"]
    sh = ds[ds["stay_duration"] < 4]["total_cost"]
    if len(lg) and len(sh) and lg.mean() > sh.mean() * 1.1:
        up = round((lg.mean() / sh.mean() - 1) * 100)
        advice.append({
            "insight": f"停留≥4小时游客客单价 ¥{round(float(lg.mean()))}，比短停留 ¥{round(float(sh.mean()))} 高 {up}%",
            "action": "以夜游、《灵山吉祥颂》演出、九龙灌浴场次、禅修体验延长游客停留时间",
            "expected": f"延长停留有望带动客单价提升约 {up}% 量级"})
    hi = d[d["total_cost"] >= 1200]
    if len(hi):
        advice.append({
            "insight": f"高消费客群（客单价≥¥1200）占 {round(len(hi) / n * 100)}%，却贡献营收 {round(float(hi['total_cost'].sum() / d['total_cost'].sum()) * 100)}%",
            "action": f"面向该客群（平均 {round(float(hi['age'].mean()))} 岁）推高端定制/贵宾祈福服务并精准投放",
            "expected": "用少量高价值客群撬动更高营收占比"})
    lowsat = d[d["satisfaction"] <= 2]
    if len(lowsat):
        advice.append({
            "insight": f"约 {round(len(lowsat) / n * 100)}% 游客满意度偏低（≤2分），平均客单价 ¥{round(float(lowsat['total_cost'].mean()))}",
            "action": "排查其消费环节体验（排队、餐饮性价比、购物），针对性改善",
            "expected": "降低差评、提升复游与口碑转化"})
    return {"scenic_id": scenic_id, "sample": n, "avg_spend": round(float(d["total_cost"].mean()), 1),
            "source": _src(real_only, n), "advice": advice}
