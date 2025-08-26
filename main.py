import sys
import os
import threading
import time
from multiprocessing import Process, Queue, Event, set_start_method, RawArray, Pipe, freeze_support
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon  # 加在顶部
from PySide6.QtWidgets import QMessageBox
import voice.recorder as recorder
import voice.asr_funasr as asr
from ui.app import VoiceApp
from settings import cfg
from loguru import logger
from ui.login_dialog import LoginDialog
logger.remove()
logger.add(sys.stderr, level="DEBUG")
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
    app.setWindowIcon(QIcon("app.ico"))
    # 显示登录对话框
    login_dialog = LoginDialog()
    from PySide6.QtWidgets import QDialog
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    
    # 获取用户选择的资源路径
    resource_dir ,save_dir = login_dialog.get_path()
    if resource_dir and save_dir:
        # 资源路径已经在登录时设置到环境变量中
        logger.info(f"使用资源路径: {resource_dir}\n使用保存路径: {save_dir}")
        cfg.set_save("app", "save_dir", save_dir)  # 将参数写入配置（假设cfg支持动态更新）
        cfg.set_save("app", "resource_dir", resource_dir)  # 将参数写入配置（假设cfg支持动态更新）
        os.makedirs(os.path.join(save_dir,'wav'), exist_ok=True)
        os.makedirs(os.path.join(save_dir,'pdf'), exist_ok=True)
    else:
        QMessageBox.warning("错误", "资源路径/保存路径未设置，使用默认路径")
        logger.warning("未设置资源路径，使用默认路径")
        sys.exit(0)

    audio_queue = Queue(maxsize=cfg.get("process", "audio_queue_size"))
    text_queue = Queue(maxsize=cfg.get("process", "text_queue_size"))
    start_event = Event()
    stop_event = Event()
    current_case_id = RawArray('c', 64) 
    start_event.clear()
    stop_event.clear()
    audio_send, audio_receive = Pipe()
    user_info = login_dialog.get_user_info()
    kwargs = {
        'start_event': start_event,
        'stop_event': stop_event,
        'audio_queue': audio_queue,
        'text_queue': text_queue,
        'current_case_id': current_case_id,
        'audio_send': audio_send,
        'audio_receive': audio_receive,
        'user_info': user_info 
    }

    procs = {}
    procs["ASRProcess"] = start_process("ASRProcess", asr.run, kwargs)
    procs["RecorderProcess"] = start_process("RecorderProcess", recorder.run, kwargs)
    
    # monitor_thread = threading.Thread(target=monitor_and_restart, args=(procs, kwargs), daemon=True)
    # monitor_thread.start()
    logger.info("所有子进程已启动，开始主应用...")
    voice_app = VoiceApp(kwargs)
    
    voice_app.show() 

    sys.exit(app.exec())
