#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAD 阈值测试脚本
测试不同 aggressiveness 值 (1, 2, 3) 的识别准确率和响应时间
"""
import sys
import os
import time
import webrtcvad
import numpy as np
from collections import defaultdict
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.recorder import VoiceRecorder
from settings import cfg


class VADThresholdTester:
    def __init__(self):
        self.results = {
            1: {"segments": [], "avg_len": 0, "response_time": 0},
            2: {"segments": [], "avg_len": 0, "response_time": 0},
            3: {"segments": [], "avg_len": 0, "response_time": 0},
        }

    def test_threshold(self, aggressiveness, test_wav_file=None):
        """测试指定 aggressiveness 值"""
        logger.info(f"[测试] VAD Aggressiveness={aggressiveness}")

        # 创建 VAD 实例
        vad = webrtcvad.Vad(aggressiveness)

        # 如果提供了测试音频文件，使用它进行测试
        if test_wav_file and os.path.exists(test_wav_file):
            return self._test_with_audio_file(vad, aggressiveness, test_wav_file)
        else:
            return self._test_with_simulated_data(vad, aggressiveness)

    def _test_with_audio_file(self, vad, aggressiveness, wav_path):
        """使用真实音频文件测试"""
        import soundfile as sf

        audio, sr = sf.read(wav_path)
        if sr != 16000:
            # 重采样到 16kHz
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        # 转换为 int16
        audio = (audio * 32767).astype(np.int16)

        # 切分 10ms 帧
        frame_len = 160  # 10ms @ 16kHz
        num_frames = len(audio) // frame_len

        start_time = time.time()
        speech_segments = []
        is_speech = False
        segment_start = 0

        for i in range(num_frames):
            frame = audio[i * frame_len:(i + 1) * frame_len]
            frame_bytes = frame.tobytes()

            has_speech = vad.is_speech(frame_bytes, 16000)

            if has_speech and not is_speech:
                is_speech = True
                segment_start = i * frame_len
            elif not has_speech and is_speech:
                is_speech = False
                segment_end = i * frame_len
                if (segment_end - segment_start) >= frame_len * 3:  # 至少 30ms
                    speech_segments.append((segment_start, segment_end))

        # 处理最后一段
        if is_speech:
            segment_end = num_frames * frame_len
            if (segment_end - segment_start) >= frame_len * 3:
                speech_segments.append((segment_start, segment_end))

        response_time = time.time() - start_time

        # 计算统计信息
        if speech_segments:
            lengths = [end - start for start, end in speech_segments]
            avg_len = np.mean(lengths) / 16000  # 转换为秒
        else:
            avg_len = 0

        result = {
            "aggressiveness": aggressiveness,
            "segments": len(speech_segments),
            "avg_length": avg_len,
            "response_time": response_time,
            "segments_detail": [(s/16000, e/16000) for s, e in speech_segments[:10]]  # 只保留前10段
        }

        self.results[aggressiveness] = result
        logger.info(f"[结果] Aggressiveness={aggressiveness}: {len(speech_segments)} 段, "
                   f"平均时长={avg_len:.2f}s, 响应时间={response_time:.4f}s")

        return result

    def _test_with_simulated_data(self, vad, aggressiveness):
        """使用模拟数据测试（用于说明测试方法）"""
        logger.warning("未提供测试音频文件，使用模拟数据测试")

        # 模拟音频数据：30秒音频，包含语音/静音段落
        duration = 30  # 秒
        sample_rate = 16000
        frame_len = 160  # 10ms
        num_frames = duration * sample_rate // frame_len

        # 定义语音段落 (起始秒, 结束秒)
        simulated_speech_segments = [
            (1.0, 3.0),
            (5.0, 8.0),
            (10.0, 12.0),
            (15.0, 18.0),
            (20.0, 25.0),
        ]

        # 创建模拟音频数据
        audio = np.random.randint(-100, 100, size=num_frames * frame_len, dtype=np.int16)
        for start, end in simulated_speech_segments:
            start_sample = int(start * sample_rate)
            end_sample = int(end * sample_rate)
            audio[start_sample:end_sample] = np.random.randint(-3000, 3000,
                                                           size=end_sample - start_sample,
                                                           dtype=np.int16)

        # 测试 VAD
        start_time = time.time()
        detected_segments = []
        is_speech = False
        segment_start = 0

        for i in range(num_frames):
            frame = audio[i * frame_len:(i + 1) * frame_len]
            frame_bytes = frame.tobytes()

            has_speech = vad.is_speech(frame_bytes, 16000)

            if has_speech and not is_speech:
                is_speech = True
                segment_start = i * frame_len
            elif not has_speech and is_speech:
                is_speech = False
                segment_end = i * frame_len
                if (segment_end - segment_start) >= frame_len * 3:
                    detected_segments.append((segment_start, segment_end))

        if is_speech:
            detected_segments.append((segment_start, num_frames * frame_len))

        response_time = time.time() - start_time

        if detected_segments:
            lengths = [end - start for start, end in detected_segments]
            avg_len = np.mean(lengths) / 16000
        else:
            avg_len = 0

        result = {
            "aggressiveness": aggressiveness,
            "segments": len(detected_segments),
            "avg_length": avg_len,
            "response_time": response_time,
            "segments_detail": [(s/16000, e/16000) for s, e in detected_segments]
        }

        self.results[aggressiveness] = result
        logger.info(f"[结果] Aggressiveness={aggressiveness}: {len(detected_segments)} 段, "
                   f"平均时长={avg_len:.2f}s, 响应时间={response_time:.4f}s")

        return result

    def print_summary(self):
        """打印测试总结"""
        logger.info("\n" + "="*60)
        logger.info("VAD 阈值测试总结")
        logger.info("="*60)

        table = []
        for agg in [1, 2, 3]:
            result = self.results[agg]
            table.append({
                "Aggressiveness": agg,
                "语音段数": result["segments"],
                "平均时长(s)": f"{result['avg_length']:.2f}",
                "响应时间(s)": f"{result['response_time']:.4f}"
            })

        # 打印表格
        headers = table[0].keys()
        col_widths = [max(len(str(row[h])) for row in table) for h in headers]
        col_widths = [max(w, len(h)) for w, h in zip(col_widths, headers)]

        header = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        logger.info(header)
        logger.info("-" * len(header))

        for row in table:
            row_str = " | ".join(str(row[h]).ljust(w) for h, w in zip(headers, col_widths))
            logger.info(row_str)

        logger.info("\n建议:")
        # 根据测试结果给出建议
        segments_2 = self.results[2].get("segments", 0)
        response_2 = self.results[2].get("response_time", 0)

        if segments_2 >= 3 and response_2 < 0.5:
            logger.info("✓ 建议：Aggressiveness=2（平衡准确率和响应速度）")
        elif self.results[1].get("segments", 0) >= 3:
            logger.info("✓ 建议：Aggressiveness=1（响应最快，适合流畅对话）")
        else:
            logger.info("✓ 建议：Aggressiveness=3（最高准确性，适合嘈杂环境）")

        logger.info("="*60 + "\n")

    def get_recommendation(self):
        """根据测试结果返回推荐的 aggressiveness 值"""
        # 优先选择 2，如果 2 表现不好则选择 1 或 3
        agg_2 = self.results[2]
        segments_2 = agg_2.get("segments", 0)
        response_2 = agg_2.get("response_time", 0)

        if segments_2 >= 3 and response_2 < 0.5:
            return 2, "平衡准确率和响应速度"

        agg_1 = self.results[1]
        if agg_1.get("segments", 0) >= 3:
            return 1, "响应最快，适合流畅对话"

        return 3, "最高准确性，适合嘈杂环境"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VAD 阈值测试")
    parser.add_argument("--wav", type=str, help="测试用的 WAV 音频文件")
    args = parser.parse_args()

    tester = VADThresholdTester()

    # 测试所有阈值
    logger.info("\n开始 VAD 阈值测试...\n")
    for aggressiveness in [1, 2, 3]:
        tester.test_threshold(aggressiveness, args.wav)
        time.sleep(0.5)

    # 打印总结
    tester.print_summary()

    # 获取推荐
    recommended, reason = tester.get_recommendation()
    logger.info(f"\n最终推荐: Aggressiveness={recommended}, 原因: {reason}")
