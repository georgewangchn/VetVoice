"""
模型下载管理器
从 ModelScope 自动下载和管理所需模型
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from loguru import logger
from settings import cfg
from tqdm import tqdm
import threading


class DownloadManager:
    """全局单例下载管理器，用于持久化下载状态"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.downloading = False
        self.current_models = []
        self.log_lines = []
        self.thread = None
        self.callbacks = []  # 用于通知 UI 更新的回调函数

    def start_download(self, models, on_log, on_complete, on_error):
        """开始下载"""
        if self.downloading:
            logger.warning("已有下载任务在进行中")
            return False

        self.downloading = True
        self.current_models = models
        self.log_lines = []
        self.callbacks = []

        # 注册回调
        if on_log:
            self.callbacks.append(('log', on_log))
        if on_complete:
            self.callbacks.append(('complete', on_complete))
        if on_error:
            self.callbacks.append(('error', on_error))

        # 启动下载线程
        self.thread = threading.Thread(target=self._download_thread, args=(models,))
        self.thread.daemon = True
        self.thread.start()

        return True

    def _download_thread(self, models):
        """下载线程"""
        try:
            resource_dir = cfg.get("app", "resource_dir")
            from utils.model_downloader import ModelDownloader

            os.makedirs(resource_dir, exist_ok=True)
            downloader = ModelDownloader(resource_dir)

            # 自定义 logger 以捕获日志
            class LogCapture:
                def __init__(self, callback):
                    self.callback = callback

                def write(self, text):
                    if text.strip():
                        self.callback(text.strip())

            # 添加日志捕获
            log_callback = lambda text: self._notify_log(text)
            handler = logger.add(
                lambda msg: self._notify_log(msg),
                format="{message}",
                level="INFO"
            )

            # 执行下载
            results = downloader.download_missing_models(models)

            logger.remove(handler)

            self.downloading = False
            self._notify_complete(results)

        except Exception as e:
            self.downloading = False
            self._notify_error(str(e))

    def _notify_log(self, text):
        """通知日志更新"""
        self.log_lines.append(text)
        for callback_type, callback in self.callbacks:
            if callback_type == 'log':
                try:
                    callback(text)
                except:
                    pass

    def _notify_complete(self, results):
        """通知完成"""
        self.downloading = False
        for callback_type, callback in self.callbacks:
            if callback_type == 'complete':
                try:
                    callback(results)
                except:
                    pass

    def _notify_error(self, error):
        """通知错误"""
        self.downloading = False
        for callback_type, callback in self.callbacks:
            if callback_type == 'error':
                try:
                    callback(error)
                except:
                    pass

    def register_callback(self, callback_type, callback):
        """注册回调函数"""
        self.callbacks.append((callback_type, callback))

    def get_status(self):
        """获取当前状态"""
        return {
            'downloading': self.downloading,
            'models': self.current_models,
            'logs': self.log_lines
        }



