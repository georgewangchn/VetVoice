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
import tempfile
import soundfile
MIN_ASR_SECONDS = 1.8
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
            
        # self.asr_recognizer = AutoModel(model=model_path, model_revision="v2.0.4", disable_update=True,device=cfg.get("asr",'device')) if self.asr_model == "funasr" else vosk.KaldiRecognizer(vosk.Model(model_path) , 16000)
        self.asr_recognizer=AutoModel(model="FunAudioLLM/Fun-ASR-Nano-2512",
                                      trust_remote_code=True,
                                      disable_update=True,
                                      remote_code="./model.py",
                                      device="mps")
        self.asr_buffer = []
        self.asr_text_buffer=''
        self.asr_text=''
        self.asr_buffer_len = 0
        self.min_asr_smaples = int(MIN_ASR_SECONDS * self.sample_rate)
        self.min_embed_smaples = int(MIN_ASR_SECONDS * self.sample_rate)
        self.chunk_size = [0, 64, 32]
        self.encoder_chunk_look_back = 4
        self.decoder_chunk_look_back = 1
        self.cache = {}
        

        # 说话人识别模块
        self.reid = SpeakerReIDManager()
        self.re_buffer=[]
        self.reid.last_speaker = "unknown"  # 添加 last_speaker 记录
        logger.info("[ReID] 说话人识别模块已初始化")
        



    def _funasr(self,segment, is_final: bool=False):
        try:
            if segment.dtype != np.float32:
                segment = segment.astype(np.float32) / 32768.0
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                # 写入音频数据，假设采样率为16000Hz，可调整
                soundfile.write(tmp.name, segment, 16000, format='WAV', subtype='PCM_16')
                res = self.asr_recognizer.generate(
                        input=[tmp.name],
                        cache=self.cache,
                        is_final=is_final,
                        batch_size=1
                    )
                # .generate(input=[wav_path], cache={}, batch_size=1)
            if not res:
                return None
            else:
                if isinstance(res, list) and 'text' in res[0]:
                    print(self.cache,res[0]['text'])
                    return res[0]['text'].strip()
                elif isinstance(res, dict) and 'text' in res:
                    print(self.cache,res['text'])
                    return res['text'].strip()
            return None
        except:
             logger.error(f"[ASR] 识别失败: {str(traceback.format_exc())}")
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

        while True:
            try:
                
                frame ,is_final= self.audio_queue.get(timeout=1)
                logger.debug(f"[ASR] 获取音频段，长度: {len(frame)} samples")
                if  frame is None or is_final is None:
                    continue
         
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"{str(traceback.format_exc())}")
                continue
            
            # ===== 累积 =====
            if  frame is not None and len(frame)>0:
                self.asr_buffer.append(frame)
                self.re_buffer.append(frame)
                self.asr_buffer_len += len(frame)
            # ===== 是否asr=====
            if is_final:
                if self.asr_buffer_len>=int(0.1 * self.sample_rate):
                # ===== 拼接整句 =====
                    segment = np.concatenate(self.asr_buffer)
                    self.asr_buffer.clear()
                    self.asr_buffer_len = 0
                    text=self._funasr(segment,True) if self.asr_model=='funasr' else self._vosk(segment )
                    self.asr_text_buffer += text if  is_meaningful(text) else ''
                    self.cache.clear()
                    self.asr_text=self.asr_text_buffer
                    self.asr_text_buffer=''
            # elif self.asr_buffer_len >= self.min_asr_smaples:
            #     segment = np.concatenate(self.asr_buffer)
            #     self.asr_buffer.clear()
            #     self.asr_buffer_len = 0
            #     text=self._funasr(segment,False) if self.asr_model=='funasr' else self._vosk(segment )
            #     self.text_queue.put_nowait(json.dumps({"speaker": '.', "text": text}))
            #     self.asr_text_buffer += text if  is_meaningful(text) else ''
            #     continue
            else:
                continue    
            
            # ========== Speaker ReID（只在 final 做） ==========
            speaker_tag = "unknown"

            try:
                if len(self.re_buffer)>0:
                    segment = np.concatenate(self.re_buffer)
                    self.re_buffer.clear()
                    if len(segment) < self.min_asr_smaples:
                        speaker_tag = self.reid.last_speaker
                        logger.warning(f"[ReID] 段落过短({len(segment)} samples)，复用前一个 speaker: {speaker_tag}")
                    else:
                        speaker_tag = self.reid.get_or_add(segment)
                        self.reid.last_speaker = speaker_tag
            except Exception as e:
                    logger.error(f"[ReID] 说话人识别失败: {str(traceback.format_exc())}")
                    speaker_tag = "unknown"

            logger.info(f"[ASR] speaker: {speaker_tag} text: {self.asr_text}")
            if self.asr_text!='':
                self.text_queue.put_nowait(json.dumps({"speaker": speaker_tag, "text": self.asr_text}))
            self.asr_text=''
            self.cache.clear()
    # ================= Utils =================

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

