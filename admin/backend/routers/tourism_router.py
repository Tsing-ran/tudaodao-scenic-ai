import sqlite3
from pathlib import Path
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/tourism", tags=["tourism"])

DB_PATH = Path(__file__).parent.parent / "data" / "tourism.db"


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@router.get("/stats")
def get_stats(
    attraction_type: Optional[str] = Query(None, description="按景区类型筛选"),
    attraction_name: Optional[str] = Query(None, description="按景点名称筛选"),
    year: Optional[int]            = Query(None, description="按年份筛选"),
    month: Optional[int]           = Query(None, description="按月份筛选"),
):
    """综合统计：总览 KPI + 消费分布 + 客群画像 + 满意度分布"""
    con = _conn()

    where, params = _build_where(attraction_type, attraction_name, year, month)

    # ── 总览 KPI ──
    row = con.execute(f"""
        SELECT
            COUNT(*)                        AS total_visits,
            COUNT(DISTINCT tourist_id)      AS unique_tourists,
            COUNT(DISTINCT attraction_name) AS attraction_count,
            ROUND(AVG(satisfaction), 2)     AS avg_satisfaction,
            ROUND(AVG(total_cost),   1)     AS avg_total_cost,
            ROUND(AVG(stay_duration),1)     AS avg_stay_hours,
            ROUND(AVG(ticket_cost),  1)     AS avg_ticket_cost,
            ROUND(AVG(food_cost),    1)     AS avg_food_cost,
            ROUND(AVG(shopping_cost),1)     AS avg_shopping_cost
        FROM visits {where}
    """, params).fetchone()
    kpi = dict(row)

    # ── 景区类型满意度排名 ──
    type_sat = [dict(r) for r in con.execute(f"""
        SELECT attraction_type,
               ROUND(AVG(satisfaction),2) AS avg_sat,
               COUNT(*) AS visits
        FROM visits {where}
        GROUP BY attraction_type
        ORDER BY avg_sat DESC
    """, params).fetchall()]

    # ── 热门景点 Top 10 ──
    top_spots = [dict(r) for r in con.execute(f"""
        SELECT attraction_name,
               attraction_type,
               COUNT(*)                    AS visits,
               ROUND(AVG(satisfaction),2)  AS avg_sat,
               ROUND(AVG(total_cost),1)    AS avg_cost
        FROM visits {where}
        GROUP BY attraction_name
        ORDER BY visits DESC
        LIMIT 10
    """, params).fetchall()]

    # ── 满意度分布 ──
    sat_dist = [dict(r) for r in con.execute(f"""
        SELECT satisfaction AS score, COUNT(*) AS count
        FROM visits {where}
        GROUP BY satisfaction
        ORDER BY satisfaction
    """, params).fetchall()]

    # ── 年龄段分布 ──
    age_dist = [dict(r) for r in con.execute(f"""
        SELECT
            CASE
                WHEN age < 18         THEN '<18'
                WHEN age BETWEEN 18 AND 29 THEN '18-29'
                WHEN age BETWEEN 30 AND 44 THEN '30-44'
                WHEN age BETWEEN 45 AND 59 THEN '45-59'
                ELSE '60+'
            END AS age_group,
            COUNT(*) AS count
        FROM visits {where}
        GROUP BY age_group
        ORDER BY age_group
    """, params).fetchall()]

    # ── 性别分布 ──
    gender_dist = [dict(r) for r in con.execute(f"""
        SELECT gender, COUNT(*) AS count
        FROM visits {where}
        GROUP BY gender
    """, params).fetchall()]

    # ── 团队规模分布 ──
    group_dist = [dict(r) for r in con.execute(f"""
        SELECT group_size, COUNT(*) AS count
        FROM visits {where}
        GROUP BY group_size
        ORDER BY group_size
    """, params).fetchall()]

    # ── 月度趋势（仅当未指定月份时） ──
    monthly = []
    if month is None:
        monthly = [dict(r) for r in con.execute(f"""
            SELECT SUBSTR(visit_date, 1, 7) AS month,
                   COUNT(*)                  AS visits,
                   ROUND(AVG(satisfaction),2) AS avg_sat,
                   ROUND(AVG(total_cost),1)   AS avg_cost
            FROM visits {where}
            GROUP BY month
            ORDER BY month
        """, params).fetchall()]

    con.close()
    return {
        "kpi":         kpi,
        "type_sat":    type_sat,
        "top_spots":   top_spots,
        "sat_dist":    sat_dist,
        "age_dist":    age_dist,
        "gender_dist": gender_dist,
        "group_dist":  group_dist,
        "monthly":     monthly,
    }


@router.get("/types")
def list_types():
    """返回所有景区类型"""
    con = _conn()
    rows = con.execute("SELECT DISTINCT attraction_type FROM visits ORDER BY attraction_type").fetchall()
    con.close()
    return [r[0] for r in rows]


@router.get("/attractions")
def list_attractions(attraction_type: Optional[str] = Query(None)):
    """返回景点列表（可按类型筛选）"""
    con = _conn()
    if attraction_type:
        rows = con.execute(
            "SELECT DISTINCT attraction_name FROM visits WHERE attraction_type=? ORDER BY attraction_name",
            (attraction_type,)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT DISTINCT attraction_name FROM visits ORDER BY attraction_name"
        ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _build_where(attraction_type, attraction_name, year, month):
    conditions, params = [], []
    if attraction_type:
        conditions.append("attraction_type = ?"); params.append(attraction_type)
    if attraction_name:
        conditions.append("attraction_name = ?"); params.append(attraction_name)
    if year:
        conditions.append("SUBSTR(visit_date,1,4) = ?"); params.append(str(year))
    if month:
        conditions.append("CAST(SUBSTR(visit_date,6,2) AS INTEGER) = ?"); params.append(month)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params