class ModelDownloader:
    """模型下载器，支持从 ModelScope 下载模型"""

    MODELS = {
        'funasr': {
            'name': 'Paraformer 中文语音识别模型',
            'modelscope_id': 'shuai1618/paraformer-zh-streaming',
            'revision': 'master',
            'check_files': ['model.pt', 'config.yaml'],
            'cache_path': '.cache/shuai1618/paraformer-zh-streaming'
        },
        'spk': {
            'name': 'Speaker 说话人识别模型',
            'modelscope_id': 'shuai1618/speaker-diarization',
            'revision': 'main',
            'check_files': ['config.yaml', 'embedding/pytorch_model.bin'],
            'cache_path': '.cache/shuai1618/speaker-diarization'
        },
        'voiceprint': {
            'name': '医生声纹识别模型',
            'modelscope_id': 'shuai1618/wespeaker-voxceleb-resnet34-LM',
            'revision': 'main',
            'check_files': ['config.yaml'],  # 只检查配置文件，因为模型文件名可能不同
            'cache_path': '.cache/shuai1618/wespeaker-voxceleb-resnet34-LM'
        },
        'vosk': {
            'name': 'VOSK 中文语音识别模型',
            'modelscope_id': 'shuai1618/vosk-model-small-cn',
            'revision': 'main',
            'check_files': ['README', 'model'],
            'cache_path': '.cache/shuai1618/vosk-model-small-cn'
        }
    }

    def __init__(self, resource_dir: str = None):
        """
        初始化模型下载器

        Args:
            resource_dir: 资源目录路径，如果为None则从配置读取
        """
        self.resource_dir = Path(resource_dir) if resource_dir else None

    def get_resource_dir(self) -> Path:
        """获取资源目录"""
        if self.resource_dir:
            return self.resource_dir
        return Path(cfg.get("app", "resource_dir"))

    def check_model_exists(self, model_type: str) -> bool:
        """
        检查模型是否存在

        Args:
            model_type: 模型类型 ('funasr', 'vosk', 'spk')

        Returns:
            bool: 模型是否存在
        """
        if model_type not in self.MODELS:
            logger.error(f"未知的模型类型: {model_type}")
            return False

        model_config = self.MODELS[model_type]
        resource_dir = self.get_resource_dir()

        model_path = resource_dir / model_config['cache_path']

        if not model_path.exists():
            logger.debug(f"模型目录不存在: {model_path}")
            return False

        # 检查关键文件
        for check_file in model_config['check_files']:
            if not (model_path / check_file).exists():
                logger.warning(f"模型文件缺失: {model_path / check_file}")
                return False

        logger.info(f"✅ {model_config['name']} 已存在")
        return True

    def download_model(self, model_type: str) -> bool:
        """
        从 ModelScope 下载模型

        Args:
            model_type: 模型类型 ('funasr', 'vosk', 'pyannote')

        Returns:
            bool: 是否下载成功
        """
        if model_type not in self.MODELS:
            logger.error(f"未知的模型类型: {model_type}")
            return False

        model_config = self.MODELS[model_type]
        resource_dir = self.get_resource_dir()

        logger.info(f"📥 准备下载 {model_config['name']}...")
        logger.info(f"   ModelScope ID: {model_config['modelscope_id']}")

        try:
            # 创建资源目录
            resource_dir.mkdir(parents=True, exist_ok=True)

            # 构建下载脚本的代码
            download_script = f'''
import os
import sys
import shutil
from pathlib import Path

# 防止导入 PySide6
os.environ['QT_API'] = 'none'

from modelscope import snapshot_download

model_id = "{model_config['modelscope_id']}"
cache_dir = "{str(resource_dir / '.cache')}"

print("开始下载模型...")
# 使用 snapshot_download 下载模型，指定缓存目录
model_path = snapshot_download(
    model_id,
    cache_dir=cache_dir,
)

print(f"下载完成，模型路径: {{model_path}}")
print("模型保持在 .cache 目录下，下载成功")
'''

            # 将脚本写入临时文件
            script_file = resource_dir / f'temp_download_{model_type}.py'
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(download_script)

            # 在单独的进程中执行下载脚本
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            # 输出下载日志
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line:
                        logger.info(f"   {line}")

            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line:
                        logger.warning(f"   [stderr] {line}")

            # 删除临时脚本
            if script_file.exists():
                script_file.unlink()

            # 验证下载结果
            if result.returncode == 0:
                logger.info(f"✅ {model_config['name']} 下载完成！")

                # 验证下载
                if self.check_model_exists(model_type):
                    logger.info(f"✅ {model_config['name']} 验证通过")
                    return True
                else:
                    logger.warning(f"⚠️ {model_config['name']} 下载完成但验证失败")
                    return False
            else:
                logger.error(f"❌ {model_config['name']} 下载失败，退出码: {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ {model_config['name']} 下载超时")
            return False
        except Exception as e:
            logger.error(f"❌ {model_config['name']} 下载失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            # 清理可能下载不完整的文件
            try:
                target_dir = resource_dir / model_config['cache_path']
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                    logger.info(f"已清理不完整的下载目录: {target_dir}")
            except Exception as cleanup_error:
                logger.warning(f"清理下载目录失败: {cleanup_error}")
            return False

    def ensure_model(self, model_type: str, auto_download: bool = True) -> bool:
        """
        确保模型存在，不存在则下载

        Args:
            model_type: 模型类型 ('funasr', 'vosk', 'pyannote')
            auto_download: 是否自动下载

        Returns:
            bool: 模型是否可用
        """
        if self.check_model_exists(model_type):
            return True

        if not auto_download:
            logger.warning(f"⚠️ {self.MODELS[model_type]['name']} 不存在，且禁止自动下载")
            return False

        logger.info(f"🔍 {self.MODELS[model_type]['name']} 不存在，尝试自动下载...")
        return self.download_model(model_type)

    def check_all_models(self) -> dict:
        """
        检查所有模型状态

        Returns:
            dict: 各模型的状态 {'model_type': bool}
        """
        results = {}
        for model_type in self.MODELS:
            results[model_type] = self.check_model_exists(model_type)
        return results

    def download_missing_models(self, model_types: list = None) -> dict:
        """
        下载缺失的模型

        Args:
            model_types: 要检查下载的模型类型列表，None表示检查所有模型

        Returns:
            dict: 各模型的下载结果 {'model_type': bool}
        """
        results = {}

        if model_types is None:
            model_types = list(self.MODELS.keys())

        for model_type in model_types:
            if model_type not in self.MODELS:
                logger.warning(f"跳过未知模型类型: {model_type}")
                continue

            model_config = self.MODELS[model_type]
            logger.info(f"\n{'='*50}")
            logger.info(f"检查模型: {model_config['name']}")

            if self.check_model_exists(model_type):
                logger.info(f"✅ 模型已存在，跳过下载")
                results[model_type] = True
            else:
                logger.info(f"⬇️ 模型不存在，开始下载...")
                results[model_type] = self.download_model(model_type)
                if results[model_type]:
                    logger.info(f"✅ {model_config['name']} 安装成功")
                else:
                    logger.error(f"❌ {model_config['name']} 安装失败")

        logger.info(f"\n{'='*50}")
        logger.info("模型下载摘要:")
        for model_type, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            logger.info(f"  {self.MODELS[model_type]['name']}: {status}")

        return results


def main():
    """下载管理器的命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python model_downloader.py [模型类型] [资源路径]")
        print("模型类型: funasr, vosk, pyannote, all")
        print("示例:")
        print("  python model_downloader.py all /path/to/resources")
        print("  python model_downloader.py funasr /path/to/resources")
        return

    model_type = sys.argv[1]
    resource_dir = sys.argv[2] if len(sys.argv) > 2 else None

    downloader = ModelDownloader(resource_dir)

    if model_type == 'all':
        print("开始下载所有缺失的模型...")
        results = downloader.download_missing_models()
        print("\n下载结果:")
        for m_type, success in results.items():
            print(f"  {downloader.MODELS[m_type]['name']}: {'成功' if success else '失败'}")
    else:
        if model_type in downloader.MODELS:
            result = downloader.ensure_model(model_type, auto_download=True)
            if result:
                print(f"✅ {downloader.MODELS[model_type]['name']} 已就绪")
            else:
                print(f"❌ {downloader.MODELS[model_type]['name']} 安装失败")
        else:
            print(f"❌ 未知的模型类型: {model_type}")
            print(f"支持的模型类型: {', '.join(downloader.MODELS.keys())}")


if __name__ == '__main__':
    main()