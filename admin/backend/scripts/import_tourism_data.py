"""
一次性导入脚本：将旅游行为分析 Excel 导入 SQLite 数据库
用法：python backend/scripts/import_tourism_data.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

EXCEL_PATH = Path(__file__).parent.parent.parent / "20260323113204906" / "示范景区公开资料包" / "景点景区旅游数据行为分析数据.xlsx"
DB_PATH    = Path(__file__).parent.parent / "data" / "tourism.db"

def main():
    print(f"读取 Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, parse_dates=["visit_date"])

    # 只保留分析用字段，跳过超长的 attraction_content
    cols = [
        "tourist_id", "user_nickname", "age", "gender",
        "attraction_name", "attraction_type",
        "visit_date", "stay_duration",
        "ticket_cost", "food_cost", "shopping_cost",
        "transport_cost", "entertainment_cost", "total_cost",
        "group_size", "satisfaction",
    ]
    df = df[cols].copy()
    df["visit_date"] = df["visit_date"].dt.strftime("%Y-%m-%d")

    print(f"共 {len(df)} 条记录，写入 {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    df.to_sql("visits", con, if_exists="replace", index=False)

    # 建索引加速常用查询
    con.execute("CREATE INDEX IF NOT EXISTS idx_attraction ON visits(attraction_name)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_type      ON visits(attraction_type)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_date      ON visits(visit_date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sat       ON visits(satisfaction)")
    con.commit()

    # 验证
    count = con.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    print(f"导入完成，数据库记录数: {count}")
    con.close()

if __name__ == "__main__":
    main()
