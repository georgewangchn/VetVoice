---
name: model_path_fix
description: 模型路径修复记录
type: reference
---

# 模型路径修复记录

## 问题
模型下载后存储在 `resource_dir/.cache/shuai1618/` 下，但配置和加载路径不一致，导致无法正确加载模型。

## 解决方案

### 1. 更新配置文件路径
- **settings.py**:
  - `model_funasr_path`: `funasr/paraformer-zh-streaming` → `.cache/shuai1618/paraformer-zh-streaming`
  - `model_vosk_path`: `vosk/vosk-model-small-cn` → `.cache/shuai1618/vosk-model-small-cn`
  - `model_pyannote_path`: `spk/speaker-diarization` → `.cache/shuai1618/speaker-diarization`

### 2. 修改下载器逻辑
- **utils/model_downloader.py**:
  - 移除模型移动逻辑，保持模型在 `.cache` 目录
  - 更新模型检查路径使用 `cache_path` 而非 `sub_path`
  - 下载脚本不再执行 `shutil.move`

### 3. 更新资源目录管理
- **utils/resource_path.py**:
  - `ensure_resource_dirs()`: 创建 `.cache/shuai1618/` 目录而非 `funasr/`, `spk/`, `vosk/`
  - `check_resources_available()`: 检查 `.cache/shuai1618/` 下的模型文件

### 4. 修复UI回调
- **ui/components/set_panel.py**:
  - 修复 `_restore_download_ui` 方法中的回调注册错误
  - 使用 lambda 函数发送信号而非直接调用不存在的方法

## 最终的模型文件结构
```
resource_dir/
└── .cache/
    └── shuai1618/
        ├── paraformer-zh-streaming/
        ├── speaker-diarization/
        └── vosk-model-small-cn/
```

## 验证
模型现在会保持下载位置并从正确的路径加载，无需移动操作。