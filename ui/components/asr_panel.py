from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QComboBox
from PySide6.QtCore import Qt
from ui.waveview import WaveformWidget
import sounddevice as sd
from settings import cfg
from PySide6.QtCore import Qt, QTimer,QEvent
from loguru import logger
import json
import case.llm
class ASRPanel(QWidget):
    def __init__(self, audio_receive,text_queue,llm_manager:case.llm.LLMManager):
        super().__init__()
        self.audio_receive = audio_receive
        self.text_queue = text_queue
        self.llm_manager=llm_manager
        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_text_queue)
        self.timer.start(200)  
        self.speaker_colors = {}  # 存储每个 speaker 的颜色
        self.default_colors = [
            "#1E90FF", "#FF4500", "#008000", "#800080", "#FF1493",
            "#2E8B57", "#8B0000", "#4682B4", "#DAA520", "#A52A2A"
        ]
        self.unknown_color = "#808080"  # unknown 统一灰色
        self.color_index = 0
        
        QTimer.singleShot(100, self.populate_device_list)

    def setup_ui(self):
        layout = QVBoxLayout()

        # 波形图
        self.wave_widget = WaveformWidget(self.audio_receive)
        self.wave_widget.setFixedSize(200, 40)
        self.wave_widget.setStyleSheet("background-color: #1e1e1e;")
        self.wave_widget.setContentsMargins(0, 0, 0, 0)

        # 输入输出设备下拉框
        device_widget = QWidget()
        device_widget.setFixedWidth(300)
        device_widget.setContentsMargins(0, 0, 0, 0)
        device_layout = QHBoxLayout()
        self.input_device = QComboBox()
        self.output_device = QComboBox()
        device_layout.addWidget(QLabel("音频输入"))
        device_layout.addWidget(self.input_device)
        # device_layout.addStretch(1)  # 让设备选择控件贴顶，下面空开
        # device_layout.addWidget(self.output_device)
        device_widget.setLayout(device_layout)

        # 合并波形图 + 设备选择
        view_widget = QWidget()
        view_widget.setFixedHeight(55)
        view_layout = QHBoxLayout()
        view_layout.setAlignment(Qt.AlignVCenter)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.addWidget(self.wave_widget)
        view_layout.addWidget(device_widget)
        view_widget.setLayout(view_layout)

        layout.addWidget(view_widget)

        # 对话内容
        layout.addWidget(QLabel("对话内容："))
        self.text_browser = QTextBrowser()
        self.text_browser.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.text_browser)

        self.setLayout(layout)

    def populate_device_list(self):
        self.input_device.clear()
        self.output_device.clear()
        devices = sd.query_devices()

        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                display_name = f"{idx}: {dev['name']}"
                self.input_device.addItem(display_name, userData=idx)
            if dev['max_output_channels'] > 0:
                display_name = f"{idx}: {dev['name']}"
                self.output_device.addItem(display_name, userData=idx)

        selected_input_device = cfg.get("input_device", "index")
        selected_output_device = cfg.get("output_device", "index")

        if self.input_device.count() > 0:
            if selected_input_device and selected_input_device < self.input_device.count():
                self.input_device.setCurrentIndex(selected_input_device)
            else:
                self.input_device.setCurrentIndex(self.input_device.count() - 1)

        if self.output_device.count() > 0:
            if selected_output_device and selected_output_device < self.output_device.count():
                self.output_device.setCurrentIndex(selected_output_device)
            else:
                self.output_device.setCurrentIndex(self.output_device.count() - 1)
    def poll_text_queue(self):
        try:
            while not self.text_queue.empty():
                item = self.text_queue.get_nowait()
                # 假设 item 是 JSON 字符串，如 {"speaker": "A", "text": "你好"}
                if isinstance(item, str):
                    try:
                        data = json.loads(item)
                        speaker = data.get("speaker", "unkonw")
                        text = data.get("text", "")
                    except Exception:
                        # 如果不是 JSON，就统一用 A 说话
                        speaker = "unkonw"
                        text = item
                else:
                    speaker = "unkonw"
                    text = str(item)

                self.append_dialogue(speaker, text)
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            logger.warning(f"文本队列读取出错: {e}")
    def append_dialogue(self, speaker, text):
        if speaker.lower() == "unknown" or speaker.lower() == "unkonw":
            color = self.unknown_color
        else:
            # 新 speaker 分配一个颜色
            if speaker not in self.speaker_colors:
                color = self.default_colors[self.color_index % len(self.default_colors)]
                self.speaker_colors[speaker] = color
                self.color_index += 1
            else:
                color = self.speaker_colors[speaker]
        html = f"""
                <div style="color:{color}; margin:1px; font-size:13px; line-height:1.1;">
                    <b>{speaker}：</b>{text}
                </div>
                """
        self.text_browser.append(html)
        self.text_browser.verticalScrollBar().setValue(self.text_browser.verticalScrollBar().maximum())
        self.llm_manager.append(speaker,text)
    def reset_waveform(self):
        self.wave_widget.reset_waveform()

    def append_text(self, html):
        self.text_browser.append(html)
        self.text_browser.verticalScrollBar().setValue(self.text_browser.verticalScrollBar().maximum())