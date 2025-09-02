from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTabWidget, QTextEdit
from loguru import logger
from PySide6.QtGui import QTextCursor
from case.llm import LLMManager
from ui.components.form_pane import FormPanel
import asyncio


class LLMPanel(QWidget):
    def __init__(self, llm_manager: LLMManager, form_panel: FormPanel):
        super().__init__()
        self.llm_manager = llm_manager
        self.form_panel = form_panel
        self.input_boxes = {}  
        self.tabs={}

        self.setup_ui()
        self.llm_manager.stream_signal.connect(self.print_stream)

    def setup_ui(self):
        layout = QVBoxLayout()

        

        # ---------- 下方 tab 输入区 ----------
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)  # 绑定切换事件

        tab_names = ["🩺 辅诊", "📋 病例", "💊 用药", "🧪 质检"]

        for name in tab_names:
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.setContentsMargins(3, 3, 3, 3)
            # ---------- 上方共用聊天框 ----------
            chat_box = QTextEdit()
            chat_box.setReadOnly(True)
            chat_box.setPlaceholderText("这里显示 AI 输出…")
            tab_layout.addWidget(chat_box)
            self.tabs[name]=chat_box

            input_bar = QHBoxLayout()

            input_box = QLineEdit()
            input_box.setPlaceholderText("请输入内容...")
            self.input_boxes[name]= input_box
            input_bar.addWidget(input_box)

            generate_btn = QPushButton("生成")
            generate_btn.setFixedSize(50, 30)
            generate_btn.clicked.connect(
                lambda checked=False, tab_name=name: self.send_and_generate(tab_name)
            )
            input_bar.addWidget(generate_btn)

            fill_btn = QPushButton("采用")
            fill_btn.setFixedSize(50, 30)
            fill_btn.clicked.connect(
                lambda checked=False, tab_name=name: self.fill_to_record(tab_name)
            )
            input_bar.addWidget(fill_btn)

            tab_layout.addLayout(input_bar)
            tab.setLayout(tab_layout)
            self.tab_widget.addTab(tab, name)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def send_and_generate(self, tab_name):
        """用户点击生成按钮"""
        user_text = self.input_boxes[tab_name].text().strip()
        if not user_text:
            return

        self.input_boxes[tab_name].clear()

        # 输出用户输入
        self.append_text(f"🧑‍⚕️ 医生: {user_text}\n")

        # 保存到 LLMManager
        self.llm_manager.append(tab_name, "user", user_text)

        # 异步调用 LLM
        asyncio.create_task(self.llm_manager.run_task_async(tab_name))

    def append_text(self, text: str):
        """往 chat_box 追加文本"""
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.chat_box.setTextCursor(cursor)
        self.chat_box.ensureCursorVisible()

    def print_stream(self, tab_name, text_piece):
        if text_piece == "<<START>>":
            logger.info("LLM 推理开始...")
            self.append_text("🤖 小助手: ")
            return
        if text_piece == "<<END>>":
            logger.info("LLM 推理结束")
            self.append_text("\n")
            return

        self.append_text(text_piece)

    def load_history_to_ui(self, tab_name: str):
        """切换病例或 tab 时，把历史对话刷到 UI"""
        self.chat_box.clear()
        history = self.llm_manager.dialogue_history
        for msg in history:
            speaker = "🧑‍⚕️ 医生" if msg["role"] == "user" else "🤖 小助手"
            self.append_text(f"{speaker}: {msg['content']}\n")

    def on_tab_changed(self, index: int):
       pass

    def fill_to_record(self, tab_name):
        """填充到病例"""
        content = self.chat_box.toPlainText()
        if tab_name == "🩺 辅诊":
            self.form_panel.diagnosis_text.setText(content)
        elif tab_name == "📋 病例":
            self.form_panel.complaint_text.setPlainText(content)
        # TODO: 其他 tab
        logger.info(f"已将[{tab_name}]内容填入病历")
