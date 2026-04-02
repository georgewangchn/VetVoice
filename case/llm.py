from PySide6.QtCore import QObject, Signal
from settings import cfg
from loguru import logger
import json
import traceback
import httpx
from case.template import *
from fastmcp import Client
import copy
from agent.client import run_orchestrator


TAB_STAGE = {"🩺️️️ 1-问诊阶段":"问诊阶段","🔬 2-检查阶段":"开检查阶段", "📊 3-报告阶段":"查看检查结果阶段", "💊 4-治疗阶段":"确诊治疗阶段"}
class LLMManager(QObject):
    stream_signal = Signal(str, str) 
    
    def __init__(self):
        super().__init__()
        self.asr_speaker_lst = []
        self.dialogue_history = []
        self.running = False
        self.buffer_stream = ""
        self.buffer_case={}


    def clear(self):
        self.asr_speaker_lst.clear()
        self.dialogue_history.clear()
        self.running = False

    def append(self, speaker, text):
       self.asr_speaker_lst.append((speaker, text))

    def __str__(self):
        import json
        return json.dumps(self.asr_speaker_lst, ensure_ascii=False, indent=2)
    async def run_task_async(self, tab_name: str,case_snapshot:dict,command:str):
        BASE_URL = cfg.get("llm", "api_base").strip()
        MODEL = cfg.get("llm", "model").strip()

        if not BASE_URL or not MODEL:
                self.stream_signal.emit(tab_name, "<<START>>")
                self.stream_signal.emit(tab_name, "未配置LLM，请进入【设置】【参数】【大模型】配置\n")
                self.stream_signal.emit(tab_name, "<<END>>")
                return
        content ='\n'.join([ str(tup)  for tup in self.asr_speaker_lst]) 
        if not self.asr_speaker_lst or len(content)<30:
                self.stream_signal.emit(tab_name, "<<START>>")
                self.stream_signal.emit(tab_name, "无对话内容/<30字\n")
                self.stream_signal.emit(tab_name, "<<END>>")
                return
        if cfg.get("llm","mcp"):
            await self.run_mcp(tab_name,case_snapshot)
        else:
            await self.run_llm(tab_name,case_snapshot,command)
    async def run_mcp(self, tab_name: str,case_snapshot:dict):
        params=copy.deepcopy(case_snapshot)
        dialogue ='\n'.join([ str(tup)  for tup in self.asr_speaker_lst]) 
        logger.debug(dialogue)
        logger.debug(params)
        self.buffer_case={}
        self. stream_signal.emit(tab_name, "<<START>>")
        self.buffer_case=await run_orchestrator(params,dialogue,self.stream_signal,tab_name)
        self.stream_signal.emit(tab_name, f"<<END>>")

    async def run_llm(self, tab_name: str, case_snapshot:dict,command:str):

        """异步调用 LLM 接口"""
        logger.info(f"LLM 任务: tab={tab_name}")
        API_KEY = cfg.get("llm", "api_key").strip()
        BASE_URL = cfg.get("llm", "api_base").strip()
        BASE_URL = f"{BASE_URL}/chat/completions" if "chat/completions" not in BASE_URL else BASE_URL
        MODEL = cfg.get("llm", "model").strip()

        try:
            self.running = True
            self.stream_signal.emit(tab_name, "<<START>>")
            timeout = httpx.Timeout(60.0, read=120.0)
            
            params=copy.deepcopy(case_snapshot)
            content ='\n'.join([ str(tup)  for tup in self.asr_speaker_lst]) 
            params["dialogue"]=content
            params["command"]=command
            self.buffer_stream=""
            logger.debug(str(TEMPLATE_MAP.get(tab_name).format(**params)))
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    BASE_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_KEY}" if API_KEY else None,
                    },
                    json={
                        "model": MODEL,
                        "messages": [
                            {"role": "user","content": TEMPLATE_MAP.get(tab_name).format(**params)}
                            ],
                        "max_tokens": int(cfg.get("llm", "max_tokens", 2048)),
                        "temperature": float(cfg.get("llm", "temperature", 0.1)),
                        "stream": True,
                        "extra_body": {
                            "chat_template_kwargs": {
                                "enable_thinking": cfg.get("llm", "think", False)
                            }
                        },
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
                                self.buffer_stream+=delta
                        except Exception as e:
                            logger.error(f"解析失败 line={data} err={e}")

        except Exception as e:
            logger.error(traceback.format_exc())
            self.stream_signal.emit(tab_name, f"LLM 调用失败: {e}")
        finally:
            self.stream_signal.emit(tab_name, "<<END>>")
            self.running = False
