import torch
from torch.serialization import add_safe_globals
from torch.torch_version import TorchVersion

add_safe_globals([TorchVersion])
import sys
import warnings

warnings.filterwarnings(
    "ignore",
    message="torchcodec is not installed correctly"
)
warnings.filterwarnings(
    "ignore",
    message="torchcodec"
)

import os
import time
from multiprocessing import Process, Queue, set_start_method, freeze_support
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Disable torch distributed module loading to prevent crashes in pyinstaller builds
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '0'
os.environ['PYTORCH_NO_CUDA_MEMORY_CACHING'] = '1'

import voice.recorder as recorder
import voice.asr as asr
from ui.app import VoiceApp
from settings import cfg
from loguru import logger
from ui.login_dialog import LoginDialog
from PySide6.QtWidgets import QDialog
from pathlib import Path
from case.sql_manage import init_db
import asyncio
from qasync import QEventLoop
import ui.cs

# Prevent torch distributed from loading (causes crashes in packaged apps)
import torch
if hasattr(torch, 'distributed'):
    torch.distributed.is_available = lambda: False

def start_process(name, target, kwargs):
    p = Process(target=target, args=(kwargs,), name=name)
    p.daemon = True
    p.start()
    logger.info(f"启动子进程: {name} (pid={p.pid})")
    return p

def monitor_and_restart(procs_dict, kwargs):
    while True:
        try:
            for name, proc in list(procs_dict.items()):
                if not proc.is_alive():
                    logger.warning(f"子进程{name}已挂，自动重启中...")
                    proc.terminate()
                    proc.join(timeout=5)
                    if name == "RecorderProcess":
                        new_proc = start_process(name, recorder.run, kwargs)
                    elif name == "ASRProcess":
                        new_proc = start_process(name, asr.run, kwargs)
                    else:
                        logger.error(f"未知进程名: {name}, 无法重启")
                        continue
                    procs_dict[name] = new_proc
            time.sleep(1)
        except Exception as e:
            logger.error(f"监控线程异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # 支持 PyInstaller 打包后的 multiprocessing
    freeze_support()
    set_start_method("spawn")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("img/app.ico"))
   
    home =  Path.home()
    vetvoice_folder = os.path.join(home, ".vetvoice")
    os.makedirs(vetvoice_folder, exist_ok=True)

    # 检查资源路径和模型状态（仅在有资源路径时检查）
    resource_dir = cfg.get("app", "resource_dir", "")
    save_dir_cfg = cfg.get("app", "save_dir", "")

    if resource_dir and save_dir_cfg:
        # 检查模型状态
        from utils.model_downloader import ModelDownloader
        logger.info("🔍 检查模型状态...")

        try:
            downloader = ModelDownloader()

            # 检查当前配置的ASR模型
            current_asr = cfg.get("asr", "model", "vosk")

            # 检查必要的模型
            check_models = [current_asr]

            # 如果没有模型，设置标志，不启动音频处理进程
            has_models = True
            missing_models = []

            for model_type in check_models:
                if not downloader.check_model_exists(model_type):
                    has_models = False
                    missing_models.append(downloader.MODELS[model_type]['name'])
                    logger.warning(f"⚠️ 缺少模型: {downloader.MODELS[model_type]['name']}")

            if not has_models:
                logger.warning("⚠️ 检测到缺少模型，程序将在受限模式下运行")
                logger.info("请在设置中下载模型文件后重启程序")
            else:
                logger.info("✅ 所需模型已就绪")

        except Exception as e:
            logger.error(f"模型检查失败: {e}")
            logger.warning("程序将继续启动")
            has_models = False
    else:
        logger.info("⚠️ 未设置资源路径或保存路径，不启动模型相关进程")
        has_models = False
    
    # log
    save_dir = cfg.get("app", "save_dir")
    if save_dir:
        from utils.loger_util import init_subprocess_logger
        init_subprocess_logger(os.path.join(save_dir, "log"), "main")
    else:
        logger.warning("未设置保存路径，日志将输出到控制台")

    # 初始化数据库（仅在设置了save_dir时初始化）
    if save_dir_cfg:
        init_db()

    # 显示登录对话框
    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    
    # 初始化多进程通信组件

    # 控制队列：主进程 -> 子进程 发送控制命令
    control_queue = Queue(maxsize=10)
    # 音频队列：Recorder -> ASR 传输音频数据
    audio_queue = Queue(maxsize=cfg.get("process", "audio_queue_size"))
    # 文本队列：ASR -> 主进程 传输识别结果
    text_queue = Queue(maxsize=cfg.get("process", "text_queue_size"))

    # 波形显示：Recorder -> UI 传输实时波形数据
    from multiprocessing import Pipe
    audio_receive, audio_send = Pipe(duplex=False)

    kwargs = {
        'control_queue': control_queue,
        'audio_queue': audio_queue,
        'text_queue': text_queue,
        'audio_send': audio_send,
        'audio_receive': audio_receive,
    }

    procs = {}

    # 启动录音进程（录音功能不依赖模型可以独立运行）
    procs["RecorderProcess"] = start_process("RecorderProcess", recorder.run, kwargs)
    logger.info("Recorder进程已启动")

    # 只有在有模型的情况下才启动ASR进程（语音识别和说话人识别需要模型）
    if 'has_models' in locals() and has_models:
        procs["ASRProcess"] = start_process("ASRProcess", asr.run, kwargs)
        logger.info("ASR进程已启动")
    else:
        logger.warning("由于缺少模型或未设置资源路径，不启动ASR进程")


    logger.info("所有子进程已启动，开始主应用...")
    voice_app = VoiceApp(kwargs)
    voice_app.setStyleSheet(ui.cs.CS)
    voice_app.show() 
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()
