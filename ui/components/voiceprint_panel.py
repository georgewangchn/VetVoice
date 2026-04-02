# -*- coding: utf-8 -*-
"""
声纹管理面板
提供医生声纹的录入和删除功能
"""
import os
import json
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget, QInputDialog
)
from PySide6.QtCore import QThread, Signal, Qt
from settings import cfg
from utils.resource_path import get_resource_path


class RecordThread(QThread):
    """录音线程"""
    finished = Signal(np.ndarray)  # 录音完成信号，返回音频数据
    error = Signal(str)  # 错误信号

    def __init__(self, sample_rate=16000, duration=3):
        super().__init__()
        self.sample_rate = sample_rate
        self.duration = duration
        self.recording = False

    def run(self):
        try:
            import sounddevice as sd

            # 开始录音
            recording = sd.rec(
                int(self.sample_rate * self.duration),
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()

            # 转换为numpy数组
            audio_data = recording.flatten().astype(np.float32) / 32768.0

            self.finished.emit(audio_data)

        except Exception as e:
            self.error.emit(str(e))


class VoiceprintPanel(QDialog):
    """声纹管理面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("声纹管理")
        self.resize(500, 400)

        # 声纹存储目录
        self.voiceprint_dir = Path.home() / ".vetvoice" / "voiceprints"
        self.voiceprint_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.voiceprint_dir / "metadata.json"

        # 声纹识别模型路径（使用 get_resource_path 转换为绝对路径）
        self.model_path = get_resource_path(cfg.get("spk", "voiceprint_path"))

        # 录音线程
        self.record_thread = None

        # 加载元数据
        self.metadata = {}
        self.load_metadata()

        self.setup_ui()

    def load_metadata(self):
        """加载声纹元数据"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)

                # 兼容旧格式的数据结构
                for doctor_name, doctor_info in self.metadata.items():
                    if not isinstance(doctor_info, dict):
                        continue

                    # 检查是否是旧格式（直接包含 file_path）
                    if 'file_path' in doctor_info and 'voiceprints' not in doctor_info:
                        # 转换旧格式为新格式
                        old_voiceprints = [{
                            'id': 1,
                            'file_path': doctor_info['file_path'],
                            'created_time': doctor_info.get('created_at', doctor_info.get('created_time', '未知'))
                        }]

                        self.metadata[doctor_name] = {
                            'voiceprints': old_voiceprints,
                            'created_time': doctor_info.get('created_at', doctor_info.get('created_time', '未知'))
                        }
                        logger.info(f"转换旧格式声纹数据: {doctor_name}")

            else:
                self.metadata = {}

            logger.info(f"📋 加载了 {len(self.metadata)} 个医生的声纹元数据")
        except Exception as e:
            logger.error(f"加载元数据失败: {e}")
            self.metadata = {}

    def save_metadata(self):
        """保存声纹元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            logger.info("💾 声纹元数据已保存")
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()

        # Tab控件
        self.tab_widget = QTabWidget()

        # 页面1: 新增声纹
        self.add_tab = self.create_add_tab()
        self.tab_widget.addTab(self.add_tab, "新增")

        # 页面2: 删除声纹
        self.delete_tab = self.create_delete_tab()
        self.tab_widget.addTab(self.delete_tab, "删除")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def create_add_tab(self):
        """创建新增声纹tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 姓名输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("医生姓名："))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入医生姓名")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 录音按钮
        self.record_btn = QPushButton("🎤 点击录音（自动3秒）")
        self.record_btn.clicked.connect(self.start_recording)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.record_btn)

        # 状态标签
        self.status_label = QLabel("💡 点击上方按钮开始自动录音（3秒）")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

        # 已录入声纹列表
        layout.addWidget(QLabel("当前医生已录入的声纹："))
        self.voiceprint_list = QListWidget()
        layout.addWidget(self.voiceprint_list)

        # 加载当前医生的声纹
        self.name_input.textChanged.connect(self.load_voiceprints)
        self.load_voiceprints()

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_delete_tab(self):
        """创建删除声纹tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 医生列表
        layout.addWidget(QLabel("已录入声纹的医生："))
        self.doctor_list = QListWidget()
        layout.addWidget(self.doctor_list)

        # 删除按钮
        self.delete_btn = QPushButton("删除选中医生的所有声纹")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_doctor)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)

        layout.addStretch()
        widget.setLayout(layout)

        # 加载医生列表
        self.load_doctors()

        return widget

    def load_doctors(self):
        """加载医生列表到删除tab"""
        self.doctor_list.clear()
        for doctor_name in self.metadata.keys():
            item = QListWidgetItem(doctor_name)
            self.doctor_list.addItem(item)

        # 连接选中事件
        self.doctor_list.itemSelectionChanged.connect(self.on_doctor_selected)

    def on_doctor_selected(self):
        """医生选中事件"""
        has_selection = len(self.doctor_list.selectedItems()) > 0
        self.delete_btn.setEnabled(has_selection)

    def load_voiceprints(self):
        """加载当前医生的声纹列表"""
        doctor_name = self.name_input.text().strip()
        self.voiceprint_list.clear()

        if not doctor_name or doctor_name not in self.metadata:
            return

        doctor_info = self.metadata[doctor_name]

        # 兼容旧格式
        if isinstance(doctor_info, dict):
            if 'voiceprints' in doctor_info:
                # 新格式
                voiceprints = doctor_info.get('voiceprints', [])
                for i, vp_info in enumerate(voiceprints):
                    created_time = vp_info.get('created_time', 'N/A')
                    text = f"声纹 #{i+1} - {created_time}"
                    self.voiceprint_list.addItem(text)
            elif 'file_path' in doctor_info:
                # 旧格式，显示单个声纹
                text = f"声纹 #1 - {doctor_info.get('created_at', 'N/A')}"
                self.voiceprint_list.addItem(text)
        else:
            # 完全旧格式
            if isinstance(doctor_info, str):
                text = f"声纹文件 - {doctor_info}"
                self.voiceprint_list.addItem(text)

    def start_recording(self):
        """开始录音"""
        doctor_name = self.name_input.text().strip()

        if not doctor_name:
            QMessageBox.warning(self, "提示", "请先输入医生姓名")
            return

        # 检查是否已达到最大数量
        if doctor_name in self.metadata:
            doctor_info = self.metadata[doctor_name]
            if isinstance(doctor_info, dict) and 'voiceprints' in doctor_info:
                current_count = len(doctor_info.get('voiceprints', []))
                if current_count >= 5:
                    QMessageBox.warning(self, "警告", f"医生 {doctor_name} 的声纹数量已达到最大值(5个)")
                    return
            else:
                # 旧格式，转换为新格式
                self.metadata[doctor_name] = {
                    'voiceprints': [],
                    'created_time': None
                }

        # 检查模型是否可用
        if not self.model_path.exists():
            QMessageBox.warning(self, "错误", f"声纹模型不存在，请先在设置中下载模型\n路径：{self.model_path}")
            return

        # 禁用按钮
        self.record_btn.setEnabled(False)
        self.record_btn.setText("⏳ 正在录音中...")
        self.status_label.setText("🎙️ 正在录音，请清楚地说出医生姓名（3秒）")

        # 创建并启动录音线程
        self.record_thread = RecordThread(duration=3)  # 录制3秒
        self.record_thread.finished.connect(self.on_recording_finished)
        self.record_thread.error.connect(self.on_recording_error)
        self.record_thread.start()

    def on_recording_finished(self, audio_data):
        """录音完成"""
        doctor_name = self.name_input.text().strip()

        try:
            # 提取声纹特征
            embedding = self.extract_voiceprint(audio_data)

            if embedding is None:
                raise Exception("声纹特征提取失败")

            # 保存声纹
            self.save_voiceprint(doctor_name, embedding)

            # 更新UI
            self.status_label.setText("✅ 声纹录入成功！")
            self.load_voiceprints()
            self.load_doctors()

            QMessageBox.information(self, "成功", f"医生 {doctor_name} 的声纹录入成功！")

        except Exception as e:
            logger.error(f"保存声纹失败: {e}")
            self.status_label.setText(f"❌ 失败: {e}")
            QMessageBox.critical(self, "错误", f"保存声纹失败: {e}")

        finally:
            # 恢复按钮状态
            self.record_btn.setEnabled(True)
            self.record_btn.setText("🎤 点击录音（自动3秒）")

    def on_recording_error(self, error_msg):
        """录音错误"""
        logger.error(f"录音失败: {error_msg}")
        self.status_label.setText(f"❌ 录音失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"录音失败: {error_msg}")

        # 恢复按钮状态
        self.record_btn.setEnabled(True)
        self.record_btn.setText("🎤 点击录音（自动3秒）")

    def extract_voiceprint(self, audio_data):
        """提取声纹特征"""
        try:
            # 保存临时音频文件
            temp_wav = self.voiceprint_dir / "temp.wav"
            sf.write(temp_wav, audio_data, 16000)

            # 使用模型提取特征
            from voice.speaker_realtime import SpeakerRealtime

            # 创建识别器实例
            speaker_recognizer = SpeakerRealtime(str(self.model_path))

            # 提取embedding
            embedding = speaker_recognizer.extract_embedding(audio_data, 16000)

            # 清理临时文件
            if temp_wav.exists():
                temp_wav.unlink()

            return embedding

        except Exception as e:
            logger.error(f"声纹特征提取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def save_voiceprint(self, doctor_name, embedding):
        """保存声纹"""
        from datetime import datetime

        # 初始化医生数据
        if doctor_name not in self.metadata:
            self.metadata[doctor_name] = {
                'voiceprints': [],
                'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # 检查是否已达到最大数量
        if len(self.metadata[doctor_name]['voiceprints']) >= 5:
            raise Exception("声纹数量已达到最大值(5个)")

        # 生成声纹ID
        voiceprint_id = len(self.metadata[doctor_name]['voiceprints']) + 1

        # 保存声纹文件
        voiceprint_file = self.voiceprint_dir / f"{doctor_name}_{voiceprint_id}.npy"
        np.savez(voiceprint_file, embedding=embedding)

        # 添加到元数据
        self.metadata[doctor_name]['voiceprints'].append({
            'id': voiceprint_id,
            'file_path': str(voiceprint_file),
            'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 保存元数据
        self.save_metadata()

        logger.info(f"✅ 已保存医生 {doctor_name} 的第 {voiceprint_id} 条声纹")

    def delete_doctor(self):
        """删除医生的所有声纹"""
        selected_items = self.doctor_list.selectedItems()

        if not selected_items:
            return

        doctor_name = selected_items[0].text()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除医生 {doctor_name} 的所有声纹吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 删除声纹文件
            voiceprints = self.metadata[doctor_name].get('voiceprints', [])
            for vp_info in voiceprints:
                file_path = Path(vp_info.get('file_path', ''))
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"🗑️ 已删除声纹文件: {file_path}")

            # 从元数据中删除
            del self.metadata[doctor_name]
            self.save_metadata()

            # 更新UI
            self.load_doctors()
            self.load_voiceprints()
            self.name_input.clear()

            QMessageBox.information(self, "成功", f"医生 {doctor_name} 的所有声纹已删除")

        except Exception as e:
            logger.error(f"删除声纹失败: {e}")
            QMessageBox.critical(self, "错误", f"删除声纹失败: {e}")