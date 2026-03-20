#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 响应处理工具
包含重试机制、JSON 格式验证、响应格式标准化
"""
import json
import asyncio
import time
from typing import Any, Dict, Optional, Tuple
from loguru import logger


class LLMResponseValidator:
    """LLM 响应验证器"""

    @staticmethod
    def extract_json(text: str) -> Tuple[bool, Optional[Dict]]:
        """
        从文本中提取 JSON

        Args:
            text: 包含 JSON 的文本

        Returns:
            (是否成功, JSON 数据或 None)
        """
        if not text:
            return False, None

        # 尝试直接解析
        try:
            data = json.loads(text)
            return True, data
        except json.JSONDecodeError:
            pass

        # 尝试查找 JSON 代码块
        import re
        # 匹配 ```json ... ``` 或 ``` ... ```
        json_pattern = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)\n?```')
        matches = json_pattern.findall(text)

        for match in matches:
            try:
                data = json.loads(match.strip())
                return True, data
            except json.JSONDecodeError:
                continue

        # 尝试查找首个完整的 JSON 对象
        brace_pattern = re.compile(r'\{[\s\S]*\}')
        matches = brace_pattern.findall(text)

        for match in matches:
            try:
                data = json.loads(match.strip())
                return True, data
            except json.JSONDecodeError:
                continue

        return False, None

    @staticmethod
    def validate_medical_record(data: Dict) -> Tuple[bool, str]:
        """
        验证医疗记录的 JSON 结构

        Args:
            data: 待验证的数据

        Returns:
            (是否有效, 错误信息)
        """
        # 定义必需字段
        required_fields = [
            "name", "phone", "pet_name", "species", "breed", "weight",
            "deworming", "sterilization", "complaint", "checkup",
            "results", "diagnosis", "treatment"
        ]

        # 检查所有必需字段是否存在
        for field in required_fields:
            if field not in data:
                return False, f"缺少必需字段: {field}"

        # 检查字段类型
        for field in required_fields:
            value = data[field]
            if value is None:
                return False, f"字段 {field} 的值为 None，应为字符串"

            if not isinstance(value, str):
                return False, f"字段 {field} 应为字符串，实际类型: {type(value)}"

        # 检查物种是否在允许范围内
        allowed_species = ["猫", "狗", "其他"]
        if data["species"] and data["species"] not in allowed_species:
            return False, f"物种 {data['species']} 不在允许范围内: {allowed_species}"

        # 检查驱虫/绝育字段
        for field in ["deworming", "sterilization"]:
            value = data[field]
            if value and value not in ["是", "否"]:
                return False, f"字段 {field} 的值应为 '是' 或 '否'，实际值: {value}"

        # 检查体重是否为有效数字
        if data["weight"]:
            try:
                weight = float(data["weight"])
                if weight < 0 or weight > 100:
                    return False, f"体重 {weight} 超出合理范围 (0-100)"
            except ValueError:
                return False, f"体重 '{data['weight']}' 不是有效的数字"

        return True, ""


class LLMRetryHandler:
    """LLM 重试处理器"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化重试处理器

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.validator = LLMResponseValidator()

    async def llm_call_with_retry(
        self,
        llm_call_func,
        *args,
        **kwargs
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        带重试机制的 LLM 调用

        Args:
            llm_call_func: LLM 调用函数
            *args, **kwargs: LLM 调用参数

        Returns:
            (是否成功, JSON 数据或 None, 错误信息或成功信息)
        """
        last_error = ""

        for attempt in range(self.max_retries):
            try:
                logger.info(f"[LLM重试] 第 {attempt + 1}/{self.max_retries} 次尝试")

                # 调用 LLM
                response_text = await llm_call_func(*args, **kwargs)

                if not response_text:
                    last_error = "LLM 返回空响应"
                    logger.warning(f"[LLM重试] {last_error}")
                    continue

                # 提取 JSON
                success, data = self.validator.extract_json(response_text)
                if not success:
                    last_error = "无法从响应中提取有效的 JSON"
                    logger.warning(f"[LLM重试] {last_error}, 响应内容: {response_text[:200]}")
                    continue

                # 验证数据结构
                valid, error_msg = self.validator.validate_medical_record(data)
                if not valid:
                    last_error = f"数据验证失败: {error_msg}"
                    logger.warning(f"[LLM重试] {last_error}")
                    # 如果数据格式错误，不重试（因为重试也是同样的 prompt）
                    break

                # 成功！
                logger.info(f"[LLM重试] 第 {attempt + 1} 次尝试成功")
                return True, data, "成功"

            except Exception as e:
                last_error = f"异常: {str(e)}"
                logger.error(f"[LLM重试] 第 {attempt + 1} 次尝试异常: {last_error}")
                import traceback
                logger.debug(traceback.format_exc())

            # 等待后重试（最后一次不等待）
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)

        logger.error(f"[LLM重试] 所有 {self.max_retries} 次尝试均失败: {last_error}")
        return False, None, last_error


class LLMResponseNormalizer:
    """LLM 响应标准化器"""

    @staticmethod
    def normalize_medical_record(data: Dict) -> Dict:
        """
        标准化医疗记录

        Args:
            data: 原始数据

        Returns:
            标准化后的数据
        """
        normalized = {}

        # 定义所有字段及其默认值和规范化函数
        field_specs = {
            "name": {"default": "", "func": str},
            "phone": {"default": "", "func": lambda x: str(x).strip()},
            "pet_name": {"default": "", "func": str},
            "species": {"default": "", "func": lambda x: str(x).strip()},
            "breed": {"default": "", "func": lambda x: str(x).strip()},
            "weight": {"default": "", "func": lambda x: str(x).strip()},
            "deworming": {"default": "否", "func": lambda x: str(x).strip()},
            "sterilization": {"default": "否", "func": lambda x: str(x).strip()},
            "complaint": {"default": "", "func": str},
            "checkup": {"default": "", "func": str},
            "results": {"default": "", "func": str},
            "diagnosis": {"default": "", "func": str},
            "treatment": {"default": "", "func": str},
        }

        # 应用规范化
        for field, spec in field_specs.items():
            value = data.get(field, spec["default"])

            if value is None:
                normalized[field] = spec["default"]
            elif isinstance(value, str):
                normalized[field] = spec["func"](value)
            else:
                normalized[field] = str(value)

            # 确保不为 None
            if normalized[field] is None:
                normalized[field] = spec["default"]

        return normalized

    @staticmethod
    def ensure_complete(data: Dict) -> Dict:
        """
        确保数据完整，补全缺失字段

        Args:
            data: 原始数据

        Returns:
            完整的数据
        """
        complete_data = LLMResponseNormalizer.normalize_medical_record(data)
        return complete_data


if __name__ == "__main__":
    # 测试代码
    validator = LLMResponseValidator()

    # 测试 JSON 提取
    test_texts = [
        '{"name": "test", "pet_name": "小灰"}',
        '```json\n{"name": "test", "pet_name": "小灰"}\n```',
        '这是文本 ```python\n{"name": "test", "pet_name": "小灰"}\n```结束',
    ]

    for text in test_texts:
        success, data = validator.extract_json(text)
        print(f"提取 {text[:30]}...: {success}, {data}")

    # 测试验证
    valid_data = {
        "name": "",
        "phone": "",
        "pet_name": "小灰",
        "species": "猫",
        "breed": "英短",
        "weight": "3.5",
        "deworming": "否",
        "sterilization": "否",
        "complaint": "呕吐",
        "checkup": "",
        "results": "",
        "diagnosis": "",
        "treatment": ""
    }

    valid, msg = validator.validate_medical_record(valid_data)
    print(f"验证有效数据: {valid}, {msg}")

    # 测试标准化
    normalized = LLMResponseNormalizer.normalize_medical_record(valid_data)
    print(f"标准化结果: {json.dumps(normalized, ensure_ascii=False, indent=2)}")
