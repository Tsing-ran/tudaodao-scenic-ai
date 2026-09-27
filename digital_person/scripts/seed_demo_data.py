"""演示数据播种器：给 conversations / events 两张表造近 N 天的演示数据（解决大屏冷启动全零）。

设计约束：
- 所有演示行 session_id 一律带 ``demo-`` 前缀 → ``--wipe`` 一键清除，随时可回到纯真实口径；
- 播种幂等：写入前先清掉同景区旧 demo 行，跑多少遍都不会翻倍；
- 数值形态手工编排出真实节律：周末高峰/周二低谷 + 每日上午10点/下午15点双峰时段，
  情绪/客群/功能使用/评分/推荐点击全部按合理权重分布，图表天然跌宕起伏；
- 每天用 (scenic, date) 做随机种子 → 同一天反复播种结果一致，演示期间数字不会跳变。

用法（服务器 live 目录下，用跑 rag 的同一 python）：
  python scripts/seed_demo_data.py --scenic lingshan --days 7
  python scripts/seed_demo_data.py --scenic all --days 7
  python scripts/seed_demo_data.py --wipe                # 清除全部演示行
  python scripts/seed_demo_data.py --wipe --scenic xihu  # 只清一个景区
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db.database import DB_PATH, init_db  # noqa: E402
from backend.data.danmaku_bank import bank_for  # noqa: E402  # 弹幕题库：演示提问与弹幕兜底同源

SCENICS = ["lingshan", "nihuawan", "xihu", "huangshan", "gugong", "zhangjiajie", "bingmayong", "mogaoku"]

# 各景区代表景点（进问题文本，让 topic-intents / 热门话题 / 景点关注度有血有肉）
SPOTS = {
    "lingshan":    ["灵山大佛", "九龙灌浴", "梵宫", "五印坛城", "佛手广场", "降魔浮雕"],
    "nihuawan":    ["拈花塔", "香月花街", "五灯湖", "禅意客栈", "微笑广场"],
    "xihu":        ["断桥", "雷峰塔", "三潭印月", "苏堤", "灵隐寺", "花港观鱼"],
    "huangshan":   ["迎客松", "光明顶", "西海大峡谷", "莲花峰", "云谷索道"],
    "gugong":      ["太和殿", "珍宝馆", "御花园", "午门", "角楼", "钟表馆"],
    "zhangjiajie": ["天门山", "玻璃栈道", "袁家界", "金鞭溪", "百龙天梯"],
    "bingmayong":  ["一号坑", "铜车马", "跪射俑", "二号坑"],
    "mogaoku":     ["九层楼", "藏经洞", "第96窟", "数字展示中心"],
}

# 问题模板：{spot} 占位；权重≈真实景区问询构成（服务性问题占大头）
Q_TEMPLATES = [
    ("{spot}在哪里，怎么走", 10),
    ("{spot}要另外买票吗", 9),
    ("{spot}几点开放", 8),
    ("最近的厕所在哪里", 8),
    ("{spot}有什么来历", 7),
    ("附近有吃饭的地方吗", 7),
    ("帮我推荐一条半天的路线", 6),
    ("{spot}值得去吗", 5),
    ("演出时间是几点", 5),
    ("带孩子玩有什么推荐", 4),
    ("门票多少钱一张", 4),
    ("{spot}可以拍照吗", 3),
    ("停车场在哪个门", 3),
    ("轮椅方便进{spot}吗", 2),
    ("有讲解服务吗", 2),
]
REPLIES = [
    "好的，这就为您详细讲解～", "已为您规划好路线，请看地图指引。",
    "为您找到相关信息，往下看哦。", "这个问题问得好，听我慢慢道来。",
    "已标注在地图上，跟着导航走约几分钟就到。",
]

# 情绪分布（对齐 analytics 的 _POSITIVE/_NEUTRAL/_NEGATIVE 集合；正面≈54%）
EMOTIONS = [("happy", 38), ("excited", 16), ("neutral", 22), ("curious", 14), ("empathetic", 6), ("apologetic", 4)]
GROUPS   = [("adult", 45), ("family_kids", 30), ("couple", 17), ("senior", 8)]
LANGS    = [("zh", 82), ("en", 10), ("ja", 4), ("ko", 4)]
FEATURES = [("chat", 30), ("voice", 22), ("tour", 16), ("photo", 10), ("gps", 9),
            ("facility", 6), ("postcard", 4), ("trace", 2), ("avatar", 1)]
SCORES   = [(5, 52), (4, 30), (3, 12), (2, 4), (1, 2)]
INTERESTS = ["历史文化", "美食", "摄影", "亲子", "祈福", "自然风光", "建筑", "演出"]
SITUATION = {
    "age":        [("青年", 5), ("中年", 3), ("长者", 2)],
    "pace":       [("正常", 5), ("慢慢逛", 3), ("赶时间", 2)],
    "mobility":   [("良好", 7), ("一般", 2), ("推婴儿车", 1)],
    "purpose":    [("观光", 5), ("亲子", 2), ("摄影", 2), ("祈福", 1)],
    "first_time": [("是", 7), ("否", 3)],
}
RECO_TITLES = ["经典半日游路线", "亲子慢游路线", "日落摄影机位", "特色餐饮推荐", "演出场次提醒"]
RECO_ACTIONS = [("view_detail", 5), ("open_route", 3), ("navigate", 2), ("add_plan", 1)]

# 🆕 P3 游中画像演示数据（visitor_profile 行 + geo_arrival 事件，喂 /profile 的三个新字段）
DEMO_INT_IDS = ["history", "nature", "photo", "food", "culture"]  # 与 _INT_LABEL 对齐
DEMO_STYLES  = ["打卡型", "深度型", "亲子型", "悠闲型", "摄影型"]
DEMO_WISHES  = ["想看一场演出", "想尝当地素斋", "想登高看日落", "想拍标志性合影", "想深度听讲解"]
DEMO_NEEDS   = ["就近餐饮", "无障碍通道", "更多休息区", "母婴室指引", "演出场次提醒"]

# 周节律（周一→周日）与时段双峰（8-21 点）
WEEK_FACTOR = [0.82, 0.76, 0.88, 0.95, 1.18, 1.72, 1.55]
HOUR_WEIGHTS = {8: 4, 9: 7, 10: 10, 11: 9, 12: 6, 13: 5, 14: 7, 15: 10, 16: 8, 17: 5, 18: 3, 19: 2, 20: 2, 21: 1}
BASE_PER_DAY = 46  # 基准对话条数/天（乘周节律与抖动后 ≈ 35~85）


def _pick(rng: random.Random, weighted):
    items, weights = zip(*weighted)
    return rng.choices(items, weights=weights, k=1)[0]


def _ts(day: datetime, rng: random.Random) -> str:
    hours, weights = zip(*HOUR_WEIGHTS.items())
    h = rng.choices(hours, weights=weights, k=1)[0]
    return day.replace(hour=h, minute=rng.randrange(60), second=rng.randrange(60)).strftime("%Y-%m-%d %H:%M:%S")


def wipe(conn: sqlite3.Connection, scenic: str | None) -> None:
    cond, args = "session_id LIKE 'demo-%'", []
    if scenic:
        cond += " AND scenic_id=?"
        args.append(scenic)
    c1 = conn.execute(f"DELETE FROM conversations WHERE {cond}", args).rowcount
    c2 = conn.execute(f"DELETE FROM events WHERE {cond}", args).rowcount
    c3 = conn.execute(f"DELETE FROM visitor_profile WHERE {cond}", args).rowcount
    conn.commit()
    print(f"  wiped: conversations {c1} 行, events {c2} 行, visitor_profile {c3} 行"
          + (f"（{scenic}）" if scenic else "（全部景区）"))


def _seed_profiles(conn, scenic, sessions, spots, day, rng) -> tuple[int, int]:
    """为部分会话造 visitor_profile 行 + geo_arrival 到访事件（喂 /profile 三个新字段）。"""
    vp_rows, geo_rows = [], []
    for sid in sessions:
        if rng.random() > 0.62:      # 约 62% 会话形成游中画像
            continue
        ints = rng.sample(DEMO_INT_IDS, rng.randint(1, 3))
        visited = rng.sample(spots, min(len(spots), rng.randint(2, 4)))
        # geo_arrival 序列：为 visited 造带停留间隔的到访（间隔决定 style_hint）
        stay = rng.choice([4, 8, 12, 18])
        t = day.replace(hour=rng.choice([9, 10, 13, 14]), minute=rng.randrange(30), second=0)
        for name in visited:
            geo_rows.append((sid, scenic, "geo_arrival", None, None,
                             json.dumps({"name": name, "distance": rng.randint(5, 40)}, ensure_ascii=False),
                             t.strftime("%Y-%m-%d %H:%M:%S")))
            t = t + timedelta(minutes=stay + rng.randint(-2, 4))
        traits: dict = {}
        if rng.random() < 0.72:
            traits["style"] = rng.choice(DEMO_STYLES)
        if rng.random() < 0.45:
            traits["wishes"] = [rng.choice(DEMO_WISHES)]
        if rng.random() < 0.5:
            traits["needs"] = rng.sample(DEMO_NEEDS, rng.randint(1, 2))
        vp_rows.append((sid, scenic, json.dumps(ints, ensure_ascii=False),
                        json.dumps(visited, ensure_ascii=False), "[]", "{}",
                        json.dumps(traits, ensure_ascii=False), "", rng.randint(2, 12), _ts(day, rng)))
    if geo_rows:
        conn.executemany(
            "INSERT INTO events (session_id, scenic_id, type, group_type, lang, payload, created_at) "
            "VALUES (?,?,?,?,?,?,?)", geo_rows)
    if vp_rows:
        conn.executemany(
            "INSERT OR REPLACE INTO visitor_profile "
            "(session_id, scenic_id, interests, visited, asked_pois, intent_stats, traits, summary, turn_count, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)", vp_rows)
    return len(vp_rows), len(geo_rows)


def seed_scenic(conn: sqlite3.Connection, scenic: str, days: int) -> None:
    wipe(conn, scenic)
    spots = SPOTS.get(scenic, ["主景区"])
    today = datetime.now()
    total_conv = total_evt = total_vp = 0

    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        rng = random.Random(f"{scenic}:{day:%Y-%m-%d}")
        n_conv = int(BASE_PER_DAY * WEEK_FACTOR[day.weekday()] * rng.uniform(0.9, 1.12))
        # 今天只播到当前时刻的比例（避免"未来数据"）
        if offset == 0:
            n_conv = max(3, int(n_conv * min(1.0, (day.hour + 1) / 22)))
        n_sessions = max(2, n_conv // rng.randint(2, 3))
        sessions = [f"demo-{scenic}-{day:%m%d}-{i}" for i in range(n_sessions)]

        # ── conversations ──
        rows = []
        bank = bank_for(scenic)
        for _ in range(n_conv):
            # 45% 用手写题库（更像真人打字问的），其余走模板×景点组合保话题覆盖面
            if bank and rng.random() < 0.45:
                q = rng.choice(bank)[0]
            else:
                tpl = _pick(rng, Q_TEMPLATES)
                q = tpl.format(spot=rng.choice(spots))
            rows.append((rng.choice(sessions), scenic, q, rng.choice(REPLIES),
                         _pick(rng, EMOTIONS), 1 if rng.random() < 0.9 else 0, _ts(day, rng)))
        conn.executemany(
            "INSERT INTO conversations (session_id, scenic_id, user_message, ai_reply, emotion, context_used, created_at) "
            "VALUES (?,?,?,?,?,?,?)", rows)
        total_conv += len(rows)

        # ── events ──
        evts = []
        for sid in sessions:
            payload = {
                "interests": rng.sample(INTERESTS, rng.randint(1, 3)),
                **{dim: _pick(rng, opts) for dim, opts in SITUATION.items()},
            }
            evts.append((sid, scenic, "session_start", _pick(rng, GROUPS), _pick(rng, LANGS),
                         json.dumps(payload, ensure_ascii=False), _ts(day, rng)))
            for _ in range(rng.randint(1, 4)):
                evts.append((sid, scenic, "feature_open", None, None,
                             json.dumps({"feature": _pick(rng, FEATURES)}), _ts(day, rng)))
            if rng.random() < 0.4:
                evts.append((sid, scenic, "rating", None, None,
                             json.dumps({"score": _pick(rng, SCORES)}), _ts(day, rng)))
            if rng.random() < 0.65:
                evts.append((sid, scenic, "reco_impression", None, None,
                             json.dumps({"count": rng.randint(1, 3)}), _ts(day, rng)))
                if rng.random() < 0.42:
                    evts.append((sid, scenic, "reco_click", None, None,
                                 json.dumps({"title": rng.choice(RECO_TITLES),
                                             "action": _pick(rng, RECO_ACTIONS)}), _ts(day, rng)))
        conn.executemany(
            "INSERT INTO events (session_id, scenic_id, type, group_type, lang, payload, created_at) "
            "VALUES (?,?,?,?,?,?,?)", evts)
        total_evt += len(evts)

        # ── 游中画像 + 到访轨迹（🆕 P3） ──
        n_vp, n_geo = _seed_profiles(conn, scenic, sessions, spots, day, rng)
        total_vp += n_vp
        total_evt += n_geo

    conn.commit()
    print(f"  seeded {scenic}: conversations +{total_conv}, events +{total_evt}, "
          f"visitor_profile +{total_vp}（近{days}天，demo- 前缀）")


def main() -> None:
    ap = argparse.ArgumentParser(description="大屏演示数据播种/清除")
    ap.add_argument("--scenic", default=None, help="景区 id 或 all（播种默认 lingshan；--wipe 默认全部）")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--wipe", action="store_true", help="只清除演示行，不播种")
    args = ap.parse_args()

    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        if args.wipe:
            # --wipe 不带 --scenic（或 --scenic all）= 清全部演示行
            wipe(conn, None if args.scenic in (None, "all") else args.scenic)
            return
        scenic = args.scenic or "lingshan"
        targets = SCENICS if scenic == "all" else [scenic]
        for s in targets:
            seed_scenic(conn, s, args.days)
        print(f"done. DB = {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
