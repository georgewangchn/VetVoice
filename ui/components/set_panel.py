from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QMenuBar, QLabel
)
from settings import cfg

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(400, 350)

        layout = QFormLayout(self)

        # LLM 配置
        self.api_key_edit = QLineEdit(cfg.get("llm", "api_key", ""))
        self.api_key_edit.setPlaceholderText("LLM API Key:EMPTY")
        self.api_key_edit.setMinimumWidth(250)

        self.api_base_edit = QLineEdit(cfg.get("llm", "api_base", ""))
        self.api_base_edit.setPlaceholderText("LLM URL:http://127.0.0.1:8000/v1")
        self.api_base_edit.setMinimumWidth(250)
        self.model_edit = QLineEdit(cfg.get("llm", "model", ""))
        self.model_edit.setPlaceholderText("LLM Model:Qwen3-235B-A22B")
        self.api_base_edit.setMinimumWidth(250)
        

        layout.addRow("LLM API Key:", self.api_key_edit)
        layout.addRow("LLM API Base:", self.api_base_edit)
        layout.addRow("LLM 模型:", self.model_edit)

        # Process 配置
        self.audio_queue_spin = QSpinBox()
        self.audio_queue_spin.setRange(1, 10000)
        self.audio_queue_spin.setValue(cfg.get("process", "audio_queue_size", 100))

        self.text_queue_spin = QSpinBox()
        self.text_queue_spin.setRange(1, 10000)
        self.text_queue_spin.setValue(cfg.get("process", "text_queue_size", 100))

        layout.addRow("音频队列大小:", self.audio_queue_spin)
        layout.addRow("文本队列大小:", self.text_queue_spin)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        layout.addRow(QLabel("* 修改后需重启应用生效！！！"))

    def accept(self):
        # 保存配置
        cfg.set("llm", "api_key", self.api_key_edit.text())
        cfg.set("llm", "api_base", self.api_base_edit.text())
        cfg.set("llm", "model", self.model_edit.text())

        cfg.set("process", "audio_queue_size", self.audio_queue_spin.value())
        cfg.set("process", "text_queue_size", self.text_queue_spin.value())
        cfg.save()

        super().accept()

