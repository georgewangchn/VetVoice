from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QGridLayout,QHBoxLayout
)
from PySide6.QtCore import Qt

class BTPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    def setup_ui(self):
        bt_layout = QHBoxLayout()
        bt_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.mic_start = QPushButton("🎤 启动")
        self.mic_stop = QPushButton("⏸️ 暂停")
        self.save_pdf = QPushButton("📄.PDF")
        self.save_case = QPushButton("💾保存")
        
        self.mic_start.setEnabled(True)
        self.mic_stop.setEnabled(False)
        
        bt_layout.addWidget(self.mic_start)
        bt_layout.addWidget(self.mic_stop)
 
        bt_layout.addWidget(self.save_case)
        
        bt_layout.addWidget(self.save_pdf)
        bt_layout.addStretch(1)
        self.setLayout(bt_layout)