from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QTabWidget
from loguru import logger
from PySide6.QtGui import QTextCursor
from diagnosis.llm import LLMManager
from ui.components.form_pane import FormPanel
class LLMPanel(QWidget):
    def __init__(self, llm_manager: LLMManager,form_panel: FormPanel):
        super().__init__()
        self.llm = llm_manager
        self.form_panel = form_panel
        self.tabs = {}  # 存储每个 tab 的 QTextEdit
        self.setup_ui()
        self.llm.stream_signal.connect(self.print_stream)

    def setup_ui(self):
        layout = QVBoxLayout()

        # ---------- Tab 区域 ----------
        self.tab_widget = QTabWidget()
        tab_names = ["🩺 辅诊", "📋 主诉", "📇 基本信息", "💊 用药", "🧪 质检"]

        for name in tab_names:
            tab = QWidget()
            tab_layout = QHBoxLayout()
            tab_layout.setContentsMargins(0.5, 0.5, 0.5, 0)
            # 输出区域
            output_box = QTextEdit()
            output_box.setPlaceholderText("这里显示 AI 输出…")
            tab_layout.addWidget(output_box)
            tab.setLayout(tab_layout)

            self.tabs[name] = output_box
            self.tab_widget.addTab(tab, name)
            # llm交互按钮区域
            llm_button_bar = QVBoxLayout()
            llm_button_bar.setSpacing(3)  # 减少按钮之间的垂直间距
            llm_button_bar.setContentsMargins(0, 0, 0, 0)  # 移除按钮区域的外边距
            generate_btn = QPushButton("生成")
            rewrite_btn  = QPushButton("修饰")
            format_btn   = QPushButton("格式")
            fill_btn     = QPushButton("采用")
            # 设置按钮固定大小
            for btn in [generate_btn, rewrite_btn, format_btn, fill_btn]:
                btn.setFixedSize(40, 30)

            for btn, action in zip(
                [generate_btn, rewrite_btn, format_btn],
                ["生成", "修饰", "格式"]
            ):
                btn.clicked.connect(lambda checked=False, t=action, tab_name=name: self.llm.run_task(tab_name, t))
                llm_button_bar.addWidget(btn)
            fill_btn.clicked.connect(lambda checked=False, tab_name=name: self.fill_to_record(tab_name))
            llm_button_bar.addWidget(fill_btn)

            tab_layout.addLayout(llm_button_bar)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def print_stream(self, tab_name, text_piece):
        if text_piece == "<<END>>":
            logger.info("LLM 推理结束")
            return
        if tab_name not in self.tabs:
            return
        cursor = self.tabs[tab_name].textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text_piece)
        self.tabs[tab_name].setTextCursor(cursor)
        self.tabs[tab_name].ensureCursorVisible()
        
    def fill_to_record(self, tab_name):
        """将当前标签页内容填充到病历中"""
        content = self.tabs[tab_name].toPlainText()
        
        # 根据不同的标签页执行不同的填充操作
        if tab_name == "🩺 辅诊":
            self.form_panel.diagnosis_text.setText(content)
        elif tab_name == "📋 主诉":
            self.form_panel.complaint_text.setPlainText(content)
        elif tab_name == "📇 基本信息":
            pass
        elif tab_name == "💊 用药":
            pass
            # self.fill_medication(content)
        elif tab_name == "🧪 质检":
            pass
            #self.fill_quality_check(content)
        
        logger.info(f"已将[{tab_name}]内容填入病历")

        