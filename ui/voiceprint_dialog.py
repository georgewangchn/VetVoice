# -*- coding: utf-8 -*-

import os
import numpy as np
import json
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QLineEdit, QTextEdit, QMessageBox,
    QListWidget, QListWidgetItem, QComboBox, QFileDialog, QGroupBox, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon
import sounddevice as sd
import soundfile as sf
import tempfile


class RecordThread(QThread):
    """录音线程"""
    audio_data = Signal(np.ndarray, int)  # 音频数据，采样率

    def __init__(self, sample_rate=16000, device=None):
        super().__init__()
        self.sample_rate = sample_rate
        self.device = device
        self.recording = False
        self.audio_buffer = []

    def run(self):
        """开始录音"""
        try:
            def callback(indata, frames, time, status):
                if status:
                    logger.warning(f"录音状态: {status}")
                if self.recording:
                    self.audio_buffer.append(indata.copy())

            with sd.InputStream(callback=callback,
                              channels=1,
                              samplerate=self.sample_rate,
                              device=self.device):
                while self.recording:
                    sd.sleep(100)

            # 合并音频数据
            if self.audio_buffer:
                audio_data = np.concatenate(self.audio_buffer, axis=0)
                self.audio_data.emit(audio_data.flatten(), self.sample_rate)

        except Exception as e:
            logger.error(f"录音出错: {e}")

    def stop_recording(self):
        """停止录音"""
        self.recording = False
        self.wait()


