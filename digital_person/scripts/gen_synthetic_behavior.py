"""为 8 个景区造游客行为数据（与赛题 xlsx 17 列 schema 一致），补足 BI 大屏所需样本。
真实赛题 xlsx 是多景点混合、我们的景区行数少；这里按景区类型注入合理分布的合成数据，
与真实数据合并供 /analytics/bi/* 使用。纯造数，无随机性依赖（用固定 RNG 种子可复现）。
用法：.venv/bin/python scripts/gen_synthetic_behavior.py [每景区行数=2500]
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "示范景区公开资料包" / "synthetic_behavior.csv"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
rng = np.random.default_rng(20260614)

# 8 景区：名称 / 类型 / 票价基准 / 平均停留(h) / 满意度偏置
SCENICS = {
    "灵山胜境":   ("宗教文化", 210, 4.5, 4.4),
    "拈花湾":     ("度假小镇", 120, 5.0, 4.5),
    "西湖":       ("自然山水", 0,   3.5, 4.6),
    "黄山":       ("自然山岳", 190, 6.0, 4.3),
    "故宫":       ("博物馆古迹", 60, 3.5, 4.5),
    "张家界":     ("自然山岳", 225, 6.5, 4.4),
    "兵马俑":     ("博物馆古迹", 120, 2.5, 4.2),
    "莫高窟":     ("石窟艺术", 238, 2.0, 4.3),
}
SURNAMES = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林郑谢罗梁宋唐许韩冯邓曹彭曾肖田董袁潘")
GIVEN = list("芳娜敏静秀丽强磊军洋勇艳杰娟涛明超霞平刚桂兰梅琳云燕鹏华飞红玉")


def gen_scenic(name, info):
    typ, base_ticket, base_stay, base_sat = info
    age = np.clip(rng.normal(36, 13, N), 16, 75).astype(int)
    gender = rng.choice(["男", "女"], N, p=[0.46, 0.54])
    # 访问日期：近 180 天，周末/节假日加权
    days_ago = rng.integers(0, 180, N)
    dates = (pd.Timestamp("2026-06-14") - pd.to_timedelta(days_ago, unit="D"))
    weekend_boost = rng.random(N) < 0.15
    dates = dates - pd.to_timedelta(np.where(weekend_boost, rng.integers(0, 2, N), 0), unit="D")
    stay = np.clip(rng.normal(base_stay, base_stay * 0.3, N), 0.5, 12).round(1)
    group = rng.choice([1, 2, 3, 4, 5, 6], N, p=[0.18, 0.34, 0.20, 0.15, 0.08, 0.05])
    # 消费：门票×人数 + 餐饮/购物/交通/娱乐（随类型/停留波动）
    ticket = np.where(base_ticket == 0, rng.normal(0, 5, N).clip(0),
                      rng.normal(base_ticket, base_ticket * 0.1, N).clip(0)) * group
    food = (rng.normal(55, 25, N).clip(10) * group * (stay / base_stay)).round(2)
    shopping = (rng.gamma(2.0, 80, N) * (group ** 0.5)).round(2)
    transport = rng.normal(60, 35, N).clip(0).round(2) * (group ** 0.4)
    enter = (rng.gamma(1.5, 70, N) if typ in ("度假小镇", "宗教文化") else rng.gamma(1.2, 40, N)).round(2)
    ticket = ticket.round(2)
    total = (ticket + food + shopping + transport + enter).round(2)
    # 满意度：景区偏置 + 噪声，离散 1-5（偏高）
    sat = np.clip(np.round(rng.normal(base_sat, 0.6, N)), 1, 5).astype(int)
    return pd.DataFrame({
        "tourist_id": [f"S{name[:2]}{i:05d}" for i in range(N)],
        "user_nickname": [rng.choice(SURNAMES) + rng.choice(GIVEN) + rng.choice(GIVEN) for _ in range(N)],
        "age": age, "gender": gender,
        "attraction_name": name, "attraction_content": "", "attraction_type": typ,
        "visit_date": dates.strftime("%Y-%m-%d"),
        "stay_duration": stay, "ticket_cost": ticket, "food_cost": food,
        "shopping_cost": shopping, "transport_cost": transport, "entertainment_cost": enter,
        "total_cost": total, "group_size": group, "satisfaction": sat,
    })


def main():
    dfs = [gen_scenic(n, info) for n, info in SCENICS.items()]
    df = pd.concat(dfs, ignore_index=True)
    df.to_csv(OUT, index=False)
    print(f"✅ 合成 {len(df)} 行（{len(SCENICS)} 景区 × {N}）→ {OUT}")
    print("   各景区客单价/满意度抽样：")
    g = df.groupby("attraction_name").agg(客单价=("total_cost", "mean"), 满意度=("satisfaction", "mean"), n=("tourist_id", "size"))
    print(g.round(1).to_string())


if __name__ == "__main__":
    main()
