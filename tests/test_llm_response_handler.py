#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 响应处理测试脚本
测试重试机制、JSON 格式验证、响应格式标准化
"""
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_response_handler import (
    LLMResponseValidator,
    LLMRetryHandler,
    LLMResponseNormalizer
)
from loguru import logger


class LLMHandlerTester:
    """LLM 响应处理器测试器"""

    def __init__(self):
        self.validator = LLMResponseValidator()
        self.normalizer = LLMResponseNormalizer()

    def test_json_extraction(self):
        """测试 JSON 提取"""
        logger.info("\n[测试] JSON 提取功能")

        test_cases = [
            ("纯 JSON", '{"name": "test", "pet_name": "小灰", "species": "猫"}'),
            ("带 markdown 代码块", '```json\n{"name": "test", "pet_name": "小灰"}\n```'),
            ("带 python 代码块", '```python\n{"name": "test", "pet_name": "小灰", "weight": "3.5"}\n```'),
            ("文本包含 JSON", '这是分析结果：\n```json\n{"name": "test", "pet_name": "小灰", "species": "猫"}\n\n谢谢。'),
            ("无效 JSON", '{"name": "test", "pet_name": "小灰", invalid}'),
        ]

        for case_name, text in test_cases:
            success, data = self.validator.extract_json(text)
            logger.info(f"{case_name:20s}: {'✓ 成功' if success else '✗ 失败'}, {data if success else ''}")

    def test_medical_record_validation(self):
        """测试医疗记录验证"""
        logger.info("\n[测试] 医疗记录验证功能")

        test_cases = [
            ("有效记录", {
                "name": "张三",
                "phone": "13800138000",
                "pet_name": "小灰",
                "species": "猫",
                "breed": "英短",
                "weight": "3.5",
                "deworming": "是",
                "sterilization": "否",
                "complaint": "呕吐、腹泻",
                "checkup": "",
                "results": "",
                "diagnosis": "胃肠炎",
                "treatment": ""
            }),
            ("缺少字段", {
                "name": "张三",
                "pet_name": "小灰",
                "species": "猫",
                # 缺少其他字段
            }),
            ("体重无效", {
                "name": "张三",
                "phone": "13800138000",
                "pet_name": "小灰",
                "species": "猫",
                "breed": "英短",
                "weight": "abc",  # 无效的体重
                "deworming": "是",
                "sterilization": "否",
                "complaint": "",
                "checkup": "",
                "results": "",
                "diagnosis": "",
                "treatment": ""
            }),
            ("物种无效", {
                "name": "张三",
                "phone": "13800138000",
                "pet_name": "小灰",
                "species": "兔子",  # 无效的物种
                "breed": "英短",
                "weight": "3.5",
                "deworming": "是",
                "sterilization": "否",
                "complaint": "",
                "checkup": "",
                "results": "",
                "diagnosis": "",
                "treatment": ""
            }),
        ]

        for case_name, data in test_cases:
            valid, msg = self.validator.validate_medical_record(data)
            logger.info(f"{case_name:20s}: {'✓ 有效' if valid else '✗ 无效'}, {msg}")

    def test_normalization(self):
        """测试数据标准化"""
        logger.info("\n[测试] 数据标准化功能")

        test_cases = [
            ("完整数据", {
                "name": "张三",
                "phone": "13800138000",
                "pet_name": "小灰",
                "species": "猫",
                "breed": "英短",
                "weight": "3.5",
                "deworming": "是",
                "sterilization": "否",
                "complaint": "呕吐、腹泻",
                "checkup": "",
                "results": "",
                "diagnosis": "胃肠炎",
                "treatment": ""
            }),
            ("数据类型混合", {
                "name": None,
                "phone": 13800138000,  # 数字
                "pet_name": None,
                "species": 1,  # 数字
                "breed": None,
                "weight": 3.5,  # 浮点数
                "deworming": None,
                "sterilization": None,
                "complaint": None,
                "checkup": None,
                "results": None,
                "diagnosis": None,
                "treatment": None
            }),
            ("缺少字段", {
                "name": "张三",
                # 缺少其他字段
            }),
        ]

        for case_name, data in test_cases:
            normalized = self.normalizer.normalize_medical_record(data)
            logger.info(f"{case_name:20s}:")
            logger.info(f"  原始: {json.dumps(data, ensure_ascii=False, indent=2)}")
            logger.info(f"  标准化后: {json.dumps(normalized, ensure_ascii=False, indent=2)}")

    async def test_retry_mechanism(self):
        """测试重试机制"""
        logger.info("\n[测试] 重试机制")

        retry_handler = LLMRetryHandler(max_retries=3, retry_delay=0.5)

        # 模拟一个会失败的 LLM 调用
        call_count = 0

        async def failing_llm_call():
            nonlocal call_count
            call_count += 1
            logger.info(f"[测试] 第 {call_count} 次调用")

            if call_count < 3:
                raise Exception("模拟失败")
            else:
                # 返回有效的 JSON
                return '{"name": "张三", "pet_name": "小灰", "species": "猫", "breed": "英短", "weight": "3.5", "deworming": "否", "sterilization": "否", "complaint": "", "checkup": "", "results": "", "diagnosis": "", "treatment": ""}'

        success, data, message = await retry_handler.llm_call_with_retry(failing_llm_call)
        logger.info(f"重试测试结果: {'✓ 成功' if success else '✗ 失败'}, {message}, 调用次数: {call_count}")
        logger.info(f"返回数据: {data}")

        # 测试完全失败的情况
        call_count = 0

        async def always_failing_llm_call():
            nonlocal call_count
            call_count += 1
            raise Exception("始终失败")

        success, data, message = await retry_handler.llm_call_with_retry(always_failing_llm_call)
        logger.info(f"全部失败测试结果: {'✓ 成功' if success else '✗ 失败'}, {message}, 调用次数: {call_count}")

    def test_invalid_json_recovery(self):
        """测试无效 JSON 恢复"""
        logger.info("\n[测试] 无效 JSON 恢复")

        retry_handler = LLMRetryHandler(max_retries=2, retry_delay=0.1)
        call_count = 0

        async def invalid_json_llm_call():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 第一次返回无效 JSON
                return '这是一些文本，不是 JSON'
            else:
                # 第二次返回有效 JSON
                return '{"name": "张三", "pet_name": "小灰", "species": "猫", "breed": "英短", "weight": "3.5", "deworming": "否", "sterilization": "否", "complaint": "", "checkup": "", "results": "", "diagnosis": "", "treatment": ""}'

        async def run_test():
            success, data, message = await retry_handler.llm_call_with_retry(invalid_json_llm_call)
            logger.info(f"无效 JSON 恢复测试: {'✓ 成功' if success else '✗ 失败'}, {message}, 调用次数: {call_count}")
            logger.info(f"返回数据: {data}")

        asyncio.run(run_test())

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("="*60)
        logger.info("LLM 响应处理器测试套件")
        logger.info("="*60)

        self.test_json_extraction()
        self.test_medical_record_validation()
        self.test_normalization()
        asyncio.run(self.test_retry_mechanism())
        self.test_invalid_json_recovery()

        logger.info("\n" + "="*60)
        logger.info("所有测试完成")
        logger.info("="*60)


if __name__ == "__main__":
    tester = LLMHandlerTester()
    tester.run_all_tests()
