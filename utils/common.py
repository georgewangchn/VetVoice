import platform
import os
import re

# 获取当前用户的主目录（home 目录）
home_dir = os.path.expanduser("~")

os.makedirs(os.path.join(home_dir, ".vetvoice"), exist_ok=True)

def get_libopus_path(base_dir="libs/webrtc_apm") -> str:
    """
    自动获取适配当前平台和架构的 libopus 库路径。
    :param base_dir: 基础库目录
    :return: 匹配到的 libopus 路径
    :raises: RuntimeError 如果平台或架构不支持
    """
    system = platform.system().lower()  # "linux", "darwin", "windows"
    machine = platform.machine().lower()  # "x86_64", "arm64", "amd64", etc.

    if system == "darwin":  # macOS
        os_dir = "mac"
        ext = ".dylib"
    elif system == "linux":
        os_dir = "linux"
        ext = ".so"
    elif system == "windows":
        os_dir = "win"
        ext = ".dll"
    else:
        raise RuntimeError(f"不支持的系统平台: {system}")

    # 标准化架构名
    if machine in ("x86_64", "amd64"):
        arch = "x64" if system != "windows" else "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        raise RuntimeError(f"不支持的CPU架构: {machine}")

    # 拼接路径
    lib_name = "libwebrtc_apm" + ext if system != "windows" else "opus.dll"
    full_path = os.path.join(base_dir, os_dir, arch, lib_name)

    # if not os.path.exists(full_path):
    #     raise FileNotFoundError(f"未找到对应平台和架构的库文件: {full_path}")

    return full_path

def get_dynamic_silence_limit(duration, base_limit=10, min_limit=2, max_duration=10):
    """
    duration: 当前段语音已持续的秒数
    base_limit: 初始静音帧阈值
    min_limit: 最低静音帧阈值
    max_duration: 达到此语音时长后，silence_limit 下降到 min_limit

    返回当前应使用的 silence_limit（逐步线性衰减）
    """
    if duration <= 1:
        return base_limit
    elif duration >= max_duration:
        return min_limit
    else:
        decay_ratio = duration / max_duration
        dynamic_limit = base_limit - decay_ratio * (base_limit - min_limit)
        return max(min_limit, int(dynamic_limit))
    
    
def is_meaningful(text: str):
    skip_words = {"嗯", "啊", "哈", "对", "是的", "好的", "okay", "噢", "唔", "嗯嗯", "啊啊", "哎"}
    clean_text = text.replace(" ", "")
    if not clean_text:
        return False
    if all(word in skip_words for word in clean_text):
        return False
    # 连续重复“嗯”的情况
    if re.fullmatch(r"[嗯啊哈对是的好的噢唔]{1,5}", clean_text):
        return False
    return True


from loguru import logger
import sys
from settings import cfg
from pathlib import Path
import datetime

