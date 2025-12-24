# -*- coding: utf-8 -*-
import sounddevice as sd
import numpy as np
import threading
import wave
import queue
from loguru import logger
from voice.webrtc_apm_lite import WebRtcApmLite
from multiprocessing import Queue
import webrtcvad
import datetime
from settings import cfg
from utils.resource_path import get_webrtc_apm_lib
class VoiceRecorder:
    def __init__(self, audio_queue: Queue, audio_send):
        self.sample_rate = 16000
        self.audio_queue = audio_queue
        self.audio_send = audio_send
        self.audio_frames = []
        self.resample_buffer = np.array([], dtype=np.int16)
        self.apm = WebRtcApmLite(get_webrtc_apm_lib(),16000)

        self._inner_queue = queue.Queue(maxsize=200)
        self._inner_thread = None
        self._inner_stop_event= threading.Event()
        
        self.vad = webrtcvad.Vad(1)
        self.frame_len = 160  # 10ms @ 16kHz
        self.max_segment_len = 16000 * 1  # 15秒
        
        #保存30s的wav文件
        self._save_queue = queue.Queue(maxsize=300)
        self._save_thread = None 
        self._save_stop_event= threading.Event()
       
    def is_speech(self, frame):
        if len(frame) != 160:
            return False
        return self.vad.is_speech(frame.tobytes(), 16000)    
    def audio_callback(self, indata, frames, time, status):
        try:
            # logger.debug(f"麦克风接受frames: {frames}")
            mic_int16 = indata[:, 0].copy()
            self._inner_queue.put_nowait(mic_int16)
            if not self.audio_send.poll():
                    self.audio_send.send(mic_int16.copy())
        except queue.Full:
            logger.warning("audio queue full, drop frame")
        except Exception as e:
            logger.error(f"audio_callback error: {e}")

    def _inner_run(self):
        bs = 160   
        ns_chunks = []
        silence_count = 0
        while not self._inner_stop_event.is_set():
            try:
                block = self._inner_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")

            self.resample_buffer = np.concatenate([self.resample_buffer, block])
            if len(self.resample_buffer) < 800:
                continue

            num_complete = len(self.resample_buffer) // bs * bs
            chunks = self.resample_buffer[:num_complete]
            self.resample_buffer = self.resample_buffer[num_complete:]

            try:
                for i in range(0, len(chunks) - bs + 1, bs):
                    segment = chunks[i : i + bs]
                    ns_chunk = self.apm.process(segment)
                    # logger.debug(f"apm处理音频段，长度: {len(ns_chunk)} samples")
                    # webrtcvad 需要16-bit mono PCM 16kHz，且frame长度必须是10,20或30ms，这里用10ms
                    # if self.sample_rate != 16000:
                    #     float_data = ns_chunk.astype(np.float32) / 32768.0
                    #     segment_16k = resampy.resample(float_data, 48000, 16000)
                    #     ns_chunk = np.clip(segment_16k * 32768, -32768, 32767).astype(np.int16)
                    if self.is_speech(ns_chunk):
                        ns_chunks.append(ns_chunk)
                        silence_count = 0
                        if len(ns_chunks) * self.frame_len >= self.max_segment_len:
                            ns_block = np.concatenate(ns_chunks)
                            self.audio_queue.put_nowait((ns_block.copy(),False))
                            self._save_queue.put_nowait(ns_block.copy())
                            ns_chunks.clear()
                            logger.debug(f"语音段超长，送入queue，长度: {len(ns_block)} ")
                    else:
                        silence_count += 1
                        if silence_count<10:
                            continue
                        if silence_count<20:
                            if ns_chunks:
                                ns_block = np.concatenate(ns_chunks)
                                self.audio_queue.put_nowait((ns_block.copy(),False))
                                self._save_queue.put_nowait(ns_block.copy())
                                ns_chunks.clear()
                                logger.debug(f"静音<20个或者语音段超长，送入queue，长度: {len(ns_block)} ")
                            continue
                            
                        if silence_count >= 20:
                            if ns_chunks:
                                ns_block = np.concatenate(ns_chunks)
                                self.audio_queue.put_nowait((ns_block.copy(),True))
                                self._save_queue.put_nowait(ns_block.copy())
                            else:
                                self.audio_queue.put_nowait((ns_chunks.copy(),True))
                            logger.debug(f"静音>=20个或者语音段超长，送入queue，长度: {len(ns_block)} ")
                            ns_chunks.clear()
                            silence_count = 0
                                
            except (BrokenPipeError, EOFError) as e:
                logger.warning(f"audio_send failed: {e}")
            except queue.Full:
                logger.warning("audio_queue is full, dropping frame")
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")
    def _save_run(self):
        buff = np.array([], dtype=np.int16)
        while not self._save_stop_event.is_set():
            try:
                block = self._save_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")

            buff = np.concatenate([buff, block])
            if len(buff) < 480000:
                continue
            from case.sql_manage import VedisManager
            
            case_id=VedisManager.get("current_case_id")
            now_str = datetime.datetime.now().strftime("%H%M%S")
            
            import os
            os.makedirs(os.path.join(cfg.get("app", "save_dir"), "wav"), exist_ok=True)
            filepath = os.path.join(cfg.get("app", "save_dir"), f"wav/{case_id}_{now_str}.wav")
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(np.dtype('int16').itemsize)
                wf.setframerate(16000)
                wf.writeframes(b''.join([f.tobytes() for f in buff]))

            logger.info(f"Saved WAV to {filepath}")
            buff = np.array([], dtype=np.int16)

    def start(self, device=None):
        logger.info("打开麦克风录音...")
        self._inner_stop_event.clear()

        self._inner_thread = threading.Thread(target=self._inner_run,daemon=True)
        self._inner_thread.start()
        self._save_thread= threading.Thread(target=self._save_run, daemon=True)
        self._save_thread.start()

        self.stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16',
            callback=self.audio_callback,
            blocksize=1600,
            device=device
        )
        self.stream.start()
        logger.info("麦克风成功打开")

    def stop(self):
        logger.info("停止麦克风录音...")
        try:
            self.stream.stop()
            self.stream.close()
        except Exception as e:
            logger.error(f"stream stop close error: {e}")
        self._inner_stop_event.set()
        if self._inner_thread is not None:
            self._inner_thread.join(timeout=2)
            logger.info("音频处理线程已退出")

