# 🩺 ​​VetVoice | 兽医声动

<div align="center">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 25px; text-align: center;">
    <p style="font-size: 48px;" >兽医声动，诊疗更高效</p>
  </div>
</div>

</div>

<div align="center" style="margin: 30px 0;">
  <img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="800">
</div>

---
# 🎉 新闻
- [X] [2025.8.26]🎊🔥 python版发布🔥🎊
# 项目简介
VetVoice（兽医声动）​​ 是基于 ​PySide6 + FunASR + LLM​ 的智能语音病历系统，支持：

. 实时语音转文字（中英文）
. 自动区分医生/宠主对话
. 大模型辅助生成病例、诊断建议
. 一键导出PDF/WAV
. 适用于宠物医院、兽医诊所等场景，解决手写病历效率低下的痛点。
# 核心功能
## 实时语音识别

. 基于 FunASR，支持长语音断句和静音检测
. 自适应降噪，提升嘈杂环境下的识别准确率

## 实时说话人分离

. 自动标记医生与宠主对话（不同颜色/对齐方式）
. 支持多人对话场景

## 实时大模型辅助诊疗

. ​病例生成​：语音输入→结构化病历（主诉、现病史等）
. ​辅助诊断​：大模型分析对话，提供鉴别诊断建议
. ​用药指导​：自动生成用法用量（需接入大模型API）

## 一键导出

. 保存原始音频文件（WAV格式）,批量导出PDF病历


# 下载

通过网盘分享的文件：[resources.zip]
链接: https://pan.baidu.com/s/1G7meKwqaXdENkQ3HiEq4Dw?pwd=5d5k 提取码: 5d5k

# 使用
参数配置:
configs/default.toml
```toml
#大模型接口
api_key = "EMPTY"    #修改
api_base = "http://192.168.1.100:8000/v1"  #修改
model = " Qwen3" #修改

```

python环境启动
```bash
git clone https://github.com/georgewangchn/VetVoice.git
cd VetVoice
pip install torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
python app.py
```

# 致谢pip
感谢以下优秀开源项目的支持：

. [FunASR](https://github.com/modelscope/FunASR)

. [pyannote-audio](https://github.com/pyannote/pyannote-audio)

. [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)



# 🪪 [许可证](LICENSE)
VetVoice 还包含多种第三方组件及从其他代码库修改而来的部分代码（这些内容遵循其他开源许可证）。
预训练模型的使用需遵守相应模型的许可证要求。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=georgewangchn/VetVoice.git&type=Date)](https://www.star-history.com/#georgewangchn/VetVoice.git&Date)