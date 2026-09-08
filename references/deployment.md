# 部署与设计说明

官方来源：

- [Qwen3-ASR 官方 GitHub](https://github.com/QwenLM/Qwen3-ASR)
- [Qwen3-ASR-0.6B 模型](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)
- [Qwen3-ASR-1.7B 模型](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)

## 当前部署方案

- 默认模型：官方 `Qwen/Qwen3-ASR-0.6B`。
- 运行方式：官方 `qwen-asr` Transformers 后端，默认使用 CUDA。
- 目标硬件：NVIDIA RTX 4060，8GB 显存。
- 处理模式：每次处理一个音频，批量大小为 1，使用 BF16、SDPA 注意力和 75 秒分段。
- 存储根目录：`D:\Qwen3-ASR`，用于存放环境、模型、缓存、临时文件、检查点和默认输出。

## 设计选择

0.6B 适合清晰、录制规范的英语听力材料：速度更快，占用显存更少。已经安装的 1.7B 可以保留，用于复核少量疑难片段。完整的十几分钟音频会使注意力计算占用大量显存，因此脚本会把音频切成相互重叠的 75 秒片段，并在合并时删除精确重复的词。所有文件按顺序逐个处理，以控制显存峰值。每完成一个音频就写入 JSON 检查点，使长任务可以断点续传。由于普通 ASR 不提供可靠的说话人分离，脚本不会凭空添加 M、W 等说话人标签。

`--device cpu` 会把模型放在系统内存中并使用 FP32 CPU 推理。这适合显存不足或没有 NVIDIA 显卡的情况，但比 CUDA 分段推理慢很多。目标电脑的 32GB 内存可以运行这种模式，不过默认仍使用 CUDA。

官方软件包的演示服务器还依赖额外组件。本方案只安装批量本地推理所需依赖，不安装 Gradio 和 Flask，以减少空间占用和无关依赖。

## D 盘目录结构

```text
D:\Qwen3-ASR\
├── env\
├── models\Qwen3-ASR-0.6B\
├── cache\
│   ├── huggingface\
│   ├── pip\
│   └── torch\
├── tmp\
└── outputs\
```

Codex Skill 本身体积很小，仍放在 Codex 的标准技能目录中；它直接调用 D 盘运行环境，不会把模型复制到 C 盘。

## 重新安装或修复

在 PowerShell 中运行 `scripts/setup.ps1`。脚本接受 Python 3.12 可执行文件路径，默认安装到 `D:\Qwen3-ASR`。

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\path\to\python.exe'
```

安装脚本会把软件包缓存和临时下载内容留在所选安装盘，并从官方 Hugging Face 仓库下载模型。

## 验证安装

```powershell
& 'D:\Qwen3-ASR\env\Scripts\python.exe' -c "import torch; from qwen_asr import Qwen3ASRModel; print(torch.cuda.is_available())"
& 'D:\Qwen3-ASR\env\Scripts\python.exe' '.\scripts\transcribe.py' --help
```

正式批量处理前，建议先转写一个短音频并检查 Markdown 输出。
