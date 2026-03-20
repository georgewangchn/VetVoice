"""
统一错误处理工具类
提供自定义异常、错误处理装饰器和日志记录
"""
import functools
import traceback
from typing import Any, Callable, Optional, Type
from loguru import logger


# 自定义异常类


class VetVoiceError(Exception):
    """VetVoice 基础异常类"""
    pass


class DatabaseError(VetVoiceError):
    """数据库错误"""
    pass


class ASRError(VetVoiceError):
    """语音识别错误"""
    pass


class SpeakerError(VetVoiceError):
    """说话人分离错误"""
    pass


class LLMError(VetVoiceError):
    """AI 语言模型错误"""
    pass


class ValidationError(VetVoiceError):
    """数据验证错误"""
    pass


class ConfigurationError(VetVoiceError):
    """配置错误"""
    pass


class FileOperationError(VetVoiceError):
    """文件操作错误"""
    pass


def handle_exception(
    exception_type: Type[Exception] = Exception,
    default_return: Any = None,
    reraise: bool = False,
    log_level: str = "ERROR",
    show_traceback: bool = False
):
    """
    异常处理装饰器

    Args:
        exception_type: 要捕获的异常类型
        default_return: 发生异常时的默认返回值
        reraise: 是否重新抛出异常
        log_level: 日志级别
        show_traceback: 是否显示完整的堆栈跟踪
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                # 记录错误日志
                log_message = f"[{func.__name__}] 发生异常: {e}"
                if show_traceback:
                    log_message += f"\n{traceback.format_exc()}"

                if log_level == "DEBUG":
                    logger.debug(log_message)
                elif log_level == "INFO":
                    logger.info(log_message)
                elif log_level == "WARNING":
                    logger.warning(log_message)
                elif log_level == "ERROR":
                    logger.error(log_message)
                elif log_level == "CRITICAL":
                    logger.critical(log_message)

                if reraise:
                    raise

                return default_return
        return wrapper
    return decorator


def handle_database_error(default_return: Any = None, reraise: bool = False):
    """数据库错误处理装饰器"""
    return handle_exception(
        exception_type=DatabaseError,
        default_return=default_return,
        reraise=reraise,
        log_level="ERROR",
        show_traceback=True
    )


def handle_llm_error(default_return: Any = None, reraise: bool = False):
    """LLM 错误处理装饰器"""
    return handle_exception(
        exception_type=LLMError,
        default_return=default_return,
        reraise=reraise,
        log_level="WARNING",
        show_traceback=False
    )


def handle_file_error(default_return: Any = None, reraise: bool = False):
    """文件操作错误处理装饰器"""
    return handle_exception(
        exception_type=FileOperationError,
        default_return=default_return,
        reraise=reraise,
        log_level="ERROR",
        show_traceback=True
    )


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[Exception]]:
    """
    安全执行函数，返回执行结果

    Args:
        func: 要执行的函数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        (成功, 结果, 异常)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        logger.error(f"安全执行失败: {func.__name__} - {e}")
        return False, None, e


def validate_required_fields(data: dict, required_fields: list[str]) -> None:
    """
    验证必填字段

    Args:
        data: 数据字典
        required_fields: 必填字段列表

    Raises:
        ValidationError: 缺少必填字段
    """
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        raise ValidationError(f"缺少必填字段: {', '.join(missing_fields)}")


def format_error_message(error: Exception, context: str = "") -> str:
    """
    格式化错误消息

    Args:
        error: 异常对象
        context: 上下文信息

    Returns:
        格式化的错误消息
    """
    message = f"错误: {str(error)}"
    if context:
        message = f"{context}\n{message}"
    return message


def log_performance(func: Callable):
    """
    性能日志装饰器

    Args:
        func: 要测量的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"[{func.__name__}] 执行耗时: {elapsed:.4f} 秒")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[{func.__name__}] 执行失败 (耗时: {elapsed:.4f} 秒): {e}")
            raise
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple[Type[Exception], ...] = (Exception,)):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 重试间隔(秒)
        exceptions: 触发重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"[{func.__name__}] 第 {attempt + 1} 次尝试失败: {e}, {delay} 秒后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"[{func.__name__}] 所有尝试失败")

            raise last_exception
        return wrapper
    return decorator
