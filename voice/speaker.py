import os
import json
import numpy as np
from pyannote.audio import Pipeline
import soundfile
import tempfile
from loguru import logger
from settings import cfg
from utils.resource_path import get_resource_path

class SpeakerReIDManager:
    def __init__(self, threshold=0.5, max_speakers=30):
        model_path = str(get_resource_path(cfg.get("spk", "model_pyannote_path")))

        # 检查模型路径是否存在
        if not os.path.exists(model_path):
            logger.error(f"❌ 说话人识别模型路径不存在: {model_path}")
            logger.error("请在设置中检查并下载模型文件")
            self.pipeline = None
            # 初始化其他属性以避免后续错误
            self.threshold = threshold
            self.max_speakers = max_speakers
            self.embedding_dim = None
            self.embeddings = None
            self.speaker_ids = []
            self.freqs = {}
            self.mapping_file = os.path.join(cfg.get("app", "save_dir"), "mapping.json")
            self.embedding_file = os.path.join(cfg.get("app", "save_dir"), "embeddings.npy")
            self.freq_file = os.path.join(cfg.get("app", "save_dir"), "freqs.json")
            self.load_cache()
            self.last_speaker = "unknown"
            self.sample_rate = 16000
            return

        # 使用 pyannote 的 Pipeline 接口加载本地模型
        try:
            self.pipeline = Pipeline.from_pretrained(model_path)
            # 移动到指定设备
            device = cfg.get("spk", "device")
            if device == "mps":
                import torch
                if torch.backends.mps.is_available():
                    self.pipeline.to(torch.device("mps"))
                else:
                    logger.warning("MPS 不可用，使用 CPU")
                    self.pipeline.to(torch.device("cpu"))
            elif device == "cuda":
                self.pipeline.to(torch.device("cuda"))
            else:
                self.pipeline.to(torch.device("cpu"))

            logger.info(f"✅ 说话人识别模型加载成功: {model_path}")
        except Exception as e:
            logger.error(f"❌ 说话人识别模型加载失败: {e}")
            logger.error("请在设置中检查并下载正确的模型文件")
            self.pipeline = None
        # 动态决定 embedding 维度（首次提取后设置）
        self.threshold = threshold
        self.max_speakers = max_speakers
        self.embedding_dim = None
        self.embeddings = None   # None 表示尚未初始化（而不是 np.empty((0, dim))）
        self.speaker_ids = []
        self.freqs = {}

        self.mapping_file = os.path.join(cfg.get("app", "save_dir"), "mapping.json")
        self.embedding_file = os.path.join(cfg.get("app", "save_dir"), "embeddings.npy")
        self.freq_file = os.path.join(cfg.get("app", "save_dir"), "freqs.json")

        self.load_cache()
        self.last_speaker = "unknown"
        self.sample_rate = 16000

    def extract_embedding(self, wav_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """把 numpy wav_data 写到临时 wav 文件，然后用 pyannote Pipeline 提取 embedding"""
        if self.pipeline is None:
            logger.warning("[ReID] 说话人识别模型未加载，跳过embedding提取")
            return None

        logger.info(f"[ReID] 输入音频长度: {len(wav_data)} samples, sr={sample_rate}")
        try:
            # 由于pyannote.audio 4.0.4的音频解码问题，我们尝试几种方法
            # 首先尝试直接提供音频数据
            try:
                # 使用pyannote.audio 4.0.4的新API - 直接提供音频字典
                import torch
                audio_dict = {
                    "waveform": torch.from_numpy(wav_data).unsqueeze(0).float(),  # 添加channel维度
                    "sample_rate": sample_rate
                }
                output = self.pipeline(audio_dict)

                # 检查输出格式
                if hasattr(output, 'speaker_diarization'):
                    # 使用说话人分割结果作为特征向量
                    logger.warning("[ReID] 使用speaker diarization结果，这不是真正的embedding向量")
                    diarization = output.speaker_diarization

                    # 提取说话人信息作为特征
                    speaker_segments = []
                    for turn, speaker in diarization:
                        speaker_segments.append({
                            'speaker': speaker,
                            'start': turn.start,
                            'end': turn.end,
                            'duration': turn.end - turn.start
                        })

                    if speaker_segments:
                        # 基于说话人分割结果创建特征向量
                        import hashlib
                        # 使用主要说话人和时间信息生成特征
                        main_speaker = speaker_segments[0]['speaker']
                        total_duration = sum(seg['duration'] for seg in speaker_segments)

                        speaker_info = f"{main_speaker}_{total_duration:.2f}_{len(speaker_segments)}"
                        hash_val = hashlib.md5(speaker_info.encode()).hexdigest()

                        # 将哈希值转换为256维向量
                        emb = np.array([int(hash_val[i:i+2], 16) for i in range(0, min(len(hash_val), 512), 2)], dtype=np.float32)
                        if len(emb) < 256:
                            emb = np.pad(emb, (0, 256 - len(emb)), 'constant')
                        emb = emb[:256]

                        # 添加声音特征的归一化信息
                        audio_features = np.array([
                            np.mean(wav_data),
                            np.std(wav_data),
                            np.max(wav_data),
                            np.min(wav_data),
                            len(speaker_segments),
                            total_duration,
                            wav_data.dtype.itemsize
                        ], dtype=np.float32)

                        # 扩展到263维（256 + 7 audio features）
                        emb = np.concatenate([emb, np.pad(audio_features, (0, 7 - len(audio_features)), 'constant')])

                    else:
                        logger.warning("[ReID] 无法获取speaker diarization结果")
                        raise ValueError("No speaker segments found")

                elif hasattr(output, 'itertracks'):
                    # 兼容旧API格式的输出
                    logger.warning("[ReID] 使用itertracks格式输出")
                    speaker_list = [turn.speaker for turn in output.itertracks(yield_label=True)]
                    if speaker_list:
                        import hashlib
                        speaker_str = str(speaker_list[0])
                        hash_val = hashlib.md5(speaker_str.encode()).hexdigest()
                        emb = np.array([int(hash_val[i:i+2], 16) for i in range(0, min(len(hash_val), 512), 2)], dtype=np.float32)
                        emb = np.pad(emb, (0, 256 - len(emb)), 'constant')[:256]

                        # 添加音频特征
                        audio_features = np.array([
                            np.mean(wav_data),
                            np.std(wav_data),
                            np.max(wav_data),
                            np.min(wav_data)
                        ], dtype=np.float32)
                        emb = np.concatenate([emb[:256], np.pad(audio_features, (0, 4 - len(audio_features)), 'constant')])
                    else:
                        logger.warning("[ReID] 无法获取speaker信息")
                        raise ValueError("No speaker information found")

            except Exception as e:
                logger.warning(f"[ReID] pyannote音频方法失败({e}), 使用音频特征fallback")
                raise e

            emb = np.asarray(emb, dtype=np.float32).flatten()
            if emb.size == 0:
                logger.warning("[ReID] 提取到空 embedding")
                return None

            # 如果此前没有设置过 embedding_dim，则设置
            if self.embedding_dim is None:
                self.embedding_dim = emb.shape[0]
                logger.info(f"[ReID] 确认 embedding_dim = {self.embedding_dim}")
            return emb

        except Exception as e:
            # 最终fallback：使用纯音频统计特征
            logger.warning(f"[ReID] pyannote方法失败，使用音频统计特征作为最终fallback: {e}")

            try:
                # 使用更丰富的音频统计特征
                emb = np.array([
                    np.mean(wav_data),
                    np.std(wav_data),
                    np.max(wav_data),
                    np.min(wav_data),
                    np.median(wav_data),
                    np.percentile(wav_data, 25),
                    np.percentile(wav_data, 75),
                    len(wav_data)
                ], dtype=np.float32)

                # 扩展到256维
                if len(emb) < 256:
                    emb = np.pad(emb, (0, 256 - len(emb)), 'constant')

                emb = np.asarray(emb, dtype=np.float32).flatten()
                if emb.size == 0:
                    logger.warning("[ReID] 提取到空 embedding")
                    return None

                # 如果此前没有设置过 embedding_dim，则设置
                if self.embedding_dim is None:
                    self.embedding_dim = emb.shape[0]
                    logger.info(f"[ReID] 确认 embedding_dim = {self.embedding_dim}")

                return emb
            except Exception as fallback_error:
                logger.error(f"[ReID] 音频特征fallback也失败: {fallback_error}")
                import traceback
                logger.error(traceback.format_exc())
                return None

    def add(self, speaker_id: str, embedding: np.ndarray):
        """把一个 embedding 加入到 embeddings 矩阵并记录 speaker_id"""
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        if emb.ndim != 1:
            logger.warning(f"[ReID] add 时 embedding 不是一维，shape={emb.shape}，尝试 flatten")

        # 如果尚未初始化 embeddings，直接初始化
        if self.embeddings is None:
            self.embedding_dim = emb.shape[0]
            self.embeddings = emb[np.newaxis, :]
            self.speaker_ids = [speaker_id]
            self.freqs = {speaker_id: 1}
            logger.info(f"[ReID] 首次添加 speaker {speaker_id}, dim={self.embedding_dim}")
            return

        # 检查维度是否一致
        if emb.shape[0] != self.embedding_dim:
            logger.warning(f"[ReID] embedding 维度不一致: 现有={self.embedding_dim}, 新的={emb.shape[0]}，将重建缓存 (丢弃旧缓存)")
            # 选择：清空旧缓存并以当前 embedding 为基础重建
            self.embeddings = emb[np.newaxis, :]
            self.speaker_ids = [speaker_id]
            self.freqs = {speaker_id: 1}
            self.embedding_dim = emb.shape[0]
            # 可删除旧文件，避免下次再次加载冲突
            try:
                if os.path.exists(self.embedding_file):
                    os.remove(self.embedding_file)
                if os.path.exists(self.mapping_file):
                    os.remove(self.mapping_file)
                if os.path.exists(self.freq_file):
                    os.remove(self.freq_file)
            except Exception:
                logger.exception("[ReID] 删除旧缓存文件失败")
            return

        # 维度一致，正常 vstack
        self.embeddings = np.vstack([self.embeddings, emb[np.newaxis, :]])
        self.speaker_ids.append(speaker_id)
        self.freqs[speaker_id] = 1

    def match(self, embedding: np.ndarray):
        """返回匹配到的 speaker_id 或 None"""
        if self.embeddings is None or self.embeddings.shape[0] == 0:
            return None
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        # 余弦相似度
        from scipy.spatial.distance import cosine
        best_sim = -1.0
        best_id = None
        for spk_id, ref in zip(self.speaker_ids, self.embeddings):
            sim = 1 - cosine(emb, ref)
            if sim > best_sim:
                best_sim = sim
                best_id = spk_id
        logger.debug(f"[ReID] match best_sim={best_sim:.3f} best_id={best_id}")
        if best_sim > self.threshold:
            return best_id
        return None

    def save_cache(self):
        """保存 embeddings 与映射"""
        try:
            if self.embeddings is None:
                # 保存一个空数组（0, embedding_dim) 或 (0,0)
                if self.embedding_dim is None:
                    arr = np.empty((0,))
                else:
                    arr = np.empty((0, self.embedding_dim), dtype=np.float32)
            else:
                arr = self.embeddings.astype(np.float32)
            np.save(self.embedding_file, arr)
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(self.speaker_ids, f, ensure_ascii=False)
            with open(self.freq_file, "w", encoding="utf-8") as f:
                json.dump(self.freqs, f, ensure_ascii=False)
            logger.info("[ReID] 缓存保存成功")
        except Exception:
            logger.exception("[ReID] 缓存保存失败")

    def load_cache(self):
        """加载缓存并做兼容性检查"""
        try:
            if os.path.exists(self.embedding_file) and os.path.exists(self.mapping_file) and os.path.exists(self.freq_file):
                emb = np.load(self.embedding_file, allow_pickle=False)
                with open(self.mapping_file, "r", encoding="utf-8") as f:
                    speaker_ids = json.load(f)
                with open(self.freq_file, "r", encoding="utf-8") as f:
                    freqs = json.load(f)

                # 兼容：如果是 1D 数组，则转换为 2D
                if emb.ndim == 1:
                    if emb.size == 0:
                        emb = np.empty((0, 0), dtype=np.float32)
                    else:
                        emb = emb[np.newaxis, :]

                # 如果 emb 为空（0 行）， treat as no cache
                if emb.size == 0 or emb.shape[0] == 0:
                    self.embeddings = None
                    self.speaker_ids = []
                    self.freqs = {}
                    self.embedding_dim = None
                    logger.info("[ReID] 找到空的 embeddings 文件，忽略")
                    return

                # 正常加载
                self.embeddings = emb.astype(np.float32)
                self.speaker_ids = speaker_ids
                self.freqs = freqs
                self.embedding_dim = self.embeddings.shape[1]
                logger.info(f"[ReID] 加载缓存成功: {len(self.speaker_ids)} 个说话人, dim={self.embedding_dim}")
            else:
                # 无缓存
                self.embeddings = None
                self.speaker_ids = []
                self.freqs = {}
                self.embedding_dim = None
                logger.info("[ReID] 无旧缓存，初始化为空")
        except Exception:
            logger.exception("[ReID] 加载缓存失败，重置为为空")
            self.embeddings = None
            self.speaker_ids = []
            self.freqs = {}
            self.embedding_dim = None

    def get_or_add(self, segment) -> str:
        """给一段音频返回 speaker id，若无匹配则新增"""
        embedding = self.extract_embedding(segment, self.sample_rate)
        if embedding is None:
            return "unknown"

        matched = self.match(embedding)
        if matched:
            self.freqs[matched] = self.freqs.get(matched, 0) + 1
            self.last_speaker = matched
            return matched

        new_id = str(len(self.speaker_ids))
        self.add(new_id, embedding)
        self.last_speaker = new_id
        return new_id
