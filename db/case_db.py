import sqlite3
import os
from settings import cfg

save_dir = cfg.get("app", "save_dir")
DB_PATH = os.path.join(save_dir, "case.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 查询结果支持 dict 访问
    conn.execute("PRAGMA journal_mode=WAL;")  # 支持多进程并发
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            pet_name TEXT,
            species TEXT,
            breed TEXT,
            weight TEXT,
            deworming TEXT,
            sterilization TEXT,
            complaint TEXT,
            diagnosis TEXT,
            dialogue TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_case(data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO cases (
            case_id, name, phone, pet_name, species, breed, weight,
            deworming, sterilization, complaint, diagnosis, dialogue
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['case_id'], data['name'], data['phone'], data['pet_name'],
        data['species'], data['breed'], data['weight'],
        data['deworming'], data['sterilization'],
        data['complaint'], data['diagnosis'], data['dialogue']
    ))
    conn.commit()
    conn.close()


def get_cases_today():
    conn = get_conn()
    results = conn.execute("""
        SELECT case_id FROM cases
        WHERE DATE(created_at) = DATE('now')
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return [row["case_id"] for row in results]


def get_case_by_id(case_id):
    conn = get_conn()
    result = conn.execute(
        "SELECT * FROM cases WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.close()
    return dict(result) if result else None


def delete_case(case_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    conn.commit()
    conn.close()


def get_cases_by_date(date_str: str):
    # 假设 case_id 的格式是 "YYYYMMDD_N"
    conn = get_conn()
    sql = "SELECT case_id FROM cases WHERE case_id LIKE ? ORDER BY created_at DESC"
    pattern = f"{date_str}%"
    rows = conn.execute(sql, (pattern,)).fetchall()
    conn.close()
    return [r["case_id"] for r in rows]
