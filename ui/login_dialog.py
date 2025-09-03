import os
import json
import base64
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from pathlib import Path
from settings import cfg
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
        self.setFixedSize(400, 280)
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
        layout.addLayout(form)
        # 添加提示信息
        
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
        last_login = cfg.get("history", "last_login")
        if not last_login:
            return None,None
        psw = cfg.get("users", "last_login")
        return last_login,psw
        

    def save_user_data(self):
        if not self.user_data:
            return
        with open(USER_PATH, "w") as f:
            json.dump(self.user_data, f, indent=2, ensure_ascii=False)

    def prefill_last_login(self):
        last_login = cfg.get("history", "last_login")
        psw = json.loads(cfg.get("users", last_login) )['password'] if last_login else None
        if last_login and psw :
            self.username_input.setText(last_login)
            password = base64.b64decode(psw).decode()
            self.password_input.setText(password)
            self.remember_checkbox.setChecked(True)
        
       
    
    

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "错误", "请输入用户名和密码")
            return

        vs = cfg.get("users", username)
        if not vs:
            QMessageBox.warning(self, "错误", "用户不存在")
            return

        try:
            user_data = json.loads(vs)  # 解析存储的 JSON
        except Exception:
            QMessageBox.warning(self, "错误", "用户数据损坏")
            return

        stored_pw = user_data.get("password")
        if base64.b64encode(password.encode()).decode() != stored_pw:
            QMessageBox.warning(self, "错误", "密码错误")
            return

        if self.remember_checkbox.isChecked():
            cfg.set("history", "last_login", username)
        else:
            cfg.set("history", "last_login", None)

        cfg.set("history", "now_login", username)
        self.accept()

    def handle_register(self):
        reg_dialog = RegisterDialog(self)
        if reg_dialog.exec() == QDialog.Accepted:
            # 获取注册返回信息
            username, name, password = reg_dialog.get_info()

            if cfg.get("users", username):
                QMessageBox.warning(self, "错误", "用户名已存在")
                return
            
            cfg.set("users", username, json.dumps({"name": name, "password": base64.b64encode(password.encode()).decode()}, ensure_ascii=False))
            
            QMessageBox.information(self, "注册成功", f"欢迎 {name}，请登录")

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
