import os
from pathlib import Path
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
        required_dirs = ["iic", "pyannote", "libs"]
        folder_path = Path(folder)
        
        # 检查必要的子目录
        for dir_name in required_dirs:
            if not (folder_path / dir_name).exists():
                return False
        
        # 检查关键模型文件
        model_paths = [folder_path / "iic" / "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online" / "model.pt",
                       folder_path / "pyannote" / "embedding" / "pytorch_model.bin"]
        
        from utils.common import get_libopus_path
        if not os.path.exists(os.path.join(folder_path,get_libopus_path())):
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
        super().accept()
