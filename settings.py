import os
import json
from typing import Any
from functools import lru_cache
from pathlib import Path
from loguru import logger
home = os.environ.get("VETVOICE_PATH",Path.home())
vetvoice_folder =os.path.join(home,".vetvoice") 
os.makedirs(vetvoice_folder, exist_ok=True)
CONFIG_PATH = os.path.join(vetvoice_folder,"config.json") 
DEFAULT_CONFIG = {
    "app": {
        "save_dir": "",
        "resource_dir": ""
    },
    "input_device": {},
    "output_device": {},
    "asr": {
        "model_speech_path": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
        "model_vosk_path": "vosk/vosk-model-small-cn-0.22"
    },
    "process": {
        "audio_queue_size": 100,
        "text_queue_size": 100
    },
    "spk": {
        "model_embedding_path": "pyannote/embedding"
    },
    "llm": {
        "api_key": "",
        "api_base": "",
        "model": ""
    }
}
class ConfigManager:
    def __init__(self):
        self._config = {}  
        self.load()
    def load(self):

        if not os.path.exists(CONFIG_PATH):
            self._config = DEFAULT_CONFIG
            return self._config
        else:
            logger.debug(f"加载配置文件config.json: {CONFIG_PATH}")
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = json.load(f)
                return self._config


    def save(self):
        """保存当前配置到文件"""
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._config, f)
    # @lru_cache(maxsize=10)
    def get(self, section: str, key: str = None, default: Any = None):
        self.load()
        """获取某个配置值"""
        if section not in self._config:
            return default
        if key is None:
            return self._config[section]
        return self._config[section].get(key, default)

    def set(self, section: str, key: str, value: Any):
        """设置某个配置值"""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    def set_save(self, section: str, key: str, value: Any):
        self.set(section, key, value)
        self.save()

    def as_dict(self):
        """返回整个配置字典"""
        return self._config

    def __getitem__(self, section):
        return self._config[section]

    def __setitem__(self, section, value):
        self._config[section] = value
cfg = ConfigManager()