def run(kwargs):
    """多进程录音主入口，可被循环控制"""
    from utils.loger_util import init_subprocess_logger
    import os
    init_subprocess_logger(os.path.join(cfg.get("app", "save_dir"),"log"),"recorder")
    start_event = kwargs['start_event']
    stop_event = kwargs['stop_event']
    audio_queue: Queue = kwargs['audio_queue']
    audio_send = kwargs['audio_send']

    recorder = VoiceRecorder(audio_queue,audio_send)

    logger.info("🎙️ Recorder 进程初始化完成，等待启动指令...")

    
    while True:
        try:
            logger.info("🕒 等待 start_event...")
            start_event.wait()
            logger.info("📢 接收到 start_event，start_event 状态: %s", start_event.is_set())
            recorder.start()

            logger.info("🕒 等待 stop_event...")
            stop_event.wait()
            logger.info("📴 接收到 stop_event，stop_event 状态: %s", stop_event.is_set())
            recorder.stop()

            # ⭐️ 清除事件，避免循环逻辑异常
            stop_event.clear()
            start_event.clear()
            logger.info("✅ 事件已重置，等待下一次 start_event...")

        except Exception as e:
            logger.info("🧹 Recorder 进程报错，清理资源"+str(e))
            try:
                recorder.stop()

            except Exception as e2:
                logger.error(f"清理资源失败: {e2}")