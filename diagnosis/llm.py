from PySide6.QtCore import QObject, Signal
from threading import Thread
from openai import OpenAI
from settings import cfg
from loguru import logger
from diagnosis.template import *
API_KEY=cfg.get("llm", "api_key").strip()
BASE_URL=cfg.get("llm", "api_base").strip()
MODEL=cfg.get("llm", "model").strip()
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
        Thread(target=self._chat_llm, args=(tab_name, template)).start()

    def _chat_llm(self, tab_name, template):
        if not BASE_URL or not  MODEL:
            logger.warning("LLM 配置不完整, 请检查设置")
            self.stream_signal.emit(tab_name, "未配置LLM, 请前往设置界面配置后重启应用")
            self.stream_signal.emit(tab_name, "<<END>>")
            return
        self.running = True
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        print(API_KEY,BASE_URL,MODEL,self.dialogue_text_lst)

        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=[{
                    "role": "user",
                    "content": template.format(dialogue="\n".join(self.dialogue_text_lst))
                }],
                # extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                stream=True
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    self.stream_signal.emit(tab_name, chunk.choices[0].delta.content)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            logger.exception(f"LLM 调用失败: {e}")
        finally:
            self.stream_signal.emit(tab_name, "<<END>>")
            self.running = False
