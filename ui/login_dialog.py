import os
import json
import base64
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QLabel, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt
from pathlib import Path

# 获取用户主目录

home = os.environ.get("VETVOICE_PATH",Path.home())
vetvoice_folder =os.path.join(home,".vetvoice") 
# 创建文件夹
os.makedirs(vetvoice_folder, exist_ok=True)

USER_PATH = os.path.join(vetvoice_folder,"user.json") 

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户登录")
        self.setFixedSize(400, 380)
        
        self.resource_dir = ""
        self.save_dir=""
        self.user_data = self.load_user_data()
        self.setup_ui()
        self.prefill_last_login()

    def setup_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.remember_checkbox = QCheckBox("记住我")

        form.addRow("用户名：", self.username_input)
        form.addRow("密码：", self.password_input)
        form.addRow("", self.remember_checkbox)
        
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


        btn_layout = QVBoxLayout()
        self.login_btn = QPushButton("登录")
        self.register_btn = QPushButton("注册")
        self.login_btn.clicked.connect(self.handle_login)
        self.register_btn.clicked.connect(self.handle_register)
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.login_btn.setDefault(True)

    def load_user_data(self):

        if not os.path.exists(USER_PATH):
            return {"users": {}, "last_login": {}, "resource_path": "","save_path": ""}
        with open(USER_PATH, "r") as f:
            return json.load(f)

    def save_user_data(self):
        if not self.user_data:
            return
        with open(USER_PATH, "w") as f:
            json.dump(self.user_data, f, indent=2, ensure_ascii=False)

    def prefill_last_login(self):
        last = self.user_data.get("last_login", {})
        if last.get("remember"):
            username = last.get("username", "")
            self.username_input.setText(username)
            user_info = self.user_data["users"].get(username, {})
            if "password" in user_info:
                try:
                    password = base64.b64decode(user_info["password"]).decode()
                    self.password_input.setText(password)
                except Exception:
                    pass
            self.remember_checkbox.setChecked(True)
        
        # 填充上次使用的资源路径
        resource_path = self.user_data.get("resource_path", "")
        if resource_path and os.path.exists(resource_path):
            self.resource_input.setText(resource_path)
            self.resource_dir = resource_path
        save_path = self.user_data.get("save_path", "")
        if save_path and os.path.exists(save_path):
            self.save_input.setText(save_path)
            self.save_dir = save_path
    
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
        model_path = folder_path / "iic" / "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online" / "model.pt"
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

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        resource_path = self.resource_input.text().strip()
        save_path = self.save_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "错误", "请输入用户名和密码")
            return
        
        # 检查资源路径
        if not resource_path:
            QMessageBox.warning(self, "错误", "请选择资源文件夹路径")
            return
        # 检查资源路径
        if not save_path:
            QMessageBox.warning(self, "错误", "请选择病例保存文件夹路径")
            return
        
        if not self.validate_resource_folder(resource_path):
            QMessageBox.warning(self, "错误", "资源文件夹无效，请重新选择")
            return

        user_info = self.user_data["users"].get(username)
        if not user_info:
            QMessageBox.warning(self, "错误", "用户不存在，请注册")
            return

        stored_pw = user_info["password"]
        if base64.b64encode(password.encode()).decode() != stored_pw:
            QMessageBox.warning(self, "错误", "密码错误")
            return

        # 登录成功，保存资源路径
        self.resource_dir = resource_path
        self.save_dir=save_path
        self.user_data["resource_path"] = resource_path
        self.user_data["save_path"] = save_path
        self.save_user_data()
        
        # 设置环境变量，供程序使用
        # os.environ["VETVOICE_RESOURCES"] = resource_path
        # os.environ["SAVE_PATH"] = save_path
        
        if self.remember_checkbox.isChecked():
            self.user_data["last_login"] = {"username": username, "remember": True}
        else:
            self.user_data["last_login"] = {"username": "", "remember": False}

        self.save_user_data()
        self.accept()

    def handle_register(self):
        reg_dialog = RegisterDialog(self)
        if reg_dialog.exec() == QDialog.Accepted:
            # 获取注册返回信息
            username, name, password = reg_dialog.get_info()

            if username in self.user_data["users"]:
                QMessageBox.warning(self, "错误", "用户名已存在")
                return

            self.user_data["users"][username] = {
                "name": name,
                "password": base64.b64encode(password.encode()).decode()
            }
            self.save_user_data()
            QMessageBox.information(self, "注册成功", f"欢迎 {name}，请登录")

    def get_username(self):
        return self.username_input.text().strip()
    
    def get_user_info(self):
        username = self.username_input.text().strip()
        name = self.user_data["users"][username]["name"]
        return {"username": username, "name": name}
    
    def get_path(self):
        return self.resource_dir ,self.save_dir


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户注册")
        self.setFixedSize(300, 180)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.name_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form.addRow("用户名：", self.username_input)
        form.addRow("姓名：", self.name_input)
        form.addRow("密码：", self.password_input)

        layout.addLayout(form)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn)

        self.setLayout(layout)

    def get_info(self):
        return (
            self.username_input.text().strip(),
            self.name_input.text().strip(),
            self.password_input.text().strip()
        )
