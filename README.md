# Local Qwen3-ASR Skill

A Codex skill for private, local batch transcription with the official Qwen3-ASR model. It accepts one audio file or a folder, preserves natural file order, checkpoints after each file, and produces a combined Markdown transcript.

## Why this setup

- **Fast for clear recordings:** defaults to Qwen3-ASR-0.6B; 1.7B can recheck difficult passages.
- **Local processing:** audio is not uploaded to a transcription service.
- **D-drive storage:** model weights, the Python environment, caches, temporary downloads, and checkpoints stay under `D:\Qwen3-ASR`.
- **Resumable batches:** completed files are recorded after every transcription.
- **8 GB GPU friendly:** long recordings are split into overlapping 75-second chunks and merged automatically.
- **Conservative formatting:** listening-test cues are separated when recognized; speaker identities are never guessed.

See [`references/deployment.md`](references/deployment.md) for the deployment layout, reproducible setup, verification commands, and the main design tradeoffs.

## Repository contents

```text
local-qwen3-asr-skill/
├── SKILL.md
├── agents/openai.yaml
├── references/deployment.md
└── scripts/
    ├── setup.ps1
    └── transcribe.py
```

## Usage

After installing the skill, ask Codex to use `$local-qwen3-asr` with an audio file or folder. For direct execution:

```powershell
& 'D:\Qwen3-ASR\env\Scripts\python.exe' '.\scripts\transcribe.py' 'D:\path\to\audio-folder' --output 'D:\Qwen3-ASR\outputs\transcript.md'
```

Use `--language auto` for unknown or mixed-language recordings. The default is English.
Add `--device cpu` to run from system RAM instead of NVIDIA VRAM; this is supported but much slower.
Use `--model 1.7B` to switch to the larger locally installed model for difficult passages; the default is `--model 0.6B`.

## Privacy and repository scope

This repository contains only the skill instructions and helper scripts. Model weights, audio, transcripts, caches, credentials, and local environment files are excluded.
