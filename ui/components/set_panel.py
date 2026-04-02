from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QLabel,
    QTabWidget, QWidget, QVBoxLayout, QComboBox, QCheckBox, QPushButton, QMessageBox,
    QDoubleSpinBox, QHBoxLayout, QFileDialog, QTextEdit
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, QThread, Signal, QMetaObject, Qt, QObject
from settings import cfg
import requests
import os
from pathlib import Path
import sys


class DownloadSignals(QObject):
    """下载信号，用于线程间通信"""
    log = Signal(str)
    finished = Signal(dict)
    error = Signal(str)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(480, 420)

        # 下载管理器
        from utils.model_downloader import DownloadManager
        self.download_manager = DownloadManager()

        # 信号对象
        self.download_signals = DownloadSignals()

        # 日志显示限制（最多显示 N 行）
        self.max_log_lines = 3
        self.current_logs = []

        # 连接信号到槽
        self.download_signals.log.connect(self._on_log_received)
        self.download_signals.finished.connect(self._on_download_complete)
        self.download_signals.error.connect(self._on_download_error)

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
        self.max_tokens_spinbox.setRange(100, 16384)
        self.max_tokens_spinbox.setValue(int(cfg.get("llm", "max_tokens", 2048)))
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
        self.asr_model_combo.addItem("请选择 ASR 模型")
        self.asr_model_combo.addItems(["vosk", "funasr"])

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
        self.resource_dir_edit.setMinimumWidth(200)

        # 资源目录布局
        resource_layout = QHBoxLayout()
        resource_layout.addWidget(self.resource_dir_edit)

        self.resource_browse_btn = QPushButton("浏览...")
        self.resource_browse_btn.clicked.connect(self.browse_resource_dir)
        resource_layout.addWidget(self.resource_browse_btn)

        self.resource_open_btn = QPushButton("打开")
        self.resource_open_btn.clicked.connect(lambda: self.open_folder(self.resource_dir_edit.text()))
        resource_layout.addWidget(self.resource_open_btn)

        path_layout.addRow("资源目录:", resource_layout)

        # 保存目录
        save_layout = QHBoxLayout()
        self.save_dir_edit = QLineEdit(cfg.get("app", "save_dir"))
        self.save_dir_edit.setPlaceholderText("保存目录路径")
        self.save_dir_edit.setMinimumWidth(200)

        self.save_browse_btn = QPushButton("浏览...")
        self.save_browse_btn.clicked.connect(self.browse_save_dir)

        self.save_open_btn = QPushButton("打开")
        self.save_open_btn.clicked.connect(lambda: self.open_folder(self.save_dir_edit.text()))

        save_layout.addWidget(self.save_dir_edit)
        save_layout.addWidget(self.save_browse_btn)
        save_layout.addWidget(self.save_open_btn)

        # 提示信息
        hint_label = QLabel(
            "• 资源目录：包含模型文件（iic、pyannote等）的文件夹\n"
            "• 保存目录：音频文件和病例库的保存位置\n"
            "• 模型文件不存在时会自动从 ModelScope 下载"
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 11px;")

        # 下载模型按钮布局
        download_layout = QHBoxLayout()

        self.download_models_btn = QPushButton("📥 下载模型")
        self.download_models_btn.clicked.connect(self.download_models_simple)
        self.download_models_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.download_status_label = QLabel("")
        self.download_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.download_status_label.setWordWrap(True)

        download_layout.addWidget(self.download_models_btn)
        download_layout.addWidget(self.download_status_label)

        path_layout.addRow("保存目录:", save_layout)
        path_layout.addRow(download_layout)
        path_layout.addRow(hint_label)

        tabs.addTab(path_tab, "模型")

        # -------- 主布局 --------
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)

        # 检查并恢复下载状态
        self._check_and_restore_download_state()

    def showEvent(self, event):
        """对话框显示时检查并恢复下载状态"""
        super().showEvent(event)
        self._check_and_restore_download_state()

    def _check_and_restore_download_state(self):
        """检查并恢复下载状态"""
        # 使用 QTimer 单次调用以确保 UI 已经完全构建
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._restore_download_ui)

    def _restore_download_ui(self):
        """恢复下载 UI 状态"""
        status = self.download_manager.get_status()

        if status['downloading']:
            # 如果正在下载，恢复日志并更新状态
            self.current_logs = status['logs']
            self._update_download_status()

            # 注册回调以继续接收日志（通过信号）
            self.download_manager.register_callback('log', lambda text: self.download_signals.log.emit(text))
            self.download_manager.register_callback('complete', lambda results: self.download_signals.finished.emit(results))
            self.download_manager.register_callback('error', lambda error: self.download_signals.error.emit(error))
        else:
            # 如果已完成，显示最后一个结果
            if status['logs']:
                self.current_logs = status['logs']
                self._update_download_status()

    def browse_resource_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择资源目录",
            self.resource_dir_edit.text() or str(Path.home())
        )
        if folder:
            self.resource_dir_edit.setText(folder)

    def browse_save_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择保存目录",
            self.save_dir_edit.text() or str(Path.home())
        )
        if folder:
            self.save_dir_edit.setText(folder)

    def download_models_simple(self):
        """简化的模型下载"""
        # 检查是否已有下载任务
        status = self.download_manager.get_status()
        if status['downloading']:
            QMessageBox.information(self, "下载中", "已有模型在下载中，请等待完成")
            return

        resource_dir = self.resource_dir_edit.text().strip()
        if not resource_dir:
            QMessageBox.warning(self, "提示", "请先设置资源目录路径")
            return

        # 获取当前选择的ASR模型
        current_asr = self.asr_model_combo.currentText()
        if current_asr in ["请选择 ASR 模型", ""]:
            QMessageBox.warning(self, "提示", "请先选择ASR模型")
            return

        # 检查模型是否已存在
        from utils.model_downloader import ModelDownloader
        downloader = ModelDownloader(resource_dir)

        missing_models = []
        models_to_download = []
        # 更新模型类型列表，包含新的声纹识别模型
        for model_type in [current_asr, 'spk', 'voiceprint']:
            if model_type in downloader.MODELS:  # 只下载支持的模型
                if not downloader.check_model_exists(model_type):
                    missing_models.append(model_type)
                    models_to_download.append(model_type)

        if not missing_models:
            QMessageBox.information(
                self, "模型已存在",
                "所有模型已存在，无需下载。\n\n如需重新下载，请先删除旧模型文件。"
            )
            return

        # 构建提示信息
        model_names = [downloader.MODELS[m]['name'] for m in missing_models]
        confirmed = QMessageBox.question(
            self, "确认下载",
            f"将下载以下模型:\n" + "\n".join(f"• {name}" for name in model_names) + "\n\n"
            "这可能需要较长时间和较大网络流量，确定继续？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes

        if not confirmed:
            return

        # 清空历史日志
        self.current_logs = []

        # 使用 DownloadManager 开始下载，通过信号回调
        self.download_manager.start_download(
            models=models_to_download,
            on_log=lambda text: self.download_signals.log.emit(text),
            on_complete=lambda results: self.download_signals.finished.emit(results),
            on_error=lambda error: self.download_signals.error.emit(error)
        )

        # 更新 UI 状态
        self._update_download_status()

    def _on_log_received(self, log_text):
        """在主线程中处理日志（通过信号）"""
        # 过滤一些无关的日志
        if any(keyword in log_text.lower() for keyword in ['[stderr]', 'downloaded', 'processing', '%|', 'it/s']):
            return

        # 只保留关键信息
        if log_text.startswith('✅') or log_text.startswith('❌') or log_text.startswith('⚠️') or '下载完成' in log_text:
            self.current_logs.append(log_text)
            # 保持最新的几行日志
            if len(self.current_logs) > self.max_log_lines:
                self.current_logs.pop(0)
            self._update_download_status()

    def _on_download_complete(self, results):
        """在主线程中处理完成（通过信号）"""
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count == total_count:
            self.current_logs.append("✅ 所有模型下载完成")
            self._update_download_status()
            QMessageBox.information(
                self, "下载完成",
                f"所有 {total_count} 个模型下载完成！\n\n请重启程序以使用新模型。"
            )
        else:
            failed_models = [name for name, success in results.items() if not success]
            self.current_logs.append(f"⚠️ 部分失败: {', '.join(failed_models)}")
            self._update_download_status()
            QMessageBox.warning(
                self, "下载部分失败",
                f"下载了 {success_count}/{total_count} 个模型，部分下载失败。\n"
                "请检查控制台日志中的错误信息。"
            )

    def _on_download_error(self, error_msg):
        """在主线程中处理错误（通过信号）"""
        self.current_logs.append(f"❌ 下载失败: {error_msg}")
        self._update_download_status()
        QMessageBox.critical(
            self, "下载失败",
            f"下载过程中发生错误:\n{error_msg}"
        )

    def _update_download_status(self):
        """更新下载状态显示"""
        status = self.download_manager.get_status()

        if status['downloading']:
            # 下载中
            self.download_models_btn.setEnabled(False)
            if self.current_logs:
                # 显示最新的日志
                status_text = f"⏳ 下载中:\n" + "\n".join(self.current_logs[-self.max_log_lines:])
                self.download_status_label.setText(status_text)
            else:
                self.download_status_label.setText("⏳ 正在下载模型...")
        else:
            # 未下载或已完成
            self.download_models_btn.setEnabled(True)
            if self.current_logs:
                last_log = self.current_logs[-1] if self.current_logs else ""
                if last_log.startswith('✅'):
                    self.download_status_label.setText(last_log)
                elif last_log.startswith('⚠️'):
                    self.download_status_label.setText(last_log + " (可重试)")
                elif last_log.startswith('❌'):
                    self.download_status_label.setText(last_log + " (可重试)")
            else:
                self.download_status_label.setText("")

    def open_folder(self, folder_path):
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "提示", "文件夹不存在")
            return

        try:
            if os.name == 'nt':
                os.startfile(folder_path)
            elif os.name == 'posix':
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {e}")

    def test_connection(self):
        api_base = self.api_base_edit.text().strip()
        api_key = self.api_key_edit.text().strip()

        if not api_base:
            QMessageBox.warning(self, "提示", "请输入API Base地址")
            return

        try:
            response = requests.get(
                f"{api_base}/models",
                headers={'Authorization': f'Bearer {api_key}' if api_key else {}},
                timeout=5
            )
            if response.status_code == 200:
                QMessageBox.information(self, "成功", "连接成功 ✅")
            else:
                QMessageBox.critical(self, "失败", f"连接失败，状态码: {response.status_code}")
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

        # 保存 ASR 配置
        asr_model = self.asr_model_combo.currentText()
        if asr_model != "请选择 ASR 模型":
            cfg.set("asr", "model", asr_model)
        cfg.set("llm", "mcp", self.mcp_checkbox.isChecked())
        cfg.set("asr", "denoise", self.denoise_checkbox.isChecked())

        cfg.set("process", "audio_queue_size", self.audio_queue_spin.value())
        cfg.set("process", "text_queue_size", self.text_queue_spin.value())
        # 保存路径
        resource_dir = self.resource_dir_edit.text()
        save_dir = self.save_dir_edit.text()

        if resource_dir:
            cfg.set("app", "resource_dir", resource_dir)
        if save_dir:
            cfg.set("app", "save_dir", save_dir)

        super().accept()
