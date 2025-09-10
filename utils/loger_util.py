import sys
import os
from pathlib import Path
from loguru import logger
import datetime

def init_subprocess_logger(save_dir:str,process_name: str = "subprocess"):
    """
    为子进程初始化 logger，输出到控制台和独立的日志文件。

    Args:
        process_name (str): 当前子进程的名称，用于区分日志来源和日志文件名
    """
    try:
        # 日志根目录（和主程序一致，位于用户目录下 .vetvoice/log/）
        log_dir =Path(save_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件名包含日期和进程名，例如：asr_log_20240601.txt
        log_filename = f"{process_name}_log_{datetime.datetime.now():%Y%m%d}.txt"
        log_file = log_dir / log_filename

        # --- 移除所有默认的 handlers ---
        logger.remove()

        # --- 1. 输出到控制台（带颜色，适合调试）---
        logger.add(
            sys.stderr,
            level="DEBUG",
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<cyan>{process.name}</cyan> | "
                "<level>{level: <8}</level> | "
                "<level>{message}</level>"
            )
        )

        # --- 2. 输出到独立的日志文件（可选，推荐）---
        logger.add(
            str(log_file),
            rotation="1 day",      # 每天一个新日志文件
            retention="5 days",     # 保留最近 5 天
            level="INFO",
            encoding="utf-8",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{process.name} | "
                "{level} | "
                "{message}"
            )
        )

        logger.info(f"✅ 进程日志初始化完成 [进程名: {process_name}]，日志输出到控制台和文件: {log_file}")

    except Exception as e:
        # 如果日志初始化失败，至少打印到 stderr，避免完全静默
        import traceback
        print(f"[ERROR] 子进程日志初始化失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)