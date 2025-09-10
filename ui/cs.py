CS = """
QWidget {
    background-color: #f5f5f5;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 14px;
    color: #333333;
}

QLabel {
    color: #333333;
}

QLineEdit, QTextEdit, QComboBox, QDateEdit {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #0078d7;
}

QTextBrowser {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px;
}

QPushButton {
    background-color: #e0e0e0;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QPushButton:pressed {
    background-color: #c0c0c0;
}

/* 蓝色主按钮，比如发送、启动麦克风 */
QPushButton#PrimaryButton {
    background-color: #0078d7;
    color: white;
}
QPushButton#PrimaryButton:hover {
    background-color: #005a9e;
}

/* 绿色按钮，比如保存病例 */
QPushButton#AccentButton {
    background-color: #2e8b57;
    color: white;
}
QPushButton#AccentButton:hover {
    background-color: #256f47;
}

/* 橙色按钮，比如暂停 */
QPushButton#PauseButton {
    background-color: #f39c12;
    color: white;
}
QPushButton#PauseButton:hover {
    background-color: #d68910;
}
QPushButton#PauseButton:pressed {
    background-color: #b9770e;
}

/* Tab 样式 */
QTabWidget::pane {
    border: 1px solid #dcdcdc;
    background: white;
}
QTabBar::tab {
    background: none;
    padding: 6px 12px;
}
QTabBar::tab:selected {
    font-weight: bold;
    border-bottom: 2px solid #0078d7;
    color: #0078d7;
}

"""