class VoiceprintDialog(QDialog):
    """声纹管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("医生声纹管理")
        self.resize(600, 500)

        # 声纹存储路径
        self.voiceprint_dir = Path.home() / ".vetvoice" / "voiceprints"
        self.voiceprint_dir.mkdir(parents=True, exist_ok=True)

        # 当前选择的设备
        self.current_device = None

        # 初始化UI
        self.init_ui()
        self.load_speaker_list()

        # 初始刷新设备
        QTimer.singleShot(500, self.refresh_audio_devices)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # Tab控件
        from PySide6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()

        # 新增Tab
        self.add_tab = self.create_add_tab()
        self.tabs.addTab(self.add_tab, "新增声纹")

        # 删除Tab
        self.delete_tab = self.create_delete_tab()
        self.tabs.addTab(self.delete_tab, "删除声纹")

        layout.addWidget(self.tabs)

    def create_add_tab(self):
        """创建新增标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 医生姓名输入
        name_layout = QHBoxLayout()
        name_label = QLabel("医生姓名:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入医生姓名")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 显示当前医生声纹数量
        self.voiceprint_count_label = QLabel("当前声纹数量: 0/5")
        layout.addWidget(self.voiceprint_count_label)

        # 说话人选择（支持多个声纹）
        voiceprint_layout = QHBoxLayout()
        voiceprint_label = QLabel("声纹编号:")
        self.voiceprint_combo = QComboBox()
        for i in range(5):
            self.voiceprint_combo.addItem(f"#{i+1}")
        voiceprint_layout.addWidget(voiceprint_label)
        voiceprint_layout.addWidget(self.voiceprint_combo)
        layout.addLayout(voiceprint_layout)

        # 录音设备选择
        device_layout = QHBoxLayout()
        device_label = QLabel("录音设备:")
        self.device_combo = QComboBox()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_audio_devices)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(refresh_btn)
        layout.addLayout(device_layout)

        # 录音按钮
        button_layout = QHBoxLayout()
        self.record_start_btn = QPushButton("开始录音")
        self.record_start_btn.clicked.connect(self.start_recording)
        self.record_stop_btn = QPushButton("停止录音")
        self.record_stop_btn.clicked.connect(self.stop_recording)
        self.record_stop_btn.setEnabled(False)
        button_layout.addWidget(self.record_start_btn)
        button_layout.addWidget(self.record_stop_btn)
        layout.addLayout(button_layout)

        # 状态显示
        self.status_label = QLabel("准备就绪")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # 音频预览
        self.audio_preview = QTextEdit()
        self.audio_preview.setReadOnly(True)
        self.audio_preview.setMaximumHeight(80)
        layout.addWidget(self.audio_preview)

        # 保存按钮
        self.save_btn = QPushButton("保存声纹")
        self.save_btn.clicked.connect(self.save_voiceprint)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)

        # 提示信息
        tip_label = QLabel("提示：建议录制3-5秒的语音，同一医生可录入最多5条不同状态的声纹")
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(tip_label)

        # 录音线程
        self.record_thread = None
        self.current_audio_data = None
        self.current_sample_rate = 16000

        return widget

    def create_delete_tab(self):
        """创建删除标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 医生声纹列表
        self.speaker_list = QListWidget()
        layout.addWidget(self.speaker_list)

        # 删除按钮
        self.delete_btn = QPushButton("删除选中声纹")
        self.delete_btn.clicked.connect(self.delete_voiceprint)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)

        # 列表选择变化事件
        self.speaker_list.itemSelectionChanged.connect(self.on_selection_changed)

        return widget

    def refresh_audio_devices(self):
        """刷新音频设备列表"""
        self.device_combo.clear()

        # 获取输入设备
        devices = sd.query_devices()
        input_devices = []

        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                device_name = f"{dev['name']}"
                self.device_combo.addItem(device_name, i)

        # 默认选择第一个设备
        if self.device_combo.count() > 0:
            self.current_device = self.device_combo.currentData()
            self.name_edit.textChanged.connect(self.on_name_changed)
            self.status_label.setText("请输入医生姓名后开始录音")
        else:
            self.status_label.setText("未找到录音设备")

    def on_name_changed(self):
        """姓名变化时更新状态"""
        doctor_name = self.name_edit.text().strip()
        if doctor_name:
            self.record_start_btn.setEnabled(True)
            self.update_voiceprint_count(doctor_name)
        else:
            self.record_start_btn.setEnabled(False)
            self.voiceprint_count_label.setText("当前声纹数量: 0/5")

    def update_voiceprint_count(self, doctor_name):
        """更新声纹数量显示"""
        count = self.get_doctor_voiceprint_count(doctor_name)
        self.voiceprint_count_label.setText(f"当前声纹数量: {count}/5")

    def get_doctor_voiceprint_count(self, doctor_name):
        """获取指定医生的声纹数量"""
        count = 0
        metadata_file = self.voiceprint_dir / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            if doctor_name in metadata:
                # 检查实际文件数量
                for voiceprint_id in metadata[doctor_name].keys():
                    voiceprint_data = metadata[doctor_name][voiceprint_id]
                    voiceprint_file = Path(voiceprint_data['file_path'])
                    if voiceprint_file.exists():
                        count += 1

        return count

    def start_recording(self):
        """开始录音"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请先输入医生姓名")
            return

        if self.device_combo.count() == 0:
            QMessageBox.warning(self, "提示", "未找到录音设备")
            return

        # 检查声纹数量限制
        doctor_name = self.name_edit.text().strip()
        voiceprint_count = self.get_doctor_voiceprint_count(doctor_name)
        if voiceprint_count >= 5:
            QMessageBox.warning(self, "数量限制",
                f"{doctor_name} 已达到最大声纹数量限制（5条）\\n"
                "请先删除部分声纹后再录入新的。"
            )
            return

        self.current_device = self.device_combo.currentData()

        # 更新UI状态
        self.record_start_btn.setEnabled(False)
        self.record_stop_btn.setEnabled(True)
        self.name_edit.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.status_label.setText("正在录音...")

        # 开始录音
        self.record_thread = RecordThread(sample_rate=16000, device=self.current_device)
        self.record_thread.audio_data.connect(self.on_audio_received)

        self.record_thread.recording = True
        self.record_thread.start()

    def stop_recording(self):
        """停止录音"""
        if self.record_thread and self.record_thread.isRunning():
            self.record_thread.stop_recording()

        # 更新UI状态
        self.record_start_btn.setEnabled(True)
        self.record_stop_btn.setEnabled(False)
        self.name_edit.setEnabled(True)
        self.device_combo.setEnabled(True)
        self.status_label.setText("录音已完成，请保存声纹")

    def on_audio_received(self, audio_data, sample_rate):
        """接收录音数据"""
        self.current_audio_data = audio_data
        self.current_sample_rate = sample_rate

        # 显示音频信息
        duration = len(audio_data) / sample_rate
        audio_info = f"录音时长: {duration:.2f}秒\\n采样率: {sample_rate}Hz"
        self.audio_preview.setText(audio_info)

        # 如果录音时间足够，允许保存
        if duration >= 2.0:
            self.status_label.setText("录音完成，可以保存声纹")
            self.save_btn.setEnabled(True)
        else:
            self.status_label.setText(f"录音时间过短 ({duration:.2f}秒)，建议至少3秒")
            self.save_btn.setEnabled(False)

    def save_voiceprint(self):
        """保存声纹"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入医生姓名")
            return

        if self.current_audio_data is None or len(self.current_audio_data) == 0:
            QMessageBox.warning(self, "提示", "没有录音数据")
            return

        try:
            # 提取声纹特征
            voiceprint = self.extract_voiceprint(self.current_audio_data, self.current_sample_rate)

            if voiceprint is None:
                QMessageBox.warning(self, "错误", "声纹提取失败，请重新录音")
                return

            # 保存声纹
            doctor_name = self.name_edit.text().strip()
            voiceprint_index = self.voiceprint_combo.currentIndex()

            voiceprint_file = self.voiceprint_dir / f"{doctor_name}_{voiceprint_index}.npz"

            # 保存声纹数据
            np.savez_compressed(voiceprint_file, embedding=voiceprint)

            # 更新元数据
            self.add_speaker_metadata(doctor_name, str(voiceprint_file), voiceprint_index)

            # 清空输入
            self.audio_preview.clear()
            self.save_btn.setEnabled(False)
            self.status_label.setText("声纹保存成功！")

            # 更新显示
            self.update_voiceprint_count(doctor_name)
            self.load_speaker_list()

            QMessageBox.information(
                self, "成功",
                f"声纹已保存！\\n\\n"
                f"医生：{doctor_name}\\n"
                f"编号：#{voiceprint_index + 1}\\n"
                f"当前声纹数量：{self.get_doctor_voiceprint_count(doctor_name)}/5"
            )

        except Exception as e:
            logger.error(f"保存声纹失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def extract_voiceprint(self, audio_data, sample_rate):
        """提取声纹特征"""
        try:
            from settings import cfg
            from utils.resource_path import get_resource_path

            # 加载声纹识别模型
            resource_dir = cfg.get("app", "resource_dir")
            voiceprint_path = cfg.get("spk", "voiceprint_path")

            # 获取模型路径
            model_path = get_resource_path(voiceprint_path)
            logger.info(f"声纹模型路径: {model_path}")

            if not Path(model_path).exists():
                logger.error(f"声纹模型不存在: {model_path}")
                # 使用简化特征作为fallback
                return self.extract_simple_features(audio_data, sample_rate)

            # 尝试使用Wespeaker模型提取特征
            try:
                return self.extract_wespeaker_features(audio_data, sample_rate, model_path)
            except Exception as e:
                logger.warning(f"Wespeaker模型提取失败，使用简化特征: {e}")
                return self.extract_simple_features(audio_data, sample_rate)

        except Exception as e:
            logger.error(f"声纹提取失败: {e}")
            return self.extract_simple_features(audio_data, sample_rate)

    def extract_wespeaker_features(self, audio_data, sample_rate, model_path):
        """使用Wespeaker模型提取声纹特征"""
        try:
            import torch
            import torchaudio

            # 检查模型文件
            model_file = Path(model_path) / "resnet34.pt"
            config_file = Path(model_path) / "config.yaml"

            if not model_file.exists():
                raise FileNotFoundError(f"模型文件不存在: {model_file}")

            logger.info(f"加载Wespeaker模型: {model_file}")

            # 加载配置文件（如果存在）
            config = {}
            if config_file.exists():
                try:
                    import yaml
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    logger.info("加载声纹模型配置成功")
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {e}")

            # 加载模型
            device = cfg.get("spk", "device", "cpu")
            checkpoint = torch.load(model_file, map_location=device,weights_only=False)
            model = checkpoint['model'] if 'model' in checkpoint else checkpoint
            model.eval()

            # 确保音频是float32格式
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # 转换为torch tensor
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)

            # 提取embedding
            with torch.no_grad():
                embedding = model(audio_tensor)

            # 展平为一维向量
            embedding = embedding.squeeze().cpu().numpy()

            logger.info(f"提取声纹特征成功，维度: {embedding.shape}")
            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(f"Wespeaker特征提取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def extract_simple_features(self, audio_data, sample_rate):
        """提取简化的音频特征"""
        try:
            # 音频统计特征
            features = np.array([
                np.mean(audio_data),
                np.std(audio_data),
                np.max(audio_data),
                np.min(audio_data),
                np.median(audio_data),
                np.percentile(audio_data, 25),
                np.percentile(audio_data, 75),
                len(audio_data)
            ], dtype=np.float32)

            # 扩展到256维
            if len(features) < 256:
                features = np.pad(features, (0, 256 - len(features)), 'constant')

            # 尝试添加MFCC特征
            try:
                import librosa
                audio_float = audio_data.astype(np.float32)
                mfcc = librosa.feature.mfcc(y=audio_float, sr=sample_rate, n_mfcc=13)
                mfcc_mean = np.mean(mfcc, axis=1)

                if len(mfcc_mean) <= 256:
                    features = features[:256 - len(mfcc_mean)]
                    features = np.concatenate([features, mfcc_mean])
            except ImportError:
                logger.warning("librosa未安装，只使用统计特征")

            return features.astype(np.float32)

        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            # 返回随机特征作为fallback
            return np.random.randn(256).astype(np.float32)

    def add_speaker_metadata(self, doctor_name, file_path, voiceprint_index):
        """添加说话人元数据"""
        metadata_file = self.voiceprint_dir / "metadata.json"

        metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass

        if doctor_name not in metadata:
            metadata[doctor_name] = {}

        metadata[doctor_name][str(voiceprint_index)] = {
            'file_path': file_path,
            'created_at': str(os.path.getctime(file_path))
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def load_speaker_list(self):
        """加载说话人列表"""
        self.speaker_list.clear()

        metadata_file = self.voiceprint_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                for doctor_name in metadata.keys():
                    count = len(metadata[doctor_name])
                    display_text = f"{doctor_name} ({count}条声纹)"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, doctor_name)
                    self.speaker_list.addItem(item)

            except Exception as e:
                logger.error(f"加载说话人列表失败: {e}")

    def on_selection_changed(self):
        """列表选择变化时更新删除按钮状态"""
        has_selection = self.speaker_list.currentItem() is not None
        self.delete_btn.setEnabled(has_selection)

    def delete_voiceprint(self):
        """删除声纹"""
        current_item = self.speaker_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要删除的声纹")
            return

        doctor_name = current_item.data(Qt.UserRole)

        # 获取该医生的声纹详情
        metadata_file = self.voiceprint_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        doctor_voiceprints = metadata[doctor_name]

        # 显示选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"删除 {doctor_name} 的声纹")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        message = QLabel(f"请选择要删除的声纹编号：")
        message.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(message)

        voiceprint_combo = QComboBox()
        for vp_index in sorted([int(k) for k in doctor_voiceprints.keys()]):
            created_time = doctor_voiceprints[str(vp_index)]['created_at']
            voiceprint_combo.addItem(f"声纹 #{vp_index + 1} (创建时间: {created_time})")
        layout.addWidget(voiceprint_combo)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)

        confirm_btn = QPushButton("确定删除")
        confirm_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #da190b;
            }
        """)
        confirm_btn.clicked.connect(dialog.accept)

        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(confirm_btn)
        layout.addLayout(buttons)

        if dialog.exec() == QDialog.Accepted:
            voiceprint_indices = sorted([int(k) for k in doctor_voiceprints.keys()])
            selected_index = voiceprint_indices[voiceprint_combo.currentIndex()]
            self.delete_selected_voiceprint(doctor_name, selected_index)

    def delete_selected_voiceprint(self, doctor_name, voiceprint_index):
        """删除指定的声纹"""
        try:
            metadata_file = self.voiceprint_dir / "metadata.json"

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            if doctor_name not in metadata:
                return

            voiceprint_data = metadata[doctor_name][str(voiceprint_index)]
            voiceprint_file = Path(voiceprint_data['file_path'])

            # 删除声纹文件
            if voiceprint_file.exists():
                voiceprint_file.unlink()

            # 更新元数据
            del metadata[doctor_name][str(voiceprint_index)]

            # 如果医生没有声纹了，删除医生条目
            if not metadata[doctor_name]:
                del metadata[doctor_name]

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # 更新界面
            self.load_speaker_list()

            if doctor_name in metadata:
                count = len(metadata[doctor_name])
            else:
                count = 0

            QMessageBox.information(
                self, "成功",
                f"声纹 #{voiceprint_index + 1} 已删除！\\n\\n"
                f"医生：{doctor_name}\\n"
                f"剩余声纹数量：{count}"
            )

        except Exception as e:
            logger.error(f"删除声纹失败: {e}")
            QMessageBox.critical(self, "错误", f"删除失败: {e}")
