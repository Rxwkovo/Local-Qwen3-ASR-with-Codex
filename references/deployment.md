# Deployment and design notes

## Chosen architecture

- Default model: official `Qwen/Qwen3-ASR-0.6B` checkpoint.
- Runtime: official `qwen-asr` Transformers backend with CUDA.
- Target hardware: NVIDIA RTX 4060 with 8 GB VRAM.
- Processing mode: one audio file at a time, batch size 1, BF16, SDPA attention, with 75-second chunks for 8 GB VRAM.
- Storage root: `D:\Qwen3-ASR` for the environment, weights, caches, temporary files, checkpoints, and default outputs.

## Decision summary

The 0.6B model is selected for clear, studio-recorded English listening exercises because it is faster and uses less VRAM. The already available 1.7B deployment can be used later to recheck difficult passages. A full multi-minute recording can exceed 8 GB VRAM because attention memory grows quickly with audio length, so the helper uses overlapping 75-second chunks and removes exact word overlap when merging. Sequential processing limits peak VRAM use and is more reliable for a large folder. A JSON checkpoint is written after every audio file so a long job can resume without repeating completed files. Speaker labels are not guessed because ASR alone does not provide reliable diarization.

`--device cpu` places the model in system RAM and uses FP32 CPU inference. It is a fallback for machines without enough GPU memory and is substantially slower than chunked CUDA inference. On the target machine, 32 GB RAM is sufficient for this mode, but CUDA remains the default.

The standard package depends on optional demo-server libraries. This deployment installs only the local inference dependencies needed by the batch script; Gradio and Flask are intentionally omitted.

## Layout

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

The Codex skill itself is small and lives in the normal Codex skills directory. It references this D-drive runtime without copying model files.

## Recreate or repair

Run `scripts/setup.ps1` from PowerShell. It accepts a Python 3.12 executable and defaults to `D:\Qwen3-ASR`.

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\path\to\python.exe'
```

The setup script keeps all package caches and temporary downloads on the selected installation drive. It downloads the model from the official Hugging Face repository.

## Verification

```powershell
& 'D:\Qwen3-ASR\env\Scripts\python.exe' -c "import torch; from qwen_asr import Qwen3ASRModel; print(torch.cuda.is_available())"
& 'D:\Qwen3-ASR\env\Scripts\python.exe' '.\scripts\transcribe.py' --help
```

For a real smoke test, transcribe one short audio file and inspect the Markdown before starting a large folder.
