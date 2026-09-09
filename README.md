# 本地 Qwen3-ASR 音频转文字 Skill

这是一个供 Codex 使用的本地音频转文字技能，基于官方 Qwen3-ASR 模型。它既可以处理单个音频，也可以批量处理整个文件夹；文件会按自然顺序转写，每完成一个文件就保存检查点，最后合并为一份 Markdown 文档。

## 官方项目与模型

- Qwen3-ASR 官方 GitHub：[QwenLM/Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR)
- 当前默认模型：[Qwen/Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)
- 可选复核模型：[Qwen/Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)

Qwen3-ASR 模型和官方推理框架由 Qwen 团队发布。本仓库只是面向 Codex 的本地部署与批量转写封装，不包含、也不重新分发模型权重。使用模型时请同时遵守官方仓库及模型页面中的许可证和使用条款。

## 主要特点

- **默认使用 0.6B 模型：** 对录音清晰的英语听力材料速度更快、显存占用更低；疑难片段可切换到 1.7B 复核。
- **完全本地处理：** 音频不会上传到在线转写服务。
- **大文件留在 D 盘：** 模型、Python 环境、缓存、临时文件、检查点和默认输出均放在 `D:\Qwen3-ASR`。
- **支持断点续传：** 每完成一个音频都会保存结果，中断后再次运行会自动跳过已完成文件。
- **适配 8GB 显存：** 长音频会拆成带少量重叠的 75 秒片段，转写后自动合并。
- **输出 Markdown：** 可识别并整理听力材料中的 `Text 1`、`Text 2` 等段落；不会在无法可靠判断时臆造说话人身份。

更详细的部署结构、技术选择和验证方式见[中文部署说明](references/deployment.md)。

## 仓库结构

```text
local-qwen3-asr-skill/
├── README.md                 中文使用说明
├── SKILL.md                  Codex 技能指令
├── agents/openai.yaml        Codex 界面信息
├── references/deployment.md  中文部署说明
└── scripts/
    ├── setup.ps1             D 盘安装脚本
    └── transcribe.py         音频转写脚本
```

## 安装

在 PowerShell 中进入仓库目录，然后执行：

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\你的Python路径\python.exe'
```

脚本默认安装到 `D:\Qwen3-ASR`，并从官方 Hugging Face 仓库下载 Qwen3-ASR-0.6B。请保证 D 盘有足够空间。

把本仓库文件夹复制到 Codex 的技能目录后，即可通过 `$local-qwen3-asr` 使用。技能目录通常为：

```text
C:\Users\你的用户名\.codex\skills\local-qwen3-asr
```

## 使用方法

最简单的用法是在 Codex 中直接说：

```text
使用 local-qwen3-asr，把 D:\音频文件夹 转成 Markdown。
```

也可以直接运行脚本：

```powershell
& 'D:\Qwen3-ASR\env\Scripts\python.exe' '.\scripts\transcribe.py' 'D:\音频文件夹' --output 'D:\Qwen3-ASR\outputs\听力原文.md'
```

常用选项：

- `--model 0.6B`：默认模型，适合清晰的课程、听力训练和普通录音。
- `--model 1.7B`：更大的模型，适合对疑难片段进行复核。
- `--language auto`：语言未知或中英混合时自动识别；默认按英语处理。
- `--device cpu`：使用系统内存和 CPU，不占 NVIDIA 显存，但速度会慢很多。
- `--overwrite`：忽略原检查点并从头转写；请仅在确实需要重做时使用。
- `--render-only`：不加载模型，只根据已有检查点重新生成并去重 Markdown。

## 为什么默认使用 0.6B

这套部署面向 RTX 4060 8GB 显存和清晰的英语听力音频。0.6B 速度更快，也更不容易显存不足。已经下载的 1.7B 不需要删除，遇到专有名词、重口音或转写明显异常的片段时，可以单独切换到 1.7B 复核。

## 中断后如何继续

直接重新执行原来的命令即可。脚本会读取输出文件旁边的 `.checkpoint.json`，自动跳过已经完成的音频。不要添加 `--overwrite`，否则会从头开始。

## 隐私与仓库范围

本仓库只包含技能说明和辅助脚本，不包含模型权重、音频、转写结果、缓存、账号凭据或本地 Python 环境。`.gitignore` 已排除这些内容，避免误上传大文件或私人数据。
