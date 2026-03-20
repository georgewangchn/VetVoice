from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTabWidget, QTextEdit, QLabel
from loguru import logger
from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtCore import QTimer, Qt
from case.llm import LLMManager
from ui.components.form_pane import FormPanel
import asyncio
import json
from settings import cfg

class LLMPanel(QWidget):
    def __init__(self, llm_manager: LLMManager, form_panel: FormPanel):
        super().__init__()
        self.llm_manager = llm_manager
        self.form_panel = form_panel
        self.input_boxes = {}
        self.tabs={}
        self.loading_labels = {}
        self.loading_animations = {}
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.setup_ui()
        self.llm_manager.stream_signal.connect(self.print_stream)

    def setup_ui(self):
        # 清空旧内容
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.input_boxes.clear()
        self.tabs.clear()

        # ---------- 下方 tab 输入区 ----------
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("PrimaryButton")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)  # 绑定切换事件

        if cfg.get("llm","mcp"):
            tab_names = [ "🩺️️️ 1-问诊阶段","🔬 2-检查阶段", "📊 3-报告阶段", "💊 4-治疗阶段"]
            default_input_texts =[
            "填充电子病历",
            "推荐开具检查项",
            "填充检查结果",
            "确诊并开处方",
            ]
        else:
            tab_names=["📋 一键电子病历"]
            default_input_texts =["填充电子病历"]

        for default_input_text,name in zip(default_input_texts,tab_names):
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.setContentsMargins(3, 3, 3, 3)
            # ---------- 上方共用聊天框 ----------
            chat_box = QTextEdit()
            chat_box.setReadOnly(True)
            chat_box.setPlaceholderText("这里显示 AI 输出…")
            tab_layout.addWidget(chat_box)
            self.tabs[name]=chat_box

            # 思考中...加载动画
            loading_label = QLabel("🤔 思考中...")
            loading_label.setAlignment(Qt.AlignCenter)
            loading_label.setStyleSheet("font-weight: bold; color: #007bff;")
            loading_label.hide()
            tab_layout.addWidget(loading_label)
            self.loading_labels[name] = loading_label

            input_bar = QHBoxLayout()
            input_box = QLineEdit()
            input_box.setText(default_input_text)
            self.input_boxes[name]= input_box
            input_bar.addWidget(input_box)

            generate_btn = QPushButton("智能体")
            generate_btn.setObjectName("PrimaryButton")
            generate_btn.setFixedSize(100, 30)
            generate_btn.clicked.connect(
                lambda checked=False, tab_name=name: self.send_and_generate(tab_name)
            )
            input_bar.addWidget(generate_btn)

            # fill_btn = QPushButton("采用")
            # fill_btn.setFixedSize(50, 30)
            # fill_btn.clicked.connect(
            #     lambda checked=False, tab_name=name: self.fill_to_record(tab_name)
            # )
            # input_bar.addWidget(fill_btn)

            tab_layout.addLayout(input_bar)
            tab.setLayout(tab_layout)
            self.tab_widget.addTab(tab, name)

        self.layout.addWidget(self.tab_widget)

    def send_and_generate(self, tab_name):
        """用户点击生成按钮"""
        user_text = self.input_boxes[tab_name].text().strip()
        if not user_text:
            return

        self.input_boxes[tab_name].clear()
        self.input_boxes[tab_name].setText("重新生成:")

        # 输出用户输入
        self.append_text(tab_name,f"🧑‍⚕️ 医生: {user_text}\n")

        # 保存到 LLMManager
        self.llm_manager.append("user", user_text)

        # 异步调用 LLM
        capture_case_snapshot = self.form_panel.capture_case_snapshot()
        asyncio.create_task(self.llm_manager.run_task_async(tab_name,capture_case_snapshot,self.input_boxes[tab_name].text()))

    def append_text(self,tab_name:str, text: str):
        """往 chat_box 追加文本"""
        cursor = self.tabs[tab_name].textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.tabs[tab_name].setTextCursor(cursor)
        self.tabs[tab_name].ensureCursorVisible()

    def print_stream(self, tab_name, text_piece):
        if text_piece == "<<START>>":
            logger.info("LLM 推理开始...")
            self.append_text(tab_name,"🤖 小助手: ")
            # 显示"思考中..."加载动画
            self.start_loading_animation(tab_name)
            return
        if text_piece == "<<END>>":
            logger.info("LLM 推理结束")
            self.append_text(tab_name,"\n")
            # 隐藏"思考中..."加载动画
            self.stop_loading_animation(tab_name)
            self.fill_to_record(tab_name)
            return

        self.append_text(tab_name,text_piece)

    def start_loading_animation(self, tab_name):
        """启动"思考中..."加载动画"""
        if tab_name in self.loading_labels:
            self.loading_labels[tab_name].show()
            # 创建旋转动画
            self.loading_animations[tab_name] = QTimer(self)
            self.loading_animations[tab_name].timeout.connect(
                lambda: self.update_loading_text(tab_name)
            )
            self.loading_animations[tab_name].start(500)  # 每 500ms 更新一次

    def stop_loading_animation(self, tab_name):
        """停止"思考中..."加载动画"""
        if tab_name in self.loading_labels:
            self.loading_labels[tab_name].hide()
        if tab_name in self.loading_animations:
            self.loading_animations[tab_name].stop()
            del self.loading_animations[tab_name]

    def update_loading_text(self, tab_name):
        """更新"思考中..."文本"""
        if tab_name not in self.loading_labels:
            return

        loading_texts = ["🤔 思考中...", "💭 分析中...", "🔍 查找数据...", "✍️ 生成中...", "🤔 思考中..."]
        current_text = self.loading_labels[tab_name].text()
        try:
            current_index = loading_texts.index(current_text)
            next_index = (current_index + 1) % len(loading_texts)
        except ValueError:
            next_index = 0
        self.loading_labels[tab_name].setText(loading_texts[next_index])

    def on_tab_changed(self, index: int):
        # 切换 tab 时，隐藏所有加载动画
        for tab_name in self.loading_labels:
            self.stop_loading_animation(tab_name)

    def fill_to_record(self, tab_name):
        print("llm mcp:")
        print(type(cfg.get("llm","mcp")))
        print(cfg.get("llm","mcp"))
        if cfg.get("llm","mcp"):
            self.fill_to_record_mcp()
        else:
            self.fill_to_record_not_mcp(tab_name)
    def fill_to_record_mcp(self):
        data = self.llm_manager.buffer_case
        logger.debug(f"fill_to_record_mcp={data}")
        if data and len(data)>0:
            logger.debug("\nmcp 获取病历："+str(data))
        try:
                    if "name" in data and  data["name"]:
                        self.form_panel.name_input.setText(data["name"])
                    if "phone" in data and  data["phone"]:
                        self.form_panel.phone_input.setText(data["phone"])
                    if "pet_name" in data and  data["pet_name"]:
                        self.form_panel.pet_name_input.setText(data["pet_name"])
                    if "species" in data and  data["species"]:
                        self.form_panel.species_select.setCurrentText(data["species"])
                    if "breed" in data and  data["breed"]:
                        self.form_panel.breed_select.setCurrentText(data["breed"])
                    if "weight" in data and  data["weight"]:
                        self.form_panel.weight_input.setText(data["weight"])
                    if "deworming" in data and  data["deworming"]:
                        self.form_panel.deworming_select.setCurrentText(data["deworming"])
                    if "sterilization" in data and  data["sterilization"]:
                        self.form_panel.sterilization_select.setCurrentText(data["sterilization"])

                    if "complaint" in data and  data["complaint"]:
                        self.form_panel.complaint_text.setPlainText(data["complaint"])
                    if "checkup" in data and  data["checkup"]:
                        self.form_panel.checkup_text.setPlainText(data["checkup"])
                    if "results" in data and  data["results"]:
                        self.form_panel.results_text.setPlainText(data["results"])
                    if "treatment" in data and  data["treatment"]:
                        self.form_panel.treatment_text.setPlainText(data["treatment"])
        except Exception as e:
            logger.error(str(e))

    def fill_to_record_not_mcp(self, tab_name):
        """填充到病例"""
        buffer_stream = self.llm_manager.buffer_stream
        try:
                logger.debug("buffer_stream:\n"+buffer_stream)
                import re
                pattern = r"```json\s*(.*?)\s*```"
                match = re.search(pattern, buffer_stream, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()  # 提取 json 部分并去除首尾空格
                    logger.debug("json_str:\n"+json_str)
                    data = json.loads(json_str)
                    logger.debug("\n解析为 Python 字典成功："+str(data))

                    if "name" in data and  data["name"]:
                        self.form_panel.name_input.setText(data["name"])
                    if "phone" in data and  data["phone"]:
                        self.form_panel.phone_input.setText(data["phone"])
                    if "pet_name" in data and  data["pet_name"]:
                        self.form_panel.pet_name_input.setText(data["pet_name"])
                    if "species" in data and  data["species"]:
                        self.form_panel.species_select.setCurrentText(data["species"])
                    if "breed" in data and  data["breed"]:
                        self.form_panel.breed_select.setCurrentText(data["breed"])
                    if "weight" in data and  data["weight"]:
                        self.form_panel.weight_input.setText(data["weight"])
                    if "deworming" in data and  data["deworming"]:
                        self.form_panel.deworming_select.setCurrentText(data["deworming"])
                    if "sterilization" in data and  data["sterilization"]:
                        self.form_panel.sterilization_select.setCurrentText(data["sterilization"])

                    if "complaint" in data and  data["complaint"]:
                        self.form_panel.complaint_text.setPlainText(data["complaint"])
                    if "checkup" in data and  data["checkup"]:
                        self.form_panel.checkup_text.setPlainText(data["checkup"])
                    if "results" in data and  data["results"]:
                        self.form_panel.results_text.setPlainText(data["results"])
                    if "treatment" in data and  data["treatment"]:
                        self.form_panel.treatment_text.setPlainText(data["treatment"])
        except json.JSONDecodeError as e:
                print("JSON 解析出错：", e)
                self.input_boxes[tab_name].setText(f"JSON 解析出错：{str(e)},重新生成：")
        logger.info(f"已将内容填入病历")
