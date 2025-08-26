import ctypes
import os
from ctypes import c_void_p, c_int, c_short, POINTER, Structure, c_bool, c_float, byref
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Pipeline(Structure):
    _fields_ = [
        ("MaximumInternalProcessingRate", c_int),
        ("MultiChannelRender", c_bool),
        ("MultiChannelCapture", c_bool),
        ("CaptureDownmixMethod", c_int),
    ]

class PreAmplifier(Structure):
    _fields_ = [("Enabled", c_bool), ("FixedGainFactor", c_float)]

class AnalogMicGainEmulation(Structure):
    _fields_ = [("Enabled", c_bool), ("InitialLevel", c_int)]

class CaptureLevelAdjustment(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("PreGainFactor", c_float),
        ("PostGainFactor", c_float),
        ("MicGainEmulation", AnalogMicGainEmulation),
    ]

class HighPassFilter(Structure):
    _fields_ = [("Enabled", c_bool), ("ApplyInFullBand", c_bool)]

class EchoCanceller(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("MobileMode", c_bool),
        ("ExportLinearAecOutput", c_bool),
        ("EnforceHighPassFiltering", c_bool),
    ]

class NoiseSuppression(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("NoiseLevel", c_int),
        ("AnalyzeLinearAecOutputWhenAvailable", c_bool),
    ]

class TransientSuppression(Structure):
    _fields_ = [("Enabled", c_bool)]

class GainControllerMode:
    AdaptiveDigital = 1

class GainController1(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("ControllerMode", c_int),
        ("TargetLevelDbfs", c_int),
        ("CompressionGainDb", c_int),
        ("EnableLimiter", c_bool),
        ("AnalogController", ctypes.c_byte * 100),  # 占位
    ]

class Config(Structure):
    _fields_ = [
        ("PipelineConfig", Pipeline),
        ("PreAmp", PreAmplifier),
        ("LevelAdjustment", CaptureLevelAdjustment),
        ("HighPass", HighPassFilter),
        ("Echo", EchoCanceller),
        ("NoiseSuppress", NoiseSuppression),
        ("TransientSuppress", TransientSuppression),
        ("GainControl1", GainController1),
        ("GainControl2", ctypes.c_byte * 100),  # 占位
    ]

def create_lite_config(sample_rate=16000, enable_aec=True, enable_ns=True, ns_level=1, enable_agc=True):
    cfg = Config()
    cfg.PipelineConfig.MaximumInternalProcessingRate = sample_rate
    cfg.PipelineConfig.MultiChannelRender = False
    cfg.PipelineConfig.MultiChannelCapture = False
    cfg.PipelineConfig.CaptureDownmixMethod = 0  # Average

    cfg.PreAmp.Enabled = False
    cfg.PreAmp.FixedGainFactor = 1.0

    cfg.LevelAdjustment.Enabled = False
    cfg.LevelAdjustment.PreGainFactor = 1.0
    cfg.LevelAdjustment.PostGainFactor = 1.0
    cfg.LevelAdjustment.MicGainEmulation.Enabled = False
    cfg.LevelAdjustment.MicGainEmulation.InitialLevel = 100

    cfg.HighPass.Enabled = True
    cfg.HighPass.ApplyInFullBand = True

    cfg.Echo.Enabled = enable_aec
    cfg.Echo.MobileMode = False
    cfg.Echo.ExportLinearAecOutput = False
    cfg.Echo.EnforceHighPassFiltering = True

    cfg.NoiseSuppress.Enabled = enable_ns
    cfg.NoiseSuppress.NoiseLevel = ns_level
    cfg.NoiseSuppress.AnalyzeLinearAecOutputWhenAvailable = True

    cfg.TransientSuppress.Enabled = False

    cfg.GainControl1.Enabled = enable_agc
    cfg.GainControl1.ControllerMode = GainControllerMode.AdaptiveDigital
    cfg.GainControl1.TargetLevelDbfs = 3
    cfg.GainControl1.CompressionGainDb = 9
    cfg.GainControl1.EnableLimiter = True

    return cfg

