import os
import json
import numpy as np
from pyannote.audio import Model, Inference
from scipy.spatial.distance import cosine
from typing import Optional
import soundfile
import tempfile
from loguru import logger
from settings import cfg
from utils.resource_path import get_resource_path
class SpeakerReIDManager:
    def __init__(self, threshold=0.5, max_speakers=30):
        model_path = str(get_resource_path(cfg.get("spk", "model_pyannote_path")))
        
        model = Model.from_pretrained(checkpoint=os.path.join(model_path, "pytorch_model.bin")
                              , map_location="cpu",
                              hparams_file=os.path.join(model_path, "hparams.yaml"),
                              use_auth_token=None, local_files_only=True)
        self.infer = Inference(model, window="whole")
        self.threshold = threshold
        self.max_speakers = max_speakers  # 最大加载频次top几的说话人
        self.embeddings = np.empty((0, 512))   # 假设embedding维度192，根据模型修改
        self.speaker_ids = []
        self.freqs = {}  # 频次统计 dict {speaker_id: count}
        self.mapping_file = os.path.join(cfg.get("app", "save_dir"), "mapping.json")
        self.embedding_file = os.path.join(cfg.get("app", "save_dir"), "embeddings.npy")
        self.freq_file = os.path.join(cfg.get("app", "save_dir"), "freqs.json")
        self.load_cache()
        self.last_speaker='unknown'  # 添加 last_speaker 记录
        self.sample_rate = 16000

    def extract_embedding(self, wav_data: np.ndarray, sample_rate: int) -> np.ndarray:
        logger.info(f"Input audio length: {len(wav_data)} samples, sample rate: {sample_rate} Hz")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            soundfile.write(tmp.name, wav_data, sample_rate, subtype="PCM_16")
            embedding = self.infer(tmp.name)
        return embedding

    def add(self, speaker_id, embedding):
        self.speaker_ids.append(speaker_id)
        self.embeddings = np.vstack([self.embeddings, embedding[np.newaxis, :]])
        self.freqs[speaker_id] = 1

    def match(self, embedding: np.ndarray) -> Optional[str]:
        if self.embeddings.shape[0] == 0:
            return None
        max_sim = -1.0
        best_spk_id = None
        for spk_id, emb in zip(self.speaker_ids, self.embeddings):
            sim = 1 - cosine(embedding, emb)
            if sim > max_sim:
                max_sim = sim
                best_spk_id = spk_id

        if max_sim > self.threshold:
            logger.debug(f"[ReID] 匹配到已有 speaker: {best_spk_id} (sim={max_sim:.3f})")
            return best_spk_id
        else:
            return None

    def save_cache(self):
        np.save(self.embedding_file, self.embeddings)
        with open(self.mapping_file, "w") as f:
            json.dump(self.speaker_ids, f)
        with open(self.freq_file, "w") as f:
            json.dump(self.freqs, f)

    def load_cache(self):
        if os.path.exists(self.embedding_file) and os.path.exists(self.mapping_file) and os.path.exists(self.freq_file):
            embeddings = np.load(self.embedding_file)
            with open(self.mapping_file, "r") as f:
                speaker_ids = json.load(f)
            with open(self.freq_file, "r") as f:
                freqs = json.load(f)
            
            # 按频次排序，选出top max_speakers
            sorted_speakers = sorted(freqs.items(), key=lambda x: x[1], reverse=True)[:self.max_speakers]
            top_speaker_ids = [s[0] for s in sorted_speakers]
            
            # 过滤embeddings和ids，只保留top_speaker_ids
            filtered_embeddings = []
            filtered_ids = []
            filtered_freqs = {}
            for i, spk_id in enumerate(speaker_ids):
                if spk_id in top_speaker_ids:
                    filtered_embeddings.append(embeddings[i])
                    filtered_ids.append(spk_id)
                    filtered_freqs[spk_id] = freqs.get(spk_id, 0)
            
            self.embeddings = np.array(filtered_embeddings)
            self.speaker_ids = filtered_ids
            self.freqs = filtered_freqs
            logger.info(f"[ReID] 加载缓存成功，加载前{len(speaker_ids)}位，说话人数量限制为{len(self.speaker_ids)}位")
        else:
            self.embeddings = np.empty((0, 512))
            self.speaker_ids = []
            self.freqs = {}

    def get_or_add(self, segment) -> str:
        embedding = self.extract_embedding(segment,self.sample_rate)
        if embedding is None or len(embedding) == 0:
            return "unknown"
        matched = self.match(embedding)
        if matched:
            self.freqs[matched] = self.freqs.get(matched, 0) + 1
            self.last_speaker = matched
            return matched
        new_id = f"{len(self.speaker_ids)}"
        self.add(new_id, embedding)
        self.last_speaker = new_id  # 更新 last_speaker
        return new_id
