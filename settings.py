import os
import sqlite3
from typing import Any, Dict
from pathlib import Path
from loguru import logger

home = os.environ.get("VETVOICE_PATH", Path.home())
vetvoice_folder = os.path.join(home, ".vetvoice")
os.makedirs(vetvoice_folder, exist_ok=True)

DB_PATH = os.path.join(vetvoice_folder, "config.db")

# 默认配置（初始写入数据库用）
DEFAULT_CONFIG = {
    "app": {
        "save_dir": "",
        "resource_dir": ""
    },
    "input_device": {},
    "output_device": {},
    "asr": {
        "denoise": True,
        "model":"vosk",
        "model_funasr_path": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
        "model_vosk_path": "vosk/vosk-model-small-cn-0.22",
        "device":"mps"
    },
    "process": {
        "audio_queue_size": 100,
        "text_queue_size": 100
    },
        
    "spk": {
        "model_pyannote_path": "pyannote/embedding",
        "device":"mps"
    },
    "llm": {
        "api_key": "",
        "api_base": "",
        "model": ""
    },
}


class ConfigManager:
    def __init__(self):
        self._init_db()
        self._ensure_defaults()

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # 并发读写友好
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                section TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (section, key)
            )
        """)
        conn.commit()
        conn.close()

    def _ensure_defaults(self):
        """如果数据库里没有某些默认配置，则写入"""
        for section, kv in DEFAULT_CONFIG.items():
            for key, value in kv.items():
                if self.get(section, key) is None:
                    self.set(section, key, value)

    def get(self, section: str, key: str = None, default: Any = None):
        conn = self._get_conn()
        if key is None:
            rows = conn.execute(
                "SELECT key, value FROM config WHERE section=?", (section,)
            ).fetchall()
            conn.close()
            if not rows:
                return default
            return {row["key"]: self._deserialize(row["value"]) for row in rows}
        else:
            row = conn.execute(
                "SELECT value FROM config WHERE section=? AND key=?",
                (section, key),
            ).fetchone()
            conn.close()
            return self._deserialize(row["value"]) if row else default

    def set(self, section: str, key: str, value: Any):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO config (section, key, value) VALUES (?, ?, ?)",
            (section, key, self._serialize(value)),
        )
        conn.commit()
        conn.close()

    def set_save(self, section: str, key: str, value: Any):
        """和 set 等价，SQLite 会立即持久化"""
        self.set(section, key, value)

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        """返回整个配置为 dict"""
        conn = self._get_conn()
        rows = conn.execute("SELECT section, key, value FROM config").fetchall()
        conn.close()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            sec = row["section"]
            if sec not in result:
                result[sec] = {}
            result[sec][row["key"]] = self._deserialize(row["value"])
        return result

    def __getitem__(self, section):
        return self.get(section, None, {})

    def __setitem__(self, section, value: Dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError("Section value must be a dict")
        for k, v in value.items():
            self.set(section, k, v)

    @staticmethod
    def _serialize(value: Any) -> str:
        import json
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _deserialize(value: str) -> Any:
        import json
        try:
            return json.loads(value)
        except Exception:
            return value


cfg = ConfigManager()

import numpy as np
from dataclasses import dataclass, field
import datetime

@dataclass
class Utterance:
    audio: np.ndarray
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    end_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    is_final: bool = False
    text: str = ""
    speaker: str = "unknown"

    @property
    def duration(self):
        return len(self.audio) / 16000  # 16kHz