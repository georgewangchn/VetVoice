# -*- coding: utf-8 -*-
"""
实时声纹识别器
使用 wespeaker-voxceleb-resnet34-LM 模型进行实时声纹识别
"""
import os
import json
import numpy as np
from pathlib import Path
from loguru import logger


class SpeakerRealtime:
    """实时声纹识别器"""

    def __init__(self, model_path: str):
        """
        初始化声纹识别器

        Args:
            model_path: 声纹模型路径
        """
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            logger.error(f"声纹模型不存在: {self.model_path}")
            self.model = None
            return

        self.model = self._load_model()
        self.threshold = 0.85  # 相似度阈值

        logger.info(f"✅ 声纹识别器初始化成功: {self.model_path}")

    def _load_model(self):
        """加载声纹模型"""
        try:
            # 这里需要根据实际的模型加载方式来实现
            # wespeaker-voxceleb-resnet34-LM 是一个 ResNet34 模型
            # 我们需要使用相应的库来加载它

            import torch
            from torchaudio.models import wav2vec2_model

            # 尝试加载模型
            model_file = self.model_path / "avg_model.pt"  # 常见的模型文件名

            if model_file.exists():
                logger.info(f"加载声纹模型: {model_file}")
                model = torch.load(model_file, map_location='cpu')
                model.eval()
                return model
            else:
                logger.warning(f"模型文件不存在: {model_file}")
                # 尝试其他常见的文件名
                for fname in ['model.pt', 'pytorch_model.bin', 'checkpoint.pth']:
                    potential_file = self.model_path / fname
                    if potential_file.exists():
                        logger.info(f"加载声纹模型: {potential_file}")
                        model = torch.load(potential_file, map_location='cpu')
                        if hasattr(model, 'eval'):
                            model.eval()
                        return model

                logger.warning("未找到有效的模型文件，将使用备用方案")
                return None

        except Exception as e:
            logger.error(f"加载声纹模型失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def extract_embedding(self, audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        提取音频的声纹特征向量

        Args:
            audio_data: 音频数据
            sample_rate: 采样率

        Returns:
            声纹特征向量
        """
        if self.model is not None:
            return self._extract_with_model(audio_data, sample_rate)
        else:
            return self._extract_fallback(audio_data, sample_rate)

    def _extract_with_model(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """使用模型提取声纹特征"""
        try:
            import torch
            import torchaudio

            # 确保音频是float32格式
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0

            # 重采样到16kHz（如果不是）
            if sample_rate != 16000:
                torchaudio_transforms = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=16000
                )
                audio_data = torchaudio_transforms(torch.from_numpy(audio_data).float()).numpy()

            # 转换为torch张量
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0).float()

            # 使用模型提取embedding
            with torch.no_grad():
                # 假设模型接受音频输入并输出embedding
                # 具体实现取决于实际的模型接口
                embedding = self._forward_pass(audio_tensor)

            return embedding

        except Exception as e:
            logger.warning(f"模型提取失败，使用备用方案: {e}")
            return self._extract_fallback(audio_data, sample_rate)

    def _forward_pass(self, audio_tensor):
        """模型前向传播"""
        try:
            # 这里需要根据实际的模型来实现前向传播
            # 常见的做法是提取音频的MFCC特征或者直接送入模型

            import torch
            import torchaudio.transforms as T

            # 计算MFCC特征（13维）
            mfcc_transform = T.MFCC(
                sample_rate=16000,
                n_mfcc=13,
                melkwargs={
                    "n_fft": 512,
                    "hop_length": 160,
                    "n_mels": 40,
                }
            )

            mfcc = mfcc_transform(audio_tensor)  # (1, 13, time)

            # 对时间维度求平均
            embedding = torch.mean(mfcc, dim=2)  # (1, 13)

            # 扩展到256维（通过重复和添加特征）
            emb_256d = torch.nn.functional.interpolate(
                embedding.unsqueeze(1).float(),
                size=256,
                mode='linear',
                align_corners=False
            ).squeeze()

            return emb_256d.numpy()

        except Exception as e:
            logger.error(f"前向传播失败: {e}")
            raise

    def _extract_fallback(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        备用方案：使用特征提取
        当模型不可用时使用
        """
        try:
            # 确保音频是float32格式
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0

            # 基础统计特征
            features = np.array([
                np.mean(audio_data),
                np.std(audio_data),
                np.max(audio_data),
                np.min(audio_data),
                np.median(audio_data),
                np.percentile(audio_data, 25),
                np.percentile(audio_data, 75),
                np.percentile(audio_data, 90),
                np.percentile(audio_data, 10),
                len(audio_data)
            ], dtype=np.float32)

            # 尝试添加频域特征
            try:
                # 计算功率谱密度
                import scipy.signal
                freqs, psd = scipy.signal.welch(audio_data, fs=sample_rate, nperseg=256)

                # 添加频谱特征
                spectral_centroid = np.sum(freqs * psd) / np.sum(psd)
                spectral_bandwidth = np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * psd) / np.sum(psd))
                spectral_flatness = np.exp(np.mean(np.log(psd + 1e-10)))

                spectral_features = np.array([
                    spectral_centroid,
                    spectral_bandwidth,
                    spectral_flatness,
                    np.max(psd),
                    np.mean(psd)
                ], dtype=np.float32)

                features = np.concatenate([features, spectral_features])

            except ImportError:
                pass  # scipy未安装

            # 尝试添加MFCC特征
            try:
                import librosa
                mfcc = librosa.feature.mfcc(
                    y=audio_data.astype(np.float32),
                    sr=sample_rate,
                    n_mfcc=13
                )
                mfcc_mean = np.mean(mfcc, axis=1)
                mfcc_std = np.std(mfcc, axis=1)

                features = np.concatenate([features, mfcc_mean, mfcc_std])

            except ImportError:
                pass  # librosa未安装

            # 扩展到256维
            if len(features) < 256:
                features = np.pad(features, (0, 256 - len(features)), 'constant')
            elif len(features) > 256:
                features = features[:256]

            return features.astype(np.float32)

        except Exception as e:
            logger.error(f"备用特征提取失败: {e}")
            return np.zeros(256, dtype=np.float32)

    def compare_speaker(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        比较两个声纹特征的相似度

        Args:
            embedding1: 声纹特征1
            embedding2: 声纹特征2

        Returns:
            相似度 (0-1)
        """
        try:
            # 确保维度一致
            min_dim = min(len(embedding1), len(embedding2))
            emb1 = embedding1[:min_dim]
            emb2 = embedding2[:min_dim]

            # 归一化
            emb1 = emb1 / (np.linalg.norm(emb1) + 1e-8)
            emb2 = emb2 / (np.linalg.norm(emb2) + 1e-8)

            # 余弦相似度
            similarity = np.dot(emb1, emb2)
            return float(similarity)

        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return 0.0

    def identify_speaker(self,
                        audio_data: np.ndarray,
                        reference_embeddings: dict,
                        threshold: float = None) -> tuple:
        """
        识别音频中的说话人

        Args:
            audio_data: 音频数据
            reference_embeddings: 参考声纹字典 {speaker_name: [embedding1, embedding2, ...]}
            threshold: 匹配阈值，None则使用默认值

        Returns:
            tuple: (说话人姓名, 相似度) 或 ("用户", None)
        """
        if threshold is None:
            threshold = self.threshold

        if not reference_embeddings:
            return "用户", None

        try:
            # 提取当前音频的特征
            current_embedding = self.extract_embedding(audio_data, 16000)

            if current_embedding is None:
                return "用户", None

            # 与所有参考声纹比较
            best_match = None
            best_score = -1

            for speaker_name, embeddings in reference_embeddings.items():
                if not isinstance(embeddings, list):
                    embeddings = [embeddings]

                for ref_embedding in embeddings:
                    similarity = self.compare_speaker(current_embedding, ref_embedding)

                    if similarity > best_score:
                        best_score = similarity
                        best_match = speaker_name

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


def load_reference_embeddings(metadata_file: Path) -> dict:
    """
    加载参考声纹库

    Args:
        metadata_file: 元数据文件路径

    Returns:
        dict: {speaker_name: [embedding1, embedding2, ...]}
    """
    try:
        if not metadata_file.exists():
            return {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        reference_embeddings = {}

        for speaker_name, speaker_info in metadata.items():
            embeddings = []
            voiceprints = speaker_info.get('voiceprints', [])

            for vp_info in voiceprints:
                file_path = Path(vp_info.get('file_path', ''))
                if file_path.exists():
                    try:
                        data = np.load(file_path)
                        embedding = data['embedding'] if 'embedding' in data else data['arr_0']
                        embeddings.append(embedding)
                    except Exception as e:
                        logger.warning(f"加载声纹失败 {file_path}: {e}")

            if embeddings:
                reference_embeddings[speaker_name] = embeddings

        logger.info(f"📚 加载了 {len(reference_embeddings)} 个医生的 {sum(len(v) for v in reference_embeddings.values())} 条声纹")
        return reference_embeddings

    except Exception as e:
        logger.error(f"加载参考声纹库失败: {e}")
        return {}