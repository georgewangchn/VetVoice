from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QTabWidget
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
        self.tabs = {}  # 存储每个 tab 的 QTextEdit
        self.setup_ui()
        self.llm_manager.stream_signal.connect(self.print_stream)

    def setup_ui(self):
        layout = QVBoxLayout()

        # ---------- 上方共用聊天框 ----------
        layout.addWidget(self.chat_list, stretch=1)

        # ---------- 下方 tab 输入区 ----------
        self.tab_widget = QTabWidget()
        tab_names = ["🩺 辅诊", "📋 病例", "💊 用药", "🧪 质检"]

        for name in tab_names:
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.setContentsMargins(3, 3, 3, 3)

            # 输入 + 按钮区域
            input_bar = QHBoxLayout()

            input_box = QLineEdit()
            input_box.setPlaceholderText("请输入内容...")
            self.input_boxes[name] = input_box
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

    def print_stream(self, tab_name, text_piece):
        if text_piece == "<<START>>":
            logger.info("LLM 推理开始...")
            self.tabs[tab_name].clear()
            text_piece=""
        if text_piece == "<<END>>":
            self.current_ai_bubble = None
            return
        if tab_name not in self.tabs:
            return
        cursor = self.tabs[tab_name].textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text_piece)
        self.tabs[tab_name].setTextCursor(cursor)
        self.tabs[tab_name].ensureCursorVisible()
        
    def fill_to_record(self, tab_name):
        """填充到病例"""
        # 这里你可以直接取最后一条 AI 消息
        if self.current_ai_bubble:
            content = self.current_ai_bubble.label.text()
        else:
            return

        if tab_name == "🩺 辅诊":
            self.form_panel.diagnosis_text.setText(content)
        elif tab_name == "📋 病例":
            self.form_panel.complaint_text.setPlainText(content)
        # TODO: 其他 tab
        logger.info(f"已将[{tab_name}]内容填入病历")
