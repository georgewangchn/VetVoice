#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小识别时长测试脚本
测试不同 MIN_ASR_SECONDS 值的识别效果
"""
import sys
import os
import time
import numpy as np
from collections import defaultdict
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MinASRSecondsTester:
    def __init__(self):
        self.results = {
            1.2: {"segments": 0, "avg_len": 0, "missed_short": 0, "experience_score": 0},
            1.5: {"segments": 0, "avg_len": 0, "missed_short": 0, "experience_score": 0},
            1.8: {"segments": 0, "avg_len": 0, "missed_short": 0, "experience_score": 0},
        }

    def test_min_seconds(self, min_seconds, test_segments):
        """测试指定的最小识别时长"""
        logger.info(f"[测试] MIN_ASR_SECONDS={min_seconds}s")

        # 模拟检测场景
        segments = self._simulate_detection(min_seconds, test_segments)

        # 统计结果
        detected_count = sum(1 for s in segments if s["detected"])
        avg_len = np.mean([s["length"] for s in segments if s["detected"]]) if segments else 0
        missed_short = sum(1 for s in segments if not s["detected"] and s["length"] < min_seconds)

        # 体验评分（模拟）：越短越快，但可能漏掉短句
        experience_score = self._calculate_experience_score(min_seconds, detected_count, missed_short)

        result = {
            "min_seconds": min_seconds,
            "segments": detected_count,
            "avg_length": avg_len,
            "missed_short": missed_short,
            "experience_score": experience_score,
            "segments_detail": segments
        }

        self.results[min_seconds] = result
        logger.info(f"[结果] MIN_ASR_SECONDS={min_seconds}s: 检测到 {detected_count} 段, "
                   f"平均时长={avg_len:.2f}s, 漏掉短句={missed_short}, "
                   f"体验评分={experience_score:.1f}/10")

        return result

    def _simulate_detection(self, min_seconds, test_segments):
        """模拟语音检测场景"""
        min_samples = int(min_seconds * 16000)

        segments = []
        for start, end in test_segments:
            length = end - start
            detected = length >= min_samples

            segments.append({
                "start": start,
                "end": end,
                "length": length,
                "detected": detected
            })

        return segments

    def _calculate_experience_score(self, min_seconds, detected_count, missed_short):
        """计算用户体验评分（模拟）"""
        # 基础分：检测到的段数越多越好
        base_score = (detected_count / 5) * 5  # 假设最少检测到5段

        # 补充分：时长越短越快（越好），但要惩罚漏掉短句
        speed_score = (1.8 - min_seconds) / (1.8 - 1.2) * 3  # 1.2s得3分，1.8s得0分
        penalty = missed_short * 0.5  # 每漏掉一个短句扣0.5分

        total_score = base_score + speed_score - penalty
        return max(0, min(10, total_score))

    def print_summary(self):
        """打印测试总结"""
        logger.info("\n" + "="*60)
        logger.info("最小识别时长测试总结")
        logger.info("="*60)

        table = []
        for seconds in [1.2, 1.5, 1.8]:
            result = self.results[seconds]
            table.append({
                "时长(s)": seconds,
                "检测段数": result["segments"],
                "平均长度(s)": f"{result['avg_length']:.2f}",
                "漏掉短句": result["missed_short"],
                "体验评分": f"{result['experience_score']:.1f}/10"
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

        logger.info("\n说明:")
        logger.info("- 检测段数：识别到的语音段数量（越多越好）")
        logger.info("- 漏掉短句：未能识别的短句数量（越少越好）")
        logger.info("- 体验评分：综合评分，考虑响应速度和准确性（越高越好）")

        logger.info("\n建议:")
        # 根据测试结果给出建议
        best_score = 0
        best_seconds = 1.5
        for seconds in [1.2, 1.5, 1.8]:
            score = self.results[seconds]["experience_score"]
            if score > best_score:
                best_score = score
                best_seconds = seconds

        if best_seconds == 1.5:
            logger.info("✓ 建议：MIN_ASR_SECONDS=1.5s（平衡响应速度和准确性）")
        elif best_seconds == 1.2:
            logger.info("✓ 建议：MIN_ASR_SECONDS=1.2s（最快响应，适合快速对话）")
        else:
            logger.info("✓ 建议：MIN_ASR_SECONDS=1.8s（最高准确性，适合完整句子）")

        logger.info("="*60 + "\n")

    def get_recommendation(self):
        """根据测试结果返回推荐的 MIN_ASR_SECONDS 值"""
        best_score = 0
        best_seconds = 1.5
        best_reason = ""

        for seconds in [1.2, 1.5, 1.8]:
            score = self.results[seconds]["experience_score"]
            result = self.results[seconds]
            detected = result["segments"]
            missed = result["missed_short"]

            if score > best_score:
                best_score = score
                best_seconds = seconds

                if seconds == 1.5:
                    best_reason = f"检测到{detected}段，漏掉{missed}句，平衡响应速度和准确性"
                elif seconds == 1.2:
                    best_reason = f"检测到{detected}段，漏掉{missed}句，最快响应，适合快速对话"
                else:
                    best_reason = f"检测到{detected}段，漏掉{missed}句，最高准确性，适合完整句子"

        return best_seconds, best_reason


if __name__ == "__main__":
    # 模拟测试数据：5个语音段，包含不同长度的语音
    test_segments = [
        (0, 1.5),    # 1.5秒 - 正常短句
        (2.0, 3.8),  # 1.8秒 - 中等长度
        (5.0, 6.0),  # 1.0秒 - 短句
        (7.0, 9.5),  # 2.5秒 - 长句
        (10.0, 11.3) # 1.3秒 - 较短句
    ]

    tester = MinASRSecondsTester()

    # 测试所有时长
    logger.info("\n开始最小识别时长测试...\n")
    for seconds in [1.2, 1.5, 1.8]:
        tester.test_min_seconds(seconds, test_segments)
        time.sleep(0.5)

    # 打印总结
    tester.print_summary()

    # 获取推荐
    recommended, reason = tester.get_recommendation()
    logger.info(f"\n最终推荐: MIN_ASR_SECONDS={recommended}s, 原因: {reason}")
