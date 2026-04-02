import os
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QLabel, QHBoxLayout, QFileDialog
)

from pathlib import Path

class PathDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置模型路径")
        self.setFixedSize(500, 200)
        
        self.resource_dir = ""
        self.save_dir=""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()
        # 添加资源路径选择
        resource_layout = QHBoxLayout()
        self.resource_input = QLineEdit()
        self.resource_input.setPlaceholderText("请选择资源文件夹路径...")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_resource_folder)
        resource_layout.addWidget(self.resource_input)
        resource_layout.addWidget(self.browse_btn)
        
        form.addRow("资源路径：", resource_layout)
        
        #病例保存目录
        save_layout = QHBoxLayout()
        self.save_input = QLineEdit()
        self.save_input.setPlaceholderText("请选择病例保存文件夹路径...")
        self.save_input_btn = QPushButton("浏览...")
        self.save_input_btn.clicked.connect(self.browse_save_folder)
        save_layout.addWidget(self.save_input)
        save_layout.addWidget(self.save_input_btn)
        
        form.addRow("数据保存路径：", save_layout)
        
        layout.addLayout(form)
        # 添加提示信息
        hint_label = QLabel("资源路径:请下载resources.zip并解压，然后选择解压后的文件夹\n数据保存路径:音频文件/病例库保存的文件夹")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def browse_resource_folder(self):
        """浏览选择资源文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "选择资源文件夹", 
            self.resource_input.text() or os.path.expanduser("~")
        )
        if folder:
            # 验证是否是有效的资源文件夹
            if self.validate_resource_folder(folder):
                self.resource_input.setText(folder)
                self.resource_dir = folder
            else:
                QMessageBox.warning(
                    self, 
                    "无效的资源文件夹",
                    "所选文件夹不包含必要的资源文件。\n"
                    "请确保选择解压后的resources文件夹，\n"
                    "其中应包含iic、pyannote、libs等子目录。"
                )
    
    
    def validate_resource_folder(self, folder):
        """验证资源文件夹是否有效"""
        # 去掉libs检查，libs在工程目录中
        required_dirs = ["iic", "pyannote"]
        folder_path = Path(folder)

        # 检查必要的子目录
        for dir_name in required_dirs:
            if not (folder_path / dir_name).exists():
                return False

        # 检查关键模型文件
        model_paths = [folder_path / "iic" / "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online" / "model.pt",
                       folder_path / "pyannote" / "embedding" / "pytorch_model.bin"]

        # 检查工程目录中的libs是否存在
        from utils.resource_path import get_project_root
        project_libs = get_project_root() / "libs"
        if not project_libs.exists():
            return False

        for model_path in model_paths:
            if not model_path.exists():
                return False

        return True
    def browse_save_folder(self):
        """浏览选择资源文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "选择保存文件夹", 
            self.save_input.text() or os.path.expanduser("~")
        )
        if folder:
            # 验证是否是有效的资源文件夹
            if os.path.exists(folder):
                self.save_input.setText(folder)
                self.save_dir = folder
            else:
                QMessageBox.warning(
                    self, 
                    "文件夹不存在"
                )

    def accept(self):
        if not self.resource_dir:
            QMessageBox.warning(self, "提示", "请设置资源路径")
            return
        if not self.save_dir:
            QMessageBox.warning(self, "提示", "请设置保存路径")
            return
        from settings import cfg
        cfg.set("app", "resource_dir", self.resource_dir)
        cfg.set("app", "save_dir", self.save_dir)

        # 检查模型是否存在
        try:
            from utils.model_downloader import ModelDownloader
            downloader = ModelDownloader(self.resource_dir)
            model_status = downloader.check_all_models()

            missing_models = [name for name, exists in model_status.items() if not exists]

            if missing_models:
                missing_names = ", ".join([downloader.MODELS[name]['name'] for name in missing_models])
                reply = QMessageBox.question(
                    self,
                    "模型检查",
                    f"资源路径已设置，但缺少以下模型:\n{missing_names}\n\n"
                    f"是否从 ModelScope 自动下载？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    from PySide6.QtWidgets import QProgressDialog, QDialog

                    # 创建进度对话框
                    progress_dialog = QProgressDialog(self)
                    progress_dialog.setWindowTitle("模型下载")
                    progress_dialog.setLabelText(f"正在下载 {len(missing_models)} 个模型...")
                    progress_dialog.setRange(0, 0)
                    progress_dialog.setCancelButton(None)
                    progress_dialog.show()

                    # 在后台执行下载（简单同步方式）
                    try:
                        results = downloader.download_missing_models(missing_models)
                        progress_dialog.close()

                        success_count = sum(1 for success in results.values() if success)
                        if success_count == len(results):
                            QMessageBox.information(
                                self, "下载完成",
                                "所有模型下载完成！\n配置已保存。"
                            )
                        else:
                            QMessageBox.warning(
                                self, "下载部分失败",
                                f"成功下载 {success_count}/{len(results)} 个模型。\n"
                                f"配置已保存，但可能功能受限。"
                            )
                    except Exception as e:
                        progress_dialog.close()
                        QMessageBox.warning(
                            self, "下载失败",
                            f"模型下载失败: {str(e)}\n"
                            f"配置已保存，请稍后手动下载模型。"
                        )

        except Exception as e:
            logger.warning(f"模型检查失败: {e}")
            # 即使模型检查失败也允许继续

        super().accept()
