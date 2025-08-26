import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient
import threading
import time
from loguru import logger


class WaveformWidget(QWidget):
    def __init__(self, audio_receive, parent=None):
        super().__init__(parent)
        self.audio_receive = audio_receive
        self.frame_len = 1600  # 100ms @ 48kHz
        self.latest = np.zeros(1600, dtype=np.int16)
        self.decay_frame = np.zeros(self.frame_len, dtype=np.float32)

        self.num_bars = 40
        self.last_bar_values = [0.0] * (self.num_bars // 2)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000 // 60)  # 60 FPS

        self.recv_thread = threading.Thread(target=self._recv_run, daemon=True)
        self.recv_thread.start()

    def _recv_run(self):
        while True:
            try:
                if self.audio_receive.poll():
                    data = self.audio_receive.recv()
                    if isinstance(data, np.ndarray) and data.dtype == np.int16:
                        self.latest = data.copy()
            except Exception as e:
                logger.warning(f"[WaveformWidget] 音频接收线程异常: {e}")

    def reset_waveform(self):
        self.decay_frame = np.zeros_like(self.decay_frame)
        self.update()

    def resume_waveform(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # 背景渐变
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor(30, 30, 30))
        gradient.setColorAt(1.0, QColor(10, 10, 10))
        painter.fillRect(self.rect(), gradient)

        if self.latest is None or len(self.latest) == 0:
            self._draw_idle_state(painter, w, h)
            return

        # 平滑衰减
        self.decay_frame = 0.85 * self.decay_frame + 0.15 * self.latest
        data = np.interp(self.decay_frame, [-32768, 32767], [-1.0, 1.0])

        num_bars = self.num_bars
        samples_per_bar = len(data) // num_bars
        bar_width = w / num_bars * 0.6
        gap = w / num_bars * 0.4
        center_x = w / 2
        scale_factor = 8.0

        for i in range(num_bars // 2):
            start_idx = i * samples_per_bar
            end_idx = start_idx + samples_per_bar
            bar_value = np.abs(data[start_idx:end_idx]).mean()

            # ✨ 非线性增强
            bar_value = bar_value ** 1.5

            # ✨ 加一点 sin 扰动波动
            noise = 0.02 * np.sin(time.time() * 4 + i)
            bar_value += noise

            # ✨ 缓动平滑（延迟降低）
            smooth_value = max(bar_value, self.last_bar_values[i] * 0.9)
            smooth_value = max(smooth_value, 0.02)  # 最低保持动态
            self.last_bar_values[i] = smooth_value

            bar_height = smooth_value * h * scale_factor
            bar_height = np.clip(bar_height, h * 0.15, h * 0.85)

            color = QColor(
                int(100 + 155 * smooth_value),
                int(240 * smooth_value),
                int(100 + 155 * smooth_value)
            )

            painter.setBrush(color)
            painter.setPen(Qt.NoPen)

            x_offset = i * (bar_width + gap)

            # 左柱
            x1 = center_x - x_offset - bar_width
            y1 = h - bar_height
            painter.drawRect(x1, y1, bar_width, bar_height)

            # 右柱
            x2 = center_x + x_offset
            y2 = h - bar_height
            painter.drawRect(x2, y2, bar_width, bar_height)

            # 小球 Glow
            glow_color = QColor(180, 255, 180, int(250 * smooth_value))
            glow_radius = 6 + 6 * smooth_value
            painter.setBrush(glow_color)
            painter.drawEllipse(x1 + bar_width / 2 - glow_radius / 2, y1 - glow_radius, glow_radius, glow_radius)
            painter.drawEllipse(x2 + bar_width / 2 - glow_radius / 2, y2 - glow_radius, glow_radius, glow_radius)

    def _draw_idle_state(self, painter, w, h):
        pen = QPen(QColor(100, 100, 100, 150))
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawLine(0, h // 2, w, h // 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(100, 100, 100, 50))
        bar_width = w / 30 * 0.6
        gap = w / 30 * 0.4
        center_x = w / 2
        bar_height = h * 0.1
        for i in range(15):
            x = i * (bar_width + gap)
            painter.drawRect(x, h // 2 - bar_height // 2, bar_width, bar_height)
