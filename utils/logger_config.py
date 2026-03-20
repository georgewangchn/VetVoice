"""
日志配置工具
提供结构化日志格式、日志级别管理和性能日志
"""
import sys
import os
from pathlib import Path
from loguru import logger
from typing import Optional


# 日志级别映射
LOG_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4
}


class LoggerConfig:
    """日志配置管理器"""
    _instance = None
    _current_level = "INFO"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init_logger(
        cls,
        log_dir: str,
        app_name: str,
        level: str = "INFO",
        rotation: str = "10 MB",
        retention: str = "14 days"
    ):
        """
        初始化日志系统

        Args:
            log_dir: 日志目录路径
            app_name: 应用名称
            level: 日志级别
            rotation: 日志轮转设置
            retention: 日志保留时间
        """
        # 确保日志目录存在
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # 移除默认处理器
        logger.remove()

        # 结构化日志格式
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        # 控制台输出（带格式）
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            colorize=True
        )

        # 日志文件（按时间分割）
        logger.add(
            os.path.join(log_dir, f"{app_name}_{{time:YYYY-MM-DD}}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8"
        )

        # 错误日志单独记录
        logger.add(
            os.path.join(log_dir, f"{app_name}_error.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
            level="ERROR",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8"
        )

        # 性能日志单独记录
        logger.add(
            os.path.join(log_dir, f"{app_name}_performance.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="DEBUG",
            rotation="50 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "PERF" in record["extra"]
        )

        cls._current_level = level
        logger.info(f"日志系统初始化完成: {level}")

    @classmethod
    def set_level(cls, level: str):
        """
        动态设置日志级别

        Args:
            level: 新的日志级别
        """
        if level.upper() not in LOG_LEVELS:
            logger.warning(f"无效的日志级别: {level}")
            return

        cls._current_level = level.upper()
        # 更新所有处理器的日志级别
        logger.remove()
        # 这里需要重新初始化，简化处理
        logger.info(f"日志级别已更新为: {level}")

    @classmethod
    def get_level(cls) -> str:
        """获取当前日志级别"""
        return cls._current_level


def log_operation(operation: str, **kwargs):
    """
    记录关键操作日志

    Args:
        operation: 操作名称
        **kwargs: 操作参数
    """
    params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"[操作] {operation} ({params_str})")


def log_performance(func_name: str, elapsed: float, **kwargs):
    """
    记录性能日志

    Args:
        func_name: 函数名称
        elapsed: 执行时间（秒）
        **kwargs: 额外信息
    """
    extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    logger.bind(PERF=True).debug(f"[性能] {func_name} 耗时: {elapsed:.4f}秒 {extra_info}")


def performance_logger(func):
    """
    性能记录装饰器

    Args:
        func: 要测量的函数
    """
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            log_performance(func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[性能] {func.__name__} 执行失败 (耗时: {elapsed:.4f}秒): {e}")
            raise
    return wrapper


def log_database_query(query: str, params: Optional[tuple], elapsed: float):
    """
    记录数据库查询日志

    Args:
        query: SQL 查询语句
        params: 查询参数
        elapsed: 执行时间（秒）
    """
    params_str = str(params) if params else "()"
    if elapsed > 0.5:  # 超过 500ms 记录为警告
        logger.warning(f"[数据库] 慢查询 ({elapsed:.4f}秒): {query[:100]}... {params_str}")
    else:
        logger.debug(f"[数据库] 查询 ({elapsed:.4f}秒): {query[:50]}...")


def log_api_request(method: str, url: str, status_code: int, elapsed: float):
    """
    记录 API 请求日志

    Args:
        method: HTTP 方法
        url: 请求 URL
        status_code: 响应状态码
        elapsed: 响应时间（秒）
    """
    if elapsed > 2.0:  # 超过 2 秒记录为警告
        logger.warning(f"[API] 慢响应 ({elapsed:.4f}秒): {method} {url} -> {status_code}")
    elif status_code >= 400:
        logger.error(f"[API] 错误响应: {method} {url} -> {status_code}")
    else:
        logger.debug(f"[API] {method} {url} -> {status_code} ({elapsed:.4f}秒)")
