<div align="center">

# 🩺 VetVoice — 兽医声动

### 🎙️ 让兽医 **只需说话**，AI 自动完成电子病历

实时语音识别 · 多人对话分离 · AI 辅助诊疗 · 自动生成病例

<p>
  <img src="https://img.shields.io/badge/Python-3.10-blue">
  <img src="https://img.shields.io/badge/PySide6-GUI-green">
  <img src="https://img.shields.io/badge/FunASR-Realtime-orange">
  <img src="https://img.shields.io/badge/LLM-Agent-purple">
</p>

</div>

<div align="center" style="margin: 30px 0;">
  <img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="800">
</div>

> VetVoice 是一个面向宠物医院的 AI 语音病历助手，将 **诊疗对话实时转换为结构化电子病历**。

---

## 🤔 为什么需要 VetVoice？

传统宠物诊疗存在：

- ✍️ 手写病历耗时
- 🧠 医生边问边记录负担大
- 📄 病历结构不统一
- ⏱️ 接诊效率低

VetVoice 让医生：

✅ 只需专注沟通
✅ AI 自动记录
✅ 自动生成标准病历

---

## 🚀 核心能力

### 🎧 实时语音理解
- WebRTC 实时降噪
- 长语音连续识别
- 嘈杂诊室高准确率

### 👥 多说话人自动识别
- 自动区分医生 / 宠主
- 彩色对话显示
- 多人场景支持

### 🧠 AI 智能诊疗 Agent

自动完成：

1️⃣ 问诊整理
2️⃣ 检查建议
3️⃣ 结果分析
4️⃣ 诊断与治疗生成

### 📄 一键生成医疗文档
- PDF 病历导出
- WAV 原始录音保存

---

## 🧩 技术架构

```
麦克风
   ↓
WebRTC APM（降噪）
   ↓
FunASR Streaming ASR
   ↓
Speaker Diarization
   ↓
LLM Agent (MCP)
   ↓
结构化电子病历
```

---

## ⚡ Quick Start（3分钟运行）

```bash
git clone https://github.com/georgewangchn/VetVoice.git
cd VetVoice
python3.12 -v venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 📺 Demo 展示

| ![图片1](img/1.png) | ![图片2](img/2.png) | ![图片3](img/3.png) |
|----------------------|----------------------|----------------------|
| 实时语音识别                | 开始agent                | 对话填充电子病历                |

---

## 📖 详细使用说明

### 环境要求
- **Python 3.12**（推荐3.10～3.12）
- 支持系统：Windows / macOS / Linux
- 硬件要求：建议至少4GB内存用于模型加载

### 首次使用配置

#### 1. 用户注册
- 启动程序后进入注册页面
- 填写用户名和密码完成注册

#### 2. 登录设置
- 使用注册的账号登录
- **资源路径设置**：指定模型文件保存目录（建议选择有足够空间的磁盘）
- **保存路径设置**：指定录制的音频和导出病历的保存目录

#### 3. 模型自动下载
- 系统首次启动时会自动检测所需模型
- 如发现模型不存在，会自动开始下载过程
- **支持的模型**：
  - 语音识别模型（paraformer-zh-streaming）
  - 说话人识别模型（wespeaker-voxceleb-resnet34-LM）
- 下载过程支持断点续传，可随时暂停和恢复
- 下载完成后模型自动保存到指定的资源路径

#### 4. 大模型参数设置
- 进入参数页面配置LLM接口
- **支持格式**：OpenAI兼容API格式
- **必需参数**：
  - API地址（如：https://api.openai.com/v1）
  - API密钥（填写相应的服务密钥）
- **可选参数**：
  - 模型名称（如：gpt-4, gpt-3.5-turbo等）
  - 温度参数（控制生成随机性）

#### 5. 重启程序
- 配置完成后需重启程序使设置生效
- 模型下载完成后重启即可开始使用

### 日常使用流程

#### 开始诊疗
1. 登录系统
2. 点击"开始录音"按钮
3. 对话过程中系统实时：
   - 语音降噪处理
   - 语音转文字
   - 自动识别说话人（医生/宠主）
4. 点击"停止录音"结束

#### 辅助诊断
1. 点击"开始agent"启动AI辅助
2. 系统智能整理电子病历，支持4个阶段：
   - 问诊阶段
   - 开检查阶段
   - 查看检查结果阶段
   - 确诊治疗阶段
3. AI根据对话内容自动填充病历结构化信息

#### 导出保存
1. 查看/编辑生成的病历内容
2. 点击导出按钮保存为PDF格式
3. 原始录音文件自动保存为WAV格式

### 注意事项
- 首次启动模型下载需要稳定网络环境
- 建议使用全向会议麦克风以获得最佳降噪效果
- 大模型调用消耗API调用次数，请根据实际需求配置

---

## 🎉 新闻
- [X] [2026.04.02]🎯📢 模型自动下载，升级Python3.12版本，升级Torch2.11.0。
- [X] [2025.09.10]🎯📢 支持agent/mcp智能体，智能整理电子病历4个阶段：问诊阶段 / 开检查阶段 / 查看检查结果阶段 / 确诊治疗阶段。
- [X] [2025.08.26]🎊🔥 基于Python3.10版发布🔥🎊

---

## 🗺️ Roadmap
- [ ] pyinstaller打包windows/ubuntu/macos平台安装包
- [ ] 开放http/mcp控制接口：当前病例号/开始录音/停止录音/辅诊/检查确诊/推荐用药/电子病历等
- [x] 采用fastmcp开发对话mcp，电子病历流程从人控制转向agent控制（开发测试使用模型：gpt-5-nano）
- [ ] 推荐用户分享样本训练模型提升效果
- [ ] 性能优化

---

## 💡 技术亮点

**AI Medical Agent** + **Realtime Speech** + **MCP**

VetVoice 结合了实时语音识别与 AI Agent 技术，实现医疗场景下的智能辅助决策与自动化病历生成。

- **Real-time Speech to Text**: 基于 FunASR 的流式 ASR，支持长语音实时识别
- **Speaker Diarization**: 自动区分医生与宠主对话
- **LLM Agent Workflow**: MCP 协议驱动的多阶段医疗流程（问诊→检查→结果→治疗）
- **Medical Structuring**: 将非结构化诊疗对话转换为标准化电子病历

---

## 🙏 致谢

感谢以下优秀开源项目的支持：

- [FunASR](https://github.com/modelscope/FunASR)
- [pyannote-audio](https://github.com/pyannote/pyannote-audio)
- [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)

---

## 📄 License

[Apache License 2.0](LICENSE)

VetVoice 还包含多种第三方组件及从其他代码库修改而来的部分代码（这些内容遵循其他开源许可证）。
预训练模型的使用需遵守相应模型的许可证要求。

---

<div align="center">

## ⭐ Star History

如果这个项目对你有帮助，请点一个 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=georgewangchn/VetVoice&type=Date)](https://www.star-history.com/#georgewangchn/VetVoice&Date)

**Keywords**: AI Medical Agent · Realtime Clinical Documentation · Veterinary AI Assistant
</div>