class WebRtcApmLite:
    def __init__(self, lib_path, sample_rate=16000):
        self.sample_rate = sample_rate
        self.frame_size = sample_rate // 100  # 10ms
        self.lib = ctypes.cdll.LoadLibrary(os.path.abspath(lib_path))

        self._init_functions()
        self.apm = self.lib.WebRTC_APM_Create()
        if not self.apm:
            raise RuntimeError("WebRTC_APM_Create failed")

        self.stream_config = self.lib.WebRTC_APM_CreateStreamConfig(self.sample_rate, 1)
        self.set_config()

        self.lib.WebRTC_APM_SetStreamDelayMs(self.apm, 50)

    def _init_functions(self):
        self.lib.WebRTC_APM_Create.restype = c_void_p
        self.lib.WebRTC_APM_Destroy.argtypes = [c_void_p]
        self.lib.WebRTC_APM_CreateStreamConfig.restype = c_void_p
        self.lib.WebRTC_APM_CreateStreamConfig.argtypes = [c_int, c_int]
        self.lib.WebRTC_APM_DestroyStreamConfig.argtypes = [c_void_p]
        self.lib.WebRTC_APM_ApplyConfig.argtypes = [c_void_p, POINTER(Config)]
        self.lib.WebRTC_APM_SetStreamDelayMs.argtypes = [c_void_p, c_int]
        self.lib.WebRTC_APM_ProcessStream.argtypes = [c_void_p, POINTER(c_short), c_void_p, c_void_p, POINTER(c_short)]
        self.lib.WebRTC_APM_ProcessReverseStream.argtypes = [c_void_p, POINTER(c_short), c_void_p, c_void_p, POINTER(c_short)]

    def set_config(self, enable_aec=True, enable_ns=True, ns_level=1, enable_agc=True):
        cfg = create_lite_config(self.sample_rate, enable_aec, enable_ns, ns_level, enable_agc)
        ret = self.lib.WebRTC_APM_ApplyConfig(self.apm, byref(cfg))
        if ret != 0:
            logger.warning(f"WebRTC_APM_ApplyConfig failed: {ret}")

    def process(self, mic_frame: np.ndarray, ref_frame: np.ndarray = None) -> np.ndarray:
        """
        处理一帧音频。帧长必须为 10ms（sample_rate / 100），如 160。
        """
        bs = self.frame_size
        if len(mic_frame) != bs:
            if len(mic_frame) > bs:
                mic_frame = mic_frame[:bs]
            else:
                tmp = np.zeros(bs, dtype=np.int16)
                tmp[:len(mic_frame)] = mic_frame
                mic_frame = tmp

        mic_ptr = mic_frame.ctypes.data_as(POINTER(c_short))
        out_buf = (c_short * bs)()

        if ref_frame is not None:
            if len(ref_frame) != bs:
                tmp = np.zeros(bs, dtype=np.int16)
                tmp[:min(bs, len(ref_frame))] = ref_frame[:bs]
                ref_frame = tmp
            ref_ptr = ref_frame.ctypes.data_as(POINTER(c_short))
            self.lib.WebRTC_APM_ProcessReverseStream(
                self.apm, ref_ptr, self.stream_config, self.stream_config, out_buf
            )

        ret = self.lib.WebRTC_APM_ProcessStream(
            self.apm, mic_ptr, self.stream_config, self.stream_config, out_buf
        )
        if ret != 0:
            logger.warning(f"ProcessStream failed: {ret}")

        return np.frombuffer(out_buf, dtype=np.int16).copy()

    def close(self):
        if hasattr(self, "stream_config") and self.stream_config:
            self.lib.WebRTC_APM_DestroyStreamConfig(self.stream_config)
            self.stream_config = None
        if hasattr(self, "apm") and self.apm:
            self.lib.WebRTC_APM_Destroy(self.apm)
            self.apm = None

    def __del__(self):
        self.close()
