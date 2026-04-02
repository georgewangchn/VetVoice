# -*- coding: utf-8 -*-

import os
import json
import numpy as np
from pathlib import Path
from loguru import logger
import hashlib


class VoiceprintManager:
    """声纹识别管理器"""

    def __init__(self):
        # 声纹存储目录
        self.voiceprint_dir = Path.home() / ".vetvoice" / "voiceprints"
        self.voiceprint_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self.metadata_file = self.voiceprint_dir / "metadata.json"

        # 医生声纹库 {姓名: embedding}
        self.doctor_voiceprints = {}

        # 加载已保存的声纹
        self.load_voiceprints()

    def load_voiceprints(self):
        """加载已保存的医生声纹"""
        self.doctor_voiceprints = {}

        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                for doctor_name, info in metadata.items():
                    # 兼性不同数据格式
                    if not isinstance(info, dict):
                        continue

                    # 新格式：包含 'voiceprints' 数组
                    if 'voiceprints' in info:
                        voiceprints = info['voiceprints']
                        if voiceprints:  # 使用第一条声纹
                            vp_info = voiceprints[0]
                            voiceprint_file = Path(vp_info.get('file_path', ''))
                            if voiceprint_file.exists():
                                try:
                                    data = np.load(voiceprint_file)
                                    embedding = data['embedding'] if 'embedding' in data else data['arr_0']
                                    self.doctor_voiceprints[doctor_name] = embedding
                                    logger.info(f"✅ 加载医生声纹: {doctor_name}")
                                except Exception as e:
                                    logger.warning(f"加载声纹失败 {doctor_name}: {e}")

                    # 旧格式：直接包含 'file_path'
                    elif 'file_path' in info:
                        voiceprint_file = Path(info['file_path'])
                        if voiceprint_file.exists():
                            try:
                                # 加载声纹
                                data = np.load(voiceprint_file)
                                embedding = data['embedding'] if 'embedding' in data else data['arr_0']
                                self.doctor_voiceprints[doctor_name] = embedding
                                logger.info(f"✅ 加载医生声纹: {doctor_name}")
                            except Exception as e:
                                logger.warning(f"加载声纹失败 {doctor_name}: {e}")

            except Exception as e:
                logger.error(f"加载声纹元数据失败: {e}")
                import traceback
                logger.error(traceback.format_exc())

        logger.info(f"当前已加载 {len(self.doctor_voiceprints)} 个医生声纹")

    def identify_speaker(self, audio_data, sample_rate=16000, threshold=0.8):
        """
        识别音频中的说话人

        Args:
            audio_data: 音频数据 (numpy array)
            sample_rate: 采样率
            threshold: 匹配阈值 (0-1)

        Returns:
            tuple: (说话人名称, 匹配分数) 或 ("用户", None)
        """
        if not self.doctor_voiceprints:
            return "用户", None

        try:
            # 提取当前音频的声纹特征
            current_embedding = self.extract_features(audio_data, sample_rate)

            if current_embedding is None:
                return "用户", None

            # 匹配最近的医生声纹
            best_match = None
            best_score = -1

            for doctor_name, doctor_embedding in self.doctor_voiceprints.items():
                # 计算相似度（余弦相似度）
                similarity = self.compute_similarity(current_embedding, doctor_embedding)

                if similarity > best_score:
                    best_score = similarity
                    best_match = doctor_name

            # 根据阈值判断
            if best_match and best_score >= threshold:
                logger.info(f"识别到医生: {best_match} (相似度: {best_score:.3f})")
                return best_match, best_score
            else:
                return "用户", best_score

        except Exception as e:
            logger.error(f"声纹识别失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "用户", None

    def extract_features(self, audio_data, sample_rate):
        """提取音频特征"""
        try:
            # 简化的特征提取（与声纹对话框中的方法保持一致）
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

            # 尝试添加频域特征
            try:
                import librosa
                # 计算MFCC特征
                mfcc = librosa.feature.mfcc(y=audio_data.astype(np.float32),
                                            sr=sample_rate, n_mfcc=13)
                mfcc_mean = np.mean(mfcc, axis=1)

                # 扩展特征向量
                if len(mfcc_mean) <= 256:
                    features = features[:256 - len(mfcc_mean)]
                    features = np.concatenate([features, mfcc_mean])
            except ImportError:
                pass  # librosa未安装，只使用时域特征

            return features.astype(np.float32)

        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return None

    def compute_similarity(self, embedding1, embedding2):
        """计算两个embedding之间的相似度（余弦相似度）"""
        try:
            # 确保维度一致
            if embedding1.shape != embedding2.shape:
                min_dim = min(embedding1.shape[0], embedding2.shape[0])
                embedding1 = embedding1[:min_dim]
                embedding2 = embedding2[:min_dim]

            # 归一化
            embedding1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
            embedding2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)

            # 余弦相似度
            similarity = np.dot(embedding1, embedding2)
            return float(similarity)

        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return 0.0

    def has_doctors(self):
        """检查是否有已录入的医生声纹"""
        return len(self.doctor_voiceprints) > 0

    def get_doctor_names(self):
        """获取所有已录入的医生姓名"""
        return list(self.doctor_voiceprints.keys())


# 全局单例
_voiceprint_manager = None


def get_voiceprint_manager():
    """获取全局声纹识别管理器"""
    global _voiceprint_manager
    if _voiceprint_manager is None:
        _voiceprint_manager = VoiceprintManager()
    return _voiceprint_manager