from PySide6.QtCore import QObject, Signal
from settings import cfg
from loguru import logger
import json
from case.template import *
import traceback
import httpx
TEMPLATE_MAP = {
    "🩺 辅诊": {
        "生成": DIAGNOSE_TEMPLATE,
        "格式": DIAGNOSE_TEMPLATE_FORMAT,
    },
    "📋 病例": {
        "生成": COMPLAINT_TEMPLATE,
        "格式": COMPLAINT_TEMPLATE_FORMAT,
    },
    "💊 用药": {
        "生成": MEDICATION_TEMPLATE,
        "格式": MEDICATION_TEMPLATE_FORMAT,
    },
    "🧪 质检": {
        "生成": QUALITY_CHECK_TEMPLATE,
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
    async def run_task_async(self, tab_name: str, action: str):
        """异步调用 LLM 接口"""
        logger.info(f"LLM 任务: tab={tab_name}, action={action}")
        template = TEMPLATE_MAP.get(tab_name, {}).get(action)
        if not template:
            logger.warning(f"未找到对应模板: {tab_name} - {action}")
            return

        try:
            API_KEY = cfg.get("llm", "api_key").strip()
            BASE_URL = cfg.get("llm", "api_base").strip()
            BASE_URL = f"{BASE_URL}/chat/completions" if "chat/completions" not in BASE_URL else BASE_URL
            MODEL = cfg.get("llm", "model").strip()

            if not BASE_URL or not MODEL :
                self.stream_signal.emit(tab_name, "<<START>>")
                self.stream_signal.emit(tab_name, "未配置LLM，请进入【设置】【全局【大模型】配置\n")
                self.stream_signal.emit(tab_name, "<<END>>")
                return
            if not self.dialogue_text_lst:
                self.stream_signal.emit(tab_name, "<<START>>")
                self.stream_signal.emit(tab_name, "无对话内容\n")
                self.stream_signal.emit(tab_name, "<<END>>")
                return

            self.running = True
            self.stream_signal.emit(tab_name, "<<START>>")
            timeout = httpx.Timeout(60.0, read=120.0) 

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    BASE_URL,
                    headers={"Content-Type": "application/json",
                            #  "Authorization": f"Bearer {API_KEY}"
                             },
                    json={
                        "model": MODEL,
                        "messages": [{
                            "role": "user",
                            "content": template.format(dialogue="\n".join(self.dialogue_text_lst))
                        }],
                        "max_tokens": int(cfg.get("llm", "max_tokens", 2048)),
                        "temperature": float(cfg.get("llm", "temperature", 0.1)),
                        "stream": True,
                        "extra_body": {"chat_template_kwargs": {"enable_thinking": cfg.get("llm", "thinking",False)}},
                    }
                ) as response:
                    response.raise_for_status() 

                    if response.status_code != 200:
                        logger.error(f"LLM 请求失败: {response.status_code} {await response.aread()}")
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: "):].strip()
                        else:
                            data = line.strip()

                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                self.stream_signal.emit(tab_name, delta)
                        except Exception as e:
                            logger.error(f"解析失败 line={data} err={e}")

        except Exception as e:
            logger.error(traceback.format_exc())
            self.stream_signal.emit(tab_name, f"LLM 调用失败: {e}")
        finally:
            self.stream_signal.emit(tab_name, "<<END>>")
            self.running = False
    def run_task(self, tab_name: str, action: str):
        logger.info(f"LLM 任务: tab={tab_name}, action={action}")
        template = TEMPLATE_MAP.get(tab_name, {}).get(action)
        if not template:
            logger.warning(f"未找到对应模板: {tab_name} - {action}")
            return
        
        try:
            API_KEY=cfg.get("llm", "api_key").strip()
            BASE_URL=cfg.get("llm", "api_base").strip()
            BASE_URL =f'{BASE_URL}/chat/completions' if "chat/completions" not in BASE_URL else BASE_URL
            MODEL=cfg.get("llm", "model").strip()
            print(API_KEY,BASE_URL,MODEL,self.dialogue_text_lst)
            if not BASE_URL or not  MODEL or not  self.dialogue_text_lst:
                logger.warning("未配置LLM or 无对话内容")
                self.stream_signal.emit(tab_name, "未配置LLM or 无对话内容")
                self.stream_signal.emit(tab_name, "<<END>>")
                return                
            ###
            import requests
            
            ###
            self.running = True
            self.stream_signal.emit(tab_name, "<<START>>")
            response = requests.post(
                BASE_URL,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL,
                    "messages": [{
                        "role": "user",
                        "content": template.format(dialogue="\n".join(self.dialogue_text_lst))
                    }],
                    "max_tokens": 2048,
                    "stream": True,
                    "extra_body":{"chat_template_kwargs": {"enable_thinking": False}},

                },
                stream=True  # ✅ 关键
            )

            if response.status_code != 200:
                logger.error(f"LLM 请求失败: {response.status_code} {response.text}")
                return

            for line in response.iter_lines(decode_unicode=True,chunk_size=1):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[len("data: "):].strip()
                else:
                    data = line.strip()

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        self.stream_signal.emit(tab_name, delta)

                except Exception as e:
                    logger.error(f"解析失败 line={data} err={e}")
            
        except Exception as e:
            
            logger.error(traceback.format_exc())
            logger.exception(f"LLM 调用失败: {e}")
        finally:
            self.stream_signal.emit(tab_name, "<<END>>")
            self.running = False
