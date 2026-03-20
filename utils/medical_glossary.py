#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗术语词典工具
用于 ASR 识别结果的后处理修正
"""
import json
import os
from typing import Dict, List, Optional
from loguru import logger


class MedicalGlossary:
    """医疗术语词典"""

    def __init__(self, glossary_path: Optional[str] = None):
        """
        初始化医疗术语词典

        Args:
            glossary_path: 词典文件路径，如未指定则使用默认路径
        """
        if glossary_path is None:
            # 默认路径：项目根目录下的 data/medical_glossary.json
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            glossary_path = os.path.join(project_root, "data", "medical_glossary.json")

        self.glossary_path = glossary_path
        self.glossary = self._load_glossary()

    def _load_glossary(self) -> Dict:
        """加载词典"""
        try:
            if os.path.exists(self.glossary_path):
                with open(self.glossary_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"[医疗词典] 成功加载词典，包含 {data.get('metadata', {}).get('total_terms', 0)} 个术语")
                return data
            else:
                logger.warning(f"[医疗词典] 词典文件不存在: {self.glossary_path}")
                return {"terms": {}}
        except Exception as e:
            logger.error(f"[医疗词典] 加载词典失败: {e}")
            return {"terms": {}}

    def correct_text(self, text: str) -> str:
        """
        使用词典修正识别结果

        Args:
            text: 原始文本

        Returns:
            修正后的文本
        """
        if not text:
            return text

        corrected = text
        corrections_count = 0

        # 遍历所有术语类别
        terms_dict = self.glossary.get("terms", {})
        for category, data in terms_dict.items():
            corrections = data.get("corrections", {})
            for correct_term, wrong_terms in corrections.items():
                for wrong_term in wrong_terms:
                    # 替换错误的术语
                    if wrong_term in corrected:
                        corrected = corrected.replace(wrong_term, correct_term)
                        corrections_count += 1

        if corrections_count > 0:
            logger.debug(f"[医疗词典] 修正了 {corrections_count} 处")

        return corrected

    def get_terms_by_category(self, category: str) -> Dict:
        """
        获取指定类别的术语

        Args:
            category: 类别名称 (breeds, diseases, medications, symptoms)

        Returns:
            词典映射
        """
        terms_dict = self.glossary.get("terms", {})
        return terms_dict.get(category, {}).get("corrections", {})

    def add_correction(self, category: str, correct_term: str, wrong_terms: List[str]):
        """
        添加新的修正规则

        Args:
            category: 类别名称
            correct_term: 正确的术语
            wrong_terms: 错误的术语列表
        """
        terms_dict = self.glossary.get("terms", {})

        if category not in terms_dict:
            terms_dict[category] = {"description": category, "corrections": {}}

        corrections = terms_dict[category].get("corrections", {})
        if correct_term not in corrections:
            corrections[correct_term] = []
        corrections[correct_term].extend(wrong_terms)
        terms_dict[category]["corrections"] = corrections
        self.glossary["terms"] = terms_dict

        logger.info(f"[医疗词典] 添加修正规则: {category}/{correct_term}")

    def save_glossary(self):
        """保存词典到文件"""
        try:
            with open(self.glossary_path, 'w', encoding='utf-8') as f:
                json.dump(self.glossary, f, ensure_ascii=False, indent=2)
            logger.info(f"[医疗词典] 词典已保存到: {self.glossary_path}")
        except Exception as e:
            logger.error(f"[医疗词典] 保存词典失败: {e}")

    def print_statistics(self):
        """打印词典统计信息"""
        terms_dict = self.glossary.get("terms", {})
        metadata = self.glossary.get("metadata", {})

        logger.info("\n" + "="*60)
        logger.info("医疗术语词典统计")
        logger.info("="*60)
        logger.info(f"版本: {metadata.get('version', 'N/A')}")
        logger.info(f"创建时间: {metadata.get('created', 'N/A')}")
        logger.info(f"总术语数: {metadata.get('total_terms', 0)}")
        logger.info("\n分类统计:")

        for category, data in terms_dict.items():
            desc = data.get("description", "")
            corrections = data.get("corrections", {})
            count = len(corrections)
            logger.info(f"  {category:15s}: {count:3d} 个 正确术语")

        logger.info("="*60 + "\n")


# 全局单例
_glossary_instance = None


def get_glossary() -> MedicalGlossary:
    """获取医疗术语词典单例"""
    global _glossary_instance
    if _glossary_instance is None:
        _glossary_instance = MedicalGlossary()
    return _glossary_instance


if __name__ == "__main__":
    # 测试代码
    glossary = MedicalGlossary()
    glossary.print_statistics()

    # 测试修正
    test_texts = [
        "我家有一只黄金，最近它总是吐和拉稀",
        "这是一只边牧，它得了细小，需要注射庆大",
        "猫出现萨罗的症状，不吃不喝，精神不好"
    ]

    logger.info("\n测试文本修正:")
    for i, text in enumerate(test_texts, 1):
        corrected = glossary.correct_text(text)
        logger.info(f"{i}. 原文: {text}")
        logger.info(f"   修正: {corrected}\n")
