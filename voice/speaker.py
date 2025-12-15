import os
import json
import numpy as np
from pyannote.audio import Model, Inference
import soundfile
import tempfile
from loguru import logger
from settings import cfg
from utils.resource_path import get_resource_path

class SpeakerReIDManager:
    def __init__(self, threshold=0.5, max_speakers=30):
        model_path = str(get_resource_path(cfg.get("spk", "model_pyannote_path")))
        # 使用 pyannote 的 from_pretrained 接口时，请传入正确参数（这里假定本地文件结构正确）
        # 你原来用的方式已经能加载模型，这里保留同样方式
        model = Model.from_pretrained(
            checkpoint=os.path.join(model_path, "pytorch_model.bin"),
            map_location=cfg.get("spk", "device"),
            hparams_file=os.path.join(model_path, "hparams.yaml"),
            use_auth_token=None,
            local_files_only=True
        )
        self.infer = Inference(model, window="whole")
        self.threshold = threshold
        self.max_speakers = max_speakers

        # 动态决定 embedding 维度（首次提取后设置）
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
        """把 numpy wav_data 写到临时 wav 文件，然后用 pyannote Inference 提取 embedding"""
        logger.info(f"[ReID] 输入音频长度: {len(wav_data)} samples, sr={sample_rate}")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            soundfile.write(tmp.name, wav_data, sample_rate, subtype="PCM_16")
            emb = self.infer(tmp.name)

        emb = np.asarray(emb, dtype=np.float32).flatten()
        if emb.size == 0:
            logger.warning("[ReID] 提取到空 embedding")
            return None

        # 如果此前没有设置过 embedding_dim，则设置
        if self.embedding_dim is None:
            self.embedding_dim = emb.shape[0]
            logger.info(f"[ReID] 确认 embedding_dim = {self.embedding_dim}")
        return emb

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
