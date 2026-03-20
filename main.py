import sys
import os
import time
import traceback
from multiprocessing import Process, Queue, Event, set_start_method, RawArray, Pipe, freeze_support
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon  # 加在顶部
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
from utils.error_handler import (
    handle_exception,
    ConfigurationError,
    DatabaseError,
    VetVoiceError
)
from utils.logger_config import LoggerConfig, log_operation


def setup_global_exception_handler():
    """设置全局异常处理"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "未捕获的异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception


@handle_exception(exception_type=Exception, reraise=True, show_traceback=True)
def start_process(name, target, kwargs):
    p = Process(target=target, args=(kwargs,), name=name)
    p.daemon = True
    p.start()
    logger.info(f"启动子进程: {name} (pid={p.pid})")
    return p


@handle_exception(exception_type=Exception, reraise=True, show_traceback=True)
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
    # 设置全局异常处理
    setup_global_exception_handler()

    try:
        # 支持 PyInstaller 打包后的 multiprocessing
        freeze_support()
        set_start_method("spawn")

        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon("app.ico"))

        home =  Path.home()
        vetvoice_folder = os.path.join(home, ".vetvoice")
        os.makedirs(vetvoice_folder, exist_ok=True)

        if not os.path.exists(cfg.get("app", "save_dir")):
            from ui.path_dialog import PathDialog
            path_dialog = PathDialog()
            if path_dialog.exec() != QDialog.Accepted:
                sys.exit(0)

        # 初始化结构化日志系统
        log_dir = os.path.join(cfg.get("app", "save_dir"), "log")
        LoggerConfig.init_logger(
            log_dir=log_dir,
            app_name="VetVoice",
            level="INFO",
            rotation="10 MB",
            retention="14 days"
        )
        logger.info("=" * 60)
        logger.info("VetVoice 启动")
        logger.info("=" * 60)

        # 初始化数据库
        try:
            init_db()
            logger.info("数据库初始化成功")
        except Exception as e:
            logger.critical(f"数据库初始化失败: {e}")
            logger.critical("应用无法启动，请检查数据库配置")
            sys.exit(1)

        # 显示登录对话框
        login_dialog = LoginDialog()
        if login_dialog.exec() != QDialog.Accepted:
            sys.exit(0)

        # 初始化多进程通信组件
        try:
            audio_queue = Queue(maxsize=cfg.get("process", "audio_queue_size"))
            text_queue = Queue(maxsize=cfg.get("process", "text_queue_size"))
            start_event = Event()
            stop_event = Event()
            current_case_id = RawArray('c', 64)
            start_event.clear()
            stop_event.clear()
            audio_send, audio_receive = Pipe()
            kwargs = {
                'start_event': start_event,
                'stop_event': stop_event,
                'audio_queue': audio_queue,
                'text_queue': text_queue,
                'audio_send': audio_send,
                'audio_receive': audio_receive
            }

            procs = {}
            procs["ASRProcess"] = start_process("ASRProcess", asr.run, kwargs)
            procs["RecorderProcess"] = start_process("RecorderProcess", recorder.run, kwargs)

            log_operation("所有子进程启动完成",
                         asr_pid=procs["ASRProcess"].pid,
                         recorder_pid=procs["RecorderProcess"].pid)

            logger.info("主应用启动...")
            voice_app = VoiceApp(kwargs)
            voice_app.setStyleSheet(ui.cs.CS)
            voice_app.show()

            loop = QEventLoop(app)
            asyncio.set_event_loop(loop)
            with loop:
                loop.run_forever()

        except ConfigurationError as e:
            logger.critical(f"配置错误: {e}")
            sys.exit(1)
        except DatabaseError as e:
            logger.critical(f"数据库错误: {e}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"应用启动失败: {e}")
            logger.critical(traceback.format_exc())
            sys.exit(1)

    except Exception as e:
        logger.critical(f"致命错误，应用无法启动: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
