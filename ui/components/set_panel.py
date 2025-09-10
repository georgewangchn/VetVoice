from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QLabel,
    QTabWidget, QWidget, QVBoxLayout, QComboBox, QCheckBox, QPushButton, QMessageBox, QDoubleSpinBox
)
from settings import cfg
import requests


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(480, 420)

        # Tab 控件
        tabs = QTabWidget(self)

        # -------- Tab1: 大模型 --------
        llm_tab = QWidget()
        llm_layout = QFormLayout(llm_tab)
        
  

        self.api_key_edit = QLineEdit(cfg.get("llm", "api_key", ""))
        self.api_key_edit.setPlaceholderText("大模型api_key: EMPTY")
        self.api_key_edit.setMinimumWidth(250)

        self.api_base_edit = QLineEdit(cfg.get("llm", "api_base", ""))
        self.api_base_edit.setPlaceholderText("大模型地址api_base: http://127.0.0.1:8000/v1")
        self.api_base_edit.setMinimumWidth(250)

        self.model_edit = QLineEdit(cfg.get("llm", "model", ""))
        self.model_edit.setPlaceholderText("大模型名model: Qwen3-235B-A22B")
        self.model_edit.setMinimumWidth(250)
        self.temperature_spinbox = QDoubleSpinBox()
        self.temperature_spinbox.setRange(0.0, 2.0)  # 温度范围
        self.temperature_spinbox.setDecimals(1)     # 保留1位小数
        self.temperature_spinbox.setSingleStep(0.1)  # 步长
        self.temperature_spinbox.setValue(float(cfg.get("llm", "temperature", 0.1)))  
        self.temperature_spinbox.setMaximumWidth(100)

        # ===== 新增：max_tokens 参数 =====
        # 最大生成 token 数，int，常用范围例如 [100 ~ 16384]
        self.max_tokens_spinbox = QSpinBox()
        self.max_tokens_spinbox.setRange(100, 16384)  # 设置合理的范围
        self.max_tokens_spinbox.setValue(int(cfg.get("llm", "max_tokens", 2048)))  # 默认1024
        self.max_tokens_spinbox.setMaximumWidth(100)
        
        self.thinking_checkbox = QCheckBox("启用<think>思考模式")
        self.thinking_checkbox.setChecked(cfg.get("llm", "think", False))

        self.test_btn = QPushButton("连接测试")
        self.test_btn.clicked.connect(self.test_connection)
        

        
        llm_layout.addRow("API Key:", self.api_key_edit)
        llm_layout.addRow("API Base:", self.api_base_edit)
        llm_layout.addRow("模型名:", self.model_edit)
        llm_layout.addRow("生成温度 (0.0-2.0):", self.temperature_spinbox)
        llm_layout.addRow("最大生成 Tokens:", self.max_tokens_spinbox)
        llm_layout.addRow(self.thinking_checkbox)
        llm_layout.addRow(self.test_btn)
        llm_layout.addWidget(QLabel("* 支持openai形式接口\n* 请确保大模型服务可用后再进行连接测试"))


        tabs.addTab(llm_tab, "大模型")
        
        # ----------table mcp--------------
        mcp_tab = QWidget()
        mcp_layout=QFormLayout(mcp_tab)
        self.mcp_checkbox = QCheckBox("启用MCP模式")
        self.mcp_checkbox.setChecked(cfg.get("llm", "mcp", False))
        mcp_layout.addWidget(self.mcp_checkbox)
        mcp_layout.addWidget(QLabel("* 重启程序才能生效"))
        tabs.addTab(mcp_tab, "MCP")
        
        
        # -------- Tab2: ASR --------
        asr_tab = QWidget()
        asr_layout = QFormLayout(asr_tab)

        self.asr_model_combo = QComboBox()
        self.asr_model_combo.addItem("请选择 ASR 模型")  # 占位符
        self.asr_model_combo.addItems(["vosk", "funasr"])

        # 默认选中 cfg.get 或 funasr
        default_asr = cfg.get("asr", "model", "funasr")
        idx = self.asr_model_combo.findText(default_asr)
        if idx != -1:
            self.asr_model_combo.setCurrentIndex(idx)
        else:
            self.asr_model_combo.setCurrentIndex(0)

        self.denoise_checkbox = QCheckBox("启用降噪")
        self.denoise_checkbox.setChecked(cfg.get("asr", "denoise", True))

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

        tabs.addTab(process_tab, "性能参数")
        
        # -------- Tab4: 资源路径 --------
        path_tab = QWidget()
        path_layout = QFormLayout(path_tab)

        self.resource_dir_edit = QLineEdit(cfg.get("app", "resource_dir"))
        self.resource_dir_edit.setPlaceholderText("资源目录路径")
        self.resource_dir_edit.setMinimumWidth(300)

        self.save_dir_edit = QLineEdit(cfg.get("app", "save_dir"))
        self.save_dir_edit.setPlaceholderText("保存目录路径")
        self.save_dir_edit.setMinimumWidth(300)

        path_layout.addRow("资源目录 resource_dir:", self.resource_dir_edit)
        path_layout.addRow("保存目录 save_dir:", self.save_dir_edit)

        tabs.addTab(path_tab, "资源路径")

        # -------- 主布局 --------
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)
        
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
                    "max_tokens": 5,
                    "stream": False
                },
                timeout=5
            )
            if resp.status_code == 200:
                QMessageBox.information(self, "成功", "连接成功 ✅")
            else:
                QMessageBox.critical(self, "失败", f"连接失败，状态码: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接出错: {e}")

    def accept(self):
    

        # 保存配置
        cfg.set("llm", "api_key", self.api_key_edit.text())
        cfg.set("llm", "api_base", self.api_base_edit.text())
        cfg.set("llm", "model", self.model_edit.text())
        cfg.set("llm", "temperature", self.temperature_spinbox.value())
        cfg.set("llm", "max_tokens", self.max_tokens_spinbox.value())
        cfg.set("llm", "think", self.thinking_checkbox.isChecked())
        asr_model = self.asr_model_combo.currentText()
        if asr_model != "请选择 ASR 模型":
            cfg.set("asr", "model", asr_model)
        cfg.set("llm", "mcp", self.mcp_checkbox.isChecked())
        cfg.set("asr", "denoise", self.denoise_checkbox.isChecked())

        cfg.set("process", "audio_queue_size", self.audio_queue_spin.value())
        cfg.set("process", "text_queue_size", self.text_queue_spin.value())
        # 保存路径
        cfg.set("app", "resource_dir", self.resource_dir_edit.text())
        cfg.set("app", "save_dir", self.save_dir_edit.text())

        super().accept()
