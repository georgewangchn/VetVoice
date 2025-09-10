import sqlite3
import os
from settings import cfg
from typing import Dict, List, Any, Type
import json
save_dir = cfg.get("app", "save_dir")
DB_PATH = os.path.join(save_dir, "vv.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


class BaseTableManagerMeta(type):
    """元类：自动收集所有子类"""
    registry: List[Type["BaseTableManager"]] = []

    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        # 排除基类本身
        if name != "BaseTableManager":
            BaseTableManagerMeta.registry.append(cls)
        return cls


class BaseTableManager(metaclass=BaseTableManagerMeta):
    """数据库表管理基类"""
    table_name: str = ""
    schema: str = ""   # 子类必须定义

    @classmethod
    def init_table(cls):
        conn = get_conn()
        conn.execute(cls.schema)
        conn.commit()
        conn.close()

    @classmethod
    def insert(cls, data: Dict[str, Any]):
        conn = get_conn()
        fields = ",".join(data.keys())
        placeholders = ",".join(["?"] * len(data))
        sql = f"INSERT OR REPLACE INTO {cls.table_name} ({fields}) VALUES ({placeholders})"
        conn.execute(sql, tuple(data.values()))
        conn.commit()
        conn.close()

    @classmethod
    def delete(cls, where: str, params: tuple):
        conn = get_conn()
        sql = f"DELETE FROM {cls.table_name} WHERE {where}"
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    @classmethod
    def get_one(cls, where: str, params: tuple) -> Dict[str, Any] | None:
        conn = get_conn()
        sql = f"SELECT * FROM {cls.table_name} WHERE {where}"
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return dict(row) if row else None

    @classmethod
    def get_all(cls, where: str = "1=1", params: tuple = ()) -> List[Dict[str, Any]]:
        conn = get_conn()
        sql = f"SELECT * FROM {cls.table_name} WHERE {where}"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# -------------------------------------------------
# 具体表：病例表
# -------------------------------------------------
class CaseManager(BaseTableManager):
    table_name = "cases"
    schema = """
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
            checkup TEXT,
            results TEXT,
            diagnosis TEXT,
            treatment TEXT,
            dialogue TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    @classmethod
    def get_case_by_date(cls, date_str: str=None) -> List[str]:
        conn = get_conn()
        if not date_str:
            results = conn.execute("""
                SELECT case_id FROM cases
                WHERE DATE(created_at) = DATE('now')
                ORDER BY created_at DESC
            """).fetchall()
        else:
            sql = "SELECT case_id FROM cases WHERE case_id LIKE ? ORDER BY created_at DESC"
            pattern = f"{date_str}%"
            results = conn.execute(sql, (pattern,)).fetchall()
        conn.close()
        return [r["case_id"] for r in results]


class VedisManager(BaseTableManager):
    table_name = "vedis"
    schema = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            key TEXT PRIMARY KEY,
            value TEXT,
            type TEXT
        )
    """

    @classmethod
    def init_table(cls):
        """初始化表并在启动时清空"""
        conn = get_conn()
        conn.execute(cls.schema)
        conn.execute(f"DELETE FROM {cls.table_name}")  # 系统启动时清空缓存
        conn.commit()
        conn.close()

    @classmethod
    def set(cls, key: str, value):
        """保存数据，支持 str/json"""
        if isinstance(value, (dict, list)):
            raw, vtype = json.dumps(value, ensure_ascii=False), "json"
        else:
            raw, vtype = str(value), "str"

        conn = get_conn()
        conn.execute(f"""
            INSERT OR REPLACE INTO {cls.table_name}(key, value, type)
            VALUES (?, ?, ?)
        """, (key, raw, vtype))
        conn.commit()
        conn.close()

    @classmethod
    def get(cls, key: str):
        """获取数据，自动解析 json"""
        conn = get_conn()
        row = conn.execute(
            f"SELECT value, type FROM {cls.table_name} WHERE key=?", (key,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return json.loads(row["value"]) if row["type"] == "json" else row["value"]

    @classmethod
    def delete(cls, key: str):
        """删除指定 key"""
        conn = get_conn()
        conn.execute(f"DELETE FROM {cls.table_name} WHERE key=?", (key,))
        conn.commit()
        conn.close()

    @classmethod
    def clear(cls):
        """清空表"""
        conn = get_conn()
        conn.execute(f"DELETE FROM {cls.table_name}")
        conn.commit()
        conn.close()

# -------------------------------------------------
# 自动初始化所有表
# -------------------------------------------------
def init_db():
    for manager_cls in BaseTableManagerMeta.registry:
        manager_cls.init_table()
