from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QLabel,
    QTabWidget, QWidget, QVBoxLayout, QComboBox, QCheckBox, QPushButton, QMessageBox
)
from settings import cfg
import requests


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(480, 420)

        self.test_passed = False  # 是否通过连接测试

        # Tab 控件
        tabs = QTabWidget(self)

        # -------- Tab1: 大模型 --------
        llm_tab = QWidget()
        llm_layout = QFormLayout(llm_tab)

        self.api_key_edit = QLineEdit(cfg.get("llm", "api_key", ""))
        self.api_key_edit.setPlaceholderText("LLM API Key: EMPTY")
        self.api_key_edit.setMinimumWidth(250)

        self.api_base_edit = QLineEdit(cfg.get("llm", "api_base", ""))
        self.api_base_edit.setPlaceholderText("LLM URL: http://127.0.0.1:8000/v1")
        self.api_base_edit.setMinimumWidth(250)

        self.model_edit = QLineEdit(cfg.get("llm", "model", ""))
        self.model_edit.setPlaceholderText("LLM Model: Qwen3-235B-A22B")
        self.model_edit.setMinimumWidth(250)

        self.test_btn = QPushButton("连接测试")
        self.test_btn.clicked.connect(self.test_connection)

        llm_layout.addRow("LLM API Key:", self.api_key_edit)
        llm_layout.addRow("LLM API Base:", self.api_base_edit)
        llm_layout.addRow("LLM 模型:", self.model_edit)
        llm_layout.addRow(self.test_btn)

        tabs.addTab(llm_tab, "大模型")

        # -------- Tab2: ASR --------
        asr_tab = QWidget()
        asr_layout = QFormLayout(asr_tab)

        self.asr_model_combo = QComboBox()
        self.asr_model_combo.addItem("请选择 ASR 模型")  # 占位符
        self.asr_model_combo.addItems(["fosk", "funasr"])

        # 默认选中 cfg.get 或 funasr
        default_asr = cfg.get("asr", "model", "funasr")
        idx = self.asr_model_combo.findText(default_asr)
        if idx != -1:
            self.asr_model_combo.setCurrentIndex(idx)
        else:
            self.asr_model_combo.setCurrentIndex(0)

        self.denoise_checkbox = QCheckBox("启用降噪")
        self.denoise_checkbox.setChecked(cfg.get("asr", "denoise", False))

        asr_layout.addRow("ASR 模型选择:", self.asr_model_combo)
        asr_layout.addRow(self.denoise_checkbox)

        tabs.addTab(asr_tab, "语音识别")

        # -------- Process 配置 --------
        process_tab = QWidget()
        process_layout = QFormLayout(process_tab)

        self.audio_queue_spin = QSpinBox()
        self.audio_queue_spin.setRange(1, 10000)
        self.audio_queue_spin.setValue(cfg.get("process", "audio_queue_size", 100))

        self.text_queue_spin = QSpinBox()
        self.text_queue_spin.setRange(1, 10000)
        self.text_queue_spin.setValue(cfg.get("process", "text_queue_size", 100))

        process_layout.addRow("音频队列大小:", self.audio_queue_spin)
        process_layout.addRow("文本队列大小:", self.text_queue_spin)

        tabs.addTab(process_tab, "进程参数")

        # -------- 主布局 --------
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)
        main_layout.addWidget(QLabel("* 修改后需重启应用生效！！！"))

    def test_connection(self):
        """测试大模型连接"""
        url = self.api_base_edit.text().strip()
        model = self.model_edit.text().strip()
        api_key = self.api_key_edit.text().strip() or "EMPTY"

        if not url or not model:
            QMessageBox.warning(self, "提示", "请填写 API Base 和 模型名称")
            return

        try:
            resp = requests.post(
                f"{url}/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "你好"}],
                    "max_tokens": 5
                },
                timeout=5
            )
            if resp.status_code == 200:
                self.test_passed = True
                QMessageBox.information(self, "成功", "连接成功 ✅")
            else:
                self.test_passed = False
                QMessageBox.critical(self, "失败", f"连接失败，状态码: {resp.status_code}")
        except Exception as e:
            self.test_passed = False
            QMessageBox.critical(self, "错误", f"连接出错: {e}")

    def accept(self):
        # 只有连接测试通过才能保存
        if not self.test_passed:
            QMessageBox.warning(self, "提示", "请先点击【连接测试】，并确保连接成功！")
            return

        # 保存配置
        cfg.set("llm", "api_key", self.api_key_edit.text())
        cfg.set("llm", "api_base", self.api_base_edit.text())
        cfg.set("llm", "model", self.model_edit.text())

        asr_model = self.asr_model_combo.currentText()
        if asr_model != "请选择 ASR 模型":
            cfg.set("asr", "model", asr_model)
        cfg.set("asr", "denoise", self.denoise_checkbox.isChecked())

        cfg.set("process", "audio_queue_size", self.audio_queue_spin.value())
        cfg.set("process", "text_queue_size", self.text_queue_spin.value())
        cfg.save()

        super().accept()
