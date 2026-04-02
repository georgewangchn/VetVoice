"""
资源路径管理模块
根据运行环境自动选择正确的资源路径
"""
import os
from pathlib import Path
from settings import cfg


def get_project_root():
    """获取工程根目录"""
    # 获取当前文件所在目录的上级目录（工程根目录）
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent  # 从 utils/ 目录向上两级
    return project_root


def get_resource_base_path():
    """
    获取资源文件的基础路径
    优先级：
    1. 环境变量 VETVOICE_RESOURCES
    2. 用户登陆设置的路径
    """
    # 1. 检查环境变量
    env_path = os.environ.get('VETVOICE_RESOURCES')
    if env_path and os.path.exists(env_path):
        return Path(env_path)
    resource_dir = cfg.get("app","resource_dir")
    return Path(resource_dir)


def get_resource_path(relative_path: str = "") -> Path:
    """
    获取资源文件的完整路径

    Args:
        relative_path: 相对于资源目录的路径（对于模型文件）
                    或相对于工程根目录的路径（对于libs文件）

    Returns:
        完整的资源文件路径
    """
    # 检查是否是libs路径，libs使用工程目录
    if relative_path.startswith("libs/"):
        return get_project_root() / relative_path

    # 其他资源文件使用配置的资源目录
    base_path = get_resource_base_path()
    if relative_path:
        return base_path / relative_path
    return base_path


def ensure_resource_dirs():
    """
    确保必要的资源目录存在
    """
    base_path = get_resource_base_path()

    # 创建必要的子目录（libs不需要创建，已经存在于工程目录中）
    # 创建资源目录和缓存目录
    dirs_to_create = [
        base_path,
        base_path / '.cache' / 'shuai1618',
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    return base_path


def check_resources_available():
    """
    检查资源文件是否可用

    Returns:
        (bool, str): (是否可用, 错误信息)
    """
    base_path = get_resource_base_path()

    if not base_path.exists():
        return False, f"资源目录不存在: {base_path}"

    # 检查关键模型文件（使用新的 .cache 路径）
    required_files = [
        '.cache/shuai1618/paraformer-zh-streaming',
        '.cache/shuai1618/speaker-diarization',
    ]

    missing_files = []
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        return False, f"缺少必要的模型文件:\n" + "\n".join(missing_files)

    # 检查libs目录（在工程目录中）
    libs_path = get_project_root() / "libs"
    if not libs_path.exists():
        missing_files.append("libs目录不存在（工程目录）")

    return True, "资源文件检查通过"

import platform


def get_webrtc_apm_lib():
    """获取webrtc_apm库路径，直接使用工程目录中的libs"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":  # macOS
        if "arm" in machine:   # Apple Silicon
            return get_project_root() / "libs" / "webrtc_apm" / "mac" / "arm64" / "libwebrtc_apm.dylib"
        elif "x86" in machine or "amd64" in machine:
            return get_project_root() / "libs" / "webrtc_apm" / "mac" / "x64" / "libwebrtc_apm.dylib"

    elif system == "linux":  # Linux
        if "x86" in machine or "amd64" in machine:
            return get_project_root() / "libs" / "webrtc_apm" / "linux" / "x64" / "libwebrtc_apm.so"

    elif system == "windows":  # Windows
        if "x86" in machine or "amd64" in machine:
            return get_project_root() / "libs" / "webrtc_apm" / "win" / "x86_64" / "libwebrtc_apm.dll"

    raise RuntimeError(f"不支持的系统平台: {system} {machine}")
