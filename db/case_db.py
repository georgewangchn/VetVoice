import duckdb
import os
from settings import cfg
save_dir = cfg.get("app","save_dir")
DB_PATH = os.path.join(save_dir, "case.db")

def init_db():
    conn = duckdb.connect(DB_PATH)
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
            created_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    conn.close()

def insert_case(data: dict):
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO cases (
            case_id, name, phone, pet_name, species, breed, weight,
            deworming, sterilization, complaint, diagnosis,dialogue
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['case_id'], data['name'], data['phone'], data['pet_name'],
        data['species'], data['breed'], data['weight'],
        data['deworming'], data['sterilization'],
        data['complaint'], data['diagnosis'],data['dialogue']
    ))
    conn.close()

def get_cases_today():
    conn = duckdb.connect(DB_PATH)
    results = conn.execute("""
        SELECT case_id FROM cases
        WHERE date_trunc('day', created_at) = date_trunc('day', now())
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return [row[0] for row in results]

def get_case_by_id(case_id):
    conn = duckdb.connect(DB_PATH)
    result = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    conn.close()
    return result
def delete_case(case_id: str):
    conn = duckdb.connect(DB_PATH)
    conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    conn.close()
def get_cases_by_date(date_str: str):
    # 假设 case_id 的格式是 "YYYYMMDD_N"
    conn = duckdb.connect(DB_PATH)
    sql = "SELECT case_id FROM cases WHERE case_id LIKE ? ORDER BY created_at DESC"
    pattern = f"{date_str}%"
    rows = conn.execute(sql, (pattern,)).fetchall()
    return [r[0] for r in rows]