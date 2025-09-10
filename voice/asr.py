# 新版 StreamVadAsr：VAD切段 + ASR识别 + ReID打标签
import queue
from threading import Thread
from loguru import logger
from multiprocessing import Queue
from voice.speaker import SpeakerReIDManager
import json
from settings import cfg
from utils.resource_path import get_resource_path
from utils.common import is_meaningful
import traceback
import numpy as np
import traceback
class StreamVadAsr:
    def __init__(self, audio_queue, text_queue, sample_rate=16000):
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self.sample_rate = sample_rate
        self.frame_len = 160  # 10ms 对应的采样点数 (16kHz)
        self.max_segment_len = sample_rate * 15
        # ASR 模型 - 使用动态资源路径
        self.asr_model=cfg.get("asr","model")
        model_path = str(get_resource_path(cfg.get("asr", f"model_{self.asr_model}_path")))
        if self.asr_model == "funasr":
            from funasr import AutoModel
        elif self.asr_model == "vosk":
            import vosk
            
        self.asr_recognizer = AutoModel(model=model_path, model_revision="v2.0.4", disable_update=True) if self.asr_model == "funasr" else vosk.KaldiRecognizer(vosk.Model(model_path) , 16000)
        self.chunk_size = [0, 64, 32]
        self.encoder_chunk_look_back = 4
        self.decoder_chunk_look_back = 1
        self.cache = {}

        # 说话人识别模块
        self.reid = SpeakerReIDManager()
        self.reid.last_speaker = "unknown"  # 添加 last_speaker 记录
        logger.info("[ReID] 说话人识别模块已初始化")

    def _funasr(self,segment):
        res = self.asr_recognizer.generate(
                input=segment,
                cache=self.cache,
                is_final=True,
                chunk_size=self.chunk_size,
                encoder_chunk_look_back=self.encoder_chunk_look_back,
                decoder_chunk_look_back=self.decoder_chunk_look_back
            )

        if res:
            if isinstance(res, list) and 'text' in res[0]:
                return res[0]['text'].strip()
            elif isinstance(res, dict) and 'text' in res:
                return res['text'].strip()
        self.cache.clear()
        return None
    def _vosk(self,segment):
        byte_data = np.array(segment, dtype=np.int16).tobytes()
        if self.asr_recognizer.AcceptWaveform(byte_data):
                result = json.loads(self.asr_recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    logger.info(f"VOSK识别结果: {text}")
                    return text
        else:
                partial = json.loads(self.asr_recognizer.PartialResult())

                logger.debug(f"实时识别: {partial.get('partial', '')}")

            
        
        return None
    def asr(self):
        logger.info("ASR识别线程启动...")
        MIN_EMBED_SAMPLES = int(1 * self.sample_rate)

        while True:
            try:
                
                segment = self.audio_queue.get(timeout=1)
                logger.debug(f"[ASR] 获取音频段，长度: {len(segment)} samples")
                if len(segment) == 0:
                    continue
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"{str(traceback.format_exc())}")
                continue
            try:
                logger.debug(f"[ASR] 获取音频段，长度: {len(segment)} samples,开始识别：")
                text=self._funasr(segment) if self.asr_model=='funasr' else self._vosk(segment )
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"[ASR] 识别失败: {e}")
                continue
            
          
            if not text or not is_meaningful(text):
                        logger.debug(f"[ASR] 丢弃无效内容: {text}")
                        continue
                    # 用整段音频做说话人识别
            try:
                if len(segment) < MIN_EMBED_SAMPLES:
                            speaker_tag = self.reid.last_speaker
                            logger.warning(f"[ReID] 段落过短({len(segment)} samples)，复用前一个 speaker: {speaker_tag}")
                else:
                            speaker_tag = self.reid.get_or_add(segment)
                            self.reid.last_speaker = speaker_tag
            except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error(f"[ReID] 说话人识别失败: {e}")
                        speaker_tag = "unknown"

            logger.info(f"[ASR] speaker: {speaker_tag} text: {text}")
            self.text_queue.put_nowait(json.dumps({"speaker": speaker_tag, "text": text}))
            self.cache.clear()

    def save_thread(self):
        import time
        while True:
            time.sleep(600)
            self.reid.save_cache()
            logger.info("[ReID] 缓存已保存")

    def start(self):
        Thread(target=self.save_thread, daemon=True).start()
        self.asr()
        logger.info("StreamVadAsr 所有线程已启动")

def run(kwargs):
    from utils.loger_util import init_subprocess_logger
    import os
    init_subprocess_logger(os.path.join(cfg.get("app", "save_dir"),"log"),"asr")
    """多进程录音主入口，可被循环控制"""
    audio_queue: Queue = kwargs['audio_queue']
    text_queue: Queue = kwargs['text_queue']
    

    StreamVadAsr(audio_queue,text_queue).start()

