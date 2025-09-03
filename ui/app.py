# -*- coding: utf-8 -*-

import sys
import json
import datetime
from loguru import logger
from settings import cfg
import time
from PySide6.QtWidgets import (QMenuBar,QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,QMessageBox)
from PySide6.QtCore import QEvent
from PySide6.QtGui import QIcon
import case.llm
import case.sql_manage
import json
import os
import ui.components.llm_panel
import ui.components.asr_panel
import ui.components.form_pane
import ui.components.bt_panel
import ui.components.set_panel
class VoiceApp(QWidget):
    def __init__(self,kwargs):
        super().__init__()
        self.setWindowTitle("VetVoice-兽医声动|智能语音电子病历")
        self.setWindowIcon(QIcon("app.ico"))
        self.resize(1400, 900)
        #
        self.start_event = kwargs['start_event']
        self.stop_event = kwargs['stop_event']
        self.audio_queue = kwargs['audio_queue']
        self.text_queue = kwargs['text_queue']
        self.audio_receive= kwargs['audio_receive']
        self.llm_manager = case.llm.LLMManager()
        #ui
        self.setup_ui()
    def setup_ui(self):
        # ---------- 病例表单区域 ----------
        self.form_panel = ui.components.form_pane.FormPanel(self.llm_manager)
        self.form_panel.case_selector.currentIndexChanged.connect(self.case_selected)
       
        self.form_panel.case_selector.installEventFilter(self)
        # ---------- 右侧 BT + ASR + LLM 区域 ----------
        self.bt_panel= ui.components.bt_panel.BTPanel()
        self.asr_panel=ui.components.asr_panel.ASRPanel(self.audio_receive,self.text_queue,self.llm_manager)
        self.llm_panel = ui.components.llm_panel.LLMPanel(self.llm_manager,self.form_panel)
        
        asr_layout = QVBoxLayout()
        asr_layout.addWidget(self.bt_panel)        
        asr_layout.addWidget(self.asr_panel)
        asr_layout.addWidget(self.llm_panel)

        # ---------- 汇总主区域 ----------
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.form_panel, 1)  
        center_layout.addLayout(asr_layout, 1)  
        app_layout = QVBoxLayout()
        app_layout.addLayout(center_layout)
        self.setLayout(app_layout)

        # ---------- 汇总绑定主区域 ----------
        self.bt_panel.mic_start.clicked.connect(self.start_recording)
        self.bt_panel.mic_stop.clicked.connect(self.stop_recording)
        self.bt_panel.save_pdf.clicked.connect(self.save2pdf)
        self.bt_panel.save_case.clicked.connect(self.form_panel.save)
        self.asr_panel.input_device.currentIndexChanged.connect(lambda: cfg.set("input_device", "index", self.asr_panel.input_device.currentData()))
        self.asr_panel.output_device.currentIndexChanged.connect(lambda: cfg.set("output_device", "index", self.asr_panel.output_device.currentData()))
        self.form_panel.new_case.clicked.connect(self.case_input)
        
        
        # 添加右上角用户信息与退出按钮
        user_name = cfg.get("history", "now_login")
        name = json.loads(cfg.get("users", user_name))["name"] if user_name else "未知用户"
        self.user_label = QLabel(f"👤 {name}", self)
        self.logout_btn = QPushButton("退出登录", self)
        self.logout_btn.setFixedHeight(24)
        self.logout_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")

        # 设置为绝对位置（右上角）
        self.user_label.move(self.width() - 100, 10)
        self.logout_btn.move(self.width() - 50, 10)

        # 保证随窗口缩放调整位置
        self.resizeEvent = self._on_resize

        # 绑定
        self.logout_btn.clicked.connect(self.logout_clicked)
        
        #菜单
        menu_bar = QMenuBar(self)
        # menu_bar.setNativeMenuBar(False)

        # 设置菜单
        settings_menu = menu_bar.addMenu("设置")
        action_settings = settings_menu.addAction("全局")
        action_settings.triggered.connect(self.open_settings_dialog)

        # 关于菜单
        about_menu = menu_bar.addMenu("帮助")
        action_about = about_menu.addAction("关于")
        action_about.triggered.connect(self.show_about_dialog)

        # 将菜单栏添加到布局（在最上方）
        self.layout().setMenuBar(menu_bar)
        
    def closeEvent(self, event):
        if not self.form_panel.case_id.text().strip():
            event.accept()
            return
        if not self.form_panel.is_case_modified():
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "确认退出",
            "当前病例未保存，是否要保存？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.form_panel.save()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()
    def eventFilter(self, obj, event):
        def _load_case_list():
            date_str = self.form_panel.date_edit.date().toString("yyyyMMdd")
            cases = case.sql_manage.CaseManager.get_case_by_date(date_str)
            self.form_panel.case_selector.clear()
            self.form_panel.case_selector.addItems(cases)
        if obj == self.form_panel.case_selector and event.type() == QEvent.MouseButtonPress:
            _load_case_list()
        return super().eventFilter(obj, event)
    
    def logout_clicked(self):
        reply = QMessageBox.question(
            self,
            "确认退出登录",
            "确定要退出当前用户并返回登录界面？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()  # 或者执行其他切换逻辑
    def del_case_clicked(self):
        case_id = self.form_panel.case_id.text()
        if not case_id:
            return
        if case_id in self.form_panel.case_selector.currentText():
            self.form_panel.case_selector.removeItem(self.form_panel.case_selector.currentIndex())
        self.form_panel.delete()
    def case_selected(self, index):
        if index < 0:
            return
        self.asr_panel.text_browser.clear()
        dialogue = self.form_panel.load(index)
        if dialogue:
            json_data = json.loads(dialogue)
            
            for speaker, text in json_data:
                self.asr_panel.append_dialogue(speaker, text)
        self.form_panel.update_case_snapshot()
        
    def case_input(self):
        self.form_panel.new()

    def start_recording(self):
        if not self.form_panel.case_id.text().strip():
            self.case_input()
        device = self.asr_panel.input_device.currentData()
        logger.info(f"Using input device {device}")
        while self.start_event.is_set():
            logger.warning("⏳ 上一轮还未清理完，等待中...")
            time.sleep(0.1)
        self.start_event.set()
        # 更新按钮状态
        self.bt_panel.mic_start.setEnabled(False)
        self.bt_panel.mic_stop.setEnabled(True)
        self.bt_panel.mic_stop.setStyleSheet("""
                                                QPushButton {
                                                    border: 1px solid red;          /* 红色边框 */
                                                    padding: 3px;                   /* 增加内边距，让内容区域缩小 */
                                                }
                                                QPushButton:hover {
                                                    border: 2px solid darkred;      /* 鼠标悬停时深红色边框 */
                                                    padding: 2px;                   /* 悬停时内边距更小，边框看起来更粗 */
                                                }
                                            """)
        self.form_panel.date_edit.setEnabled(False)
        self.form_panel.case_selector.setEnabled(False)
        self.form_panel.new_case.setEnabled(False)
        self.form_panel.del_case.setEnabled(False)

    def stop_recording(self):
        self.stop_event.set()
        # 更新按钮状态
        # self.asr_panel.reset_waveform()
        self.bt_panel.mic_start.setEnabled(True)
        self.bt_panel.mic_stop.setEnabled(False)
        self.bt_panel.mic_stop.setStyleSheet("")
        self.form_panel.date_edit.setEnabled(True)
        self.form_panel.case_selector.setEnabled(True)
        self.form_panel.new_case.setEnabled(True)
        self.form_panel.del_case.setEnabled(True)
    def save2pdf(self):
        
        os.makedirs(cfg.get("app", "save_dir"), exist_ok=False)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    def _on_resize(self, event):
        self.user_label.move(self.width() - 100, 10)
        self.logout_btn.move(self.width() - 50, 10)
    def open_settings_dialog(self):
        dialog = ui.components.set_panel.SettingsDialog(self)
        dialog.exec()
    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "关于 VetVoice",
            "VetVoice 兽医声动\n智能语音电子病历系统\n版本 1.0.0",
            "https://github.com/georgewangchn/VetVoice",
            "联系方式 aigeorge@qq.com"
            
        )