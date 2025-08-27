from PySide6.QtCore import QObject, Signal
from threading import Thread
from settings import cfg
from loguru import logger
import httpx
import asyncio
import json
from diagnosis.template import *
import traceback
API_KEY=cfg.get("llm", "api_key")
BASE_URL=cfg.get("llm", "api_base")
MODEL=cfg.get("llm", "model")
TEMPLATE_MAP = {
    "🩺 辅诊": {
        "生成": DIAGNOSE_TEMPLATE,
        "修饰": DIAGNOSE_TEMPLATE_REWRITE,
        "格式": DIAGNOSE_TEMPLATE_FORMAT,
    },
    "📋 主诉": {
        "生成": COMPLAINT_TEMPLATE,
        "修饰": COMPLAINT_TEMPLATE_REWRITE,
        "格式": COMPLAINT_TEMPLATE_FORMAT,
    },
    "📇 基本信息": {
        "生成": INFO_TEMPLATE,
        "修饰": INFO_TEMPLATE_REWRITE,
        "格式": INFO_TEMPLATE_FORMAT,
    },
    "💊 用药": {
        "生成": MEDICATION_TEMPLATE,
        "修饰": MEDICATION_TEMPLATE_REWRITE,
        "格式": MEDICATION_TEMPLATE_FORMAT,
    },
    "🧪 质检": {
        "生成": QUALITY_CHECK_TEMPLATE,
        "修饰": QUALITY_CHECK_TEMPLATE_REWRITE,
        "格式": QUALITY_CHECK_TEMPLATE_FORMAT,
    },
}

class LLMManager(QObject):
    stream_signal = Signal(str, str)  # tab_name, content

    def __init__(self):
        super().__init__()
        self.dialogue_speaker_lst = []
        self.dialogue_text_lst = []
        self.dialogue_history = []
        self.running = False

    def clear(self):
        self.dialogue_text_lst.clear()
        self.dialogue_history.clear()
        self.running = False

    def append(self, speaker, text):
        self.dialogue_speaker_lst.append(speaker)
        self.dialogue_text_lst.append(text)

    def __str__(self):
        import json
        return json.dumps({
            "speaker": self.dialogue_speaker_lst,
            "text": self.dialogue_text_lst
        }, ensure_ascii=False, indent=2)

    def run_task(self, tab_name: str, action: str):
        logger.info(f"LLM 任务: tab={tab_name}, action={action}")
        template = TEMPLATE_MAP.get(tab_name, {}).get(action)
        if not template:
            logger.warning(f"未找到对应模板: {tab_name} - {action}")
            return

        def runner():
            try:
                asyncio.run(self._chat_llm(tab_name, template))
            except Exception as e:
                logger.exception(f"异步任务执行失败: {e}")

        Thread(target=runner, daemon=True).start()

    async def _chat_llm(self, tab_name, template):
        if not BASE_URL or not  MODEL:
            logger.warning("LLM 配置不完整, 请检查设置")
            self.stream_signal.emit(tab_name, "未配置LLM, 请前往设置界面配置后重启应用")
            self.stream_signal.emit(tab_name, "<<END>>")
            return
        self.running = True

        try:
            print(API_KEY,BASE_URL,MODEL,self.dialogue_text_lst)
            headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json" }
            payload = {
                "model": MODEL,
                "messages": [{
                    "role": "user",
                    "content": template.format(dialogue="\n".join(self.dialogue_text_lst))
                }],
                "stream": True
            }

            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", BASE_URL, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: "):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                   
                                    self.stream_signal.emit(tab_name, delta)
                            except Exception as e:
                                logger.error(str(traceback.format_exc()))
                                logger.error(f"[error] {e} line={data}", flush=True)
            
        except Exception as e:
            
            logger.error(str(traceback.format_exc()))
            logger.exception(f"LLM 调用失败: {e}")
        finally:
            self.stream_signal.emit(tab_name, "<<END>>")
            self.running = False
