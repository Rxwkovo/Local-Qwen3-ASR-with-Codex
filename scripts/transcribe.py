#!/usr/bin/env python3
"""Batch-transcribe local audio with the D:\\Qwen3-ASR deployment."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


DEPLOY_ROOT = Path(r"D:\Qwen3-ASR")
DEFAULT_OUTPUT_ROOT = DEPLOY_ROOT / "outputs"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}


def configure_d_drive_caches() -> None:
    cache_root = DEPLOY_ROOT / "cache"
    temp_root = DEPLOY_ROOT / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        {
            "HF_HOME": str(cache_root / "huggingface"),
            "HUGGINGFACE_HUB_CACHE": str(cache_root / "huggingface" / "hub"),
            "TORCH_HOME": str(cache_root / "torch"),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
        }
    )


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def collect_audio(source: Path) -> list[Path]:
    if source.is_file() and source.suffix.casefold() in AUDIO_EXTENSIONS:
        return [source]
    if source.is_dir():
        return sorted(
            (p for p in source.iterdir() if p.is_file() and p.suffix.casefold() in AUDIO_EXTENSIONS),
            key=natural_key,
        )
    raise FileNotFoundError(f"未找到音频文件或文件夹：{source}")


def clean_transcript(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Put standard listening-test cues on their own paragraphs without rewriting content.
    cue = r"(?i)(?<!^)(?=\b(?:text|conversation|passage|question|questions|section|part)\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b)"
    parts = [part.strip() for part in re.split(cue, text) if part.strip()]
    return "\n\n".join(parts)


def normalized_for_comparison(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def format_listening_script(text: str) -> str:
    """Detect the two consecutive plays of each item and keep the clearer first copy."""
    text = re.sub(r"\s+", " ", text).strip()
    preamble: list[str] = []
    direction_match = re.match(
        r"^(.+?现在你有[^。！？]{0,160}(?:有关内容|试题内容)[。！？])\s*(.+)$",
        text,
    )
    if direction_match:
        preamble.append(direction_match.group(1).strip())
        text = direction_match.group(2).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s*", text) if s.strip()]
    if len(sentences) < 4:
        return clean_transcript(text)

    pending: list[str] = []
    items: list[str] = []
    i = 0
    while i < len(sentences):
        best: tuple[float, int, int] | None = None
        max_left = min(12, len(sentences) - i - 1)
        for left_size in range(1, max_left + 1):
            left_text = " ".join(sentences[i : i + left_size])
            left_norm = normalized_for_comparison(left_text)
            if len(left_norm.split()) < 4:
                continue
            right_start = i + left_size
            max_right = min(12, len(sentences) - right_start)
            for right_size in range(max(1, left_size - 2), min(max_right, left_size + 2) + 1):
                right_text = " ".join(sentences[right_start : right_start + right_size])
                score = SequenceMatcher(
                    None, left_norm, normalized_for_comparison(right_text), autojunk=False
                ).ratio()
                if score >= 0.84 and (best is None or score > best[0]):
                    best = (score, left_size, right_size)

        if best is None:
            pending.append(sentences[i])
            i += 1
            continue

        _, left_size, right_size = best
        if pending:
            if not items:
                preamble.extend(pending)
            else:
                items.append(" ".join(pending))
            pending = []
        items.append(" ".join(sentences[i : i + left_size]))
        i += left_size + right_size

    if pending:
        if items:
            items.append(" ".join(pending))
        else:
            preamble.extend(pending)

    # Only apply exercise-item formatting when repeated-play structure was detected.
    if len(items) < 2:
        return clean_transcript(text)

    blocks: list[str] = []
    if preamble:
        blocks.append(" ".join(preamble))
    for number, item in enumerate(items, start=1):
        blocks.append(f"### Text {number}\n\n{item}")
    return "\n\n".join(blocks)


def merge_overlapping_text(existing: str, new_text: str, max_words: int = 30) -> str:
    """Remove an exact normalized word overlap between consecutive chunks."""
    if not existing:
        return new_text.strip()
    left = existing.split()
    right = new_text.split()

    def normalized(word: str) -> str:
        return re.sub(r"[^a-z0-9']", "", word.casefold())

    limit = min(max_words, len(left), len(right))
    overlap = 0
    for size in range(limit, 2, -1):
        if [normalized(w) for w in left[-size:]] == [normalized(w) for w in right[:size]]:
            overlap = size
            break
    return " ".join(left + right[overlap:]).strip()


def transcribe_in_chunks(model, audio_path: Path, language: str | None, chunk_seconds: float) -> str:
    import librosa

    sample_rate = 16_000
    samples, _ = librosa.load(str(audio_path), sr=sample_rate, mono=True)
    chunk_size = int(chunk_seconds * sample_rate)
    overlap_size = int(0.75 * sample_rate)
    if len(samples) <= chunk_size:
        return model.transcribe(audio=(samples, sample_rate), language=language)[0].text

    merged = ""
    start = 0
    chunk_index = 0
    while start < len(samples):
        end = min(start + chunk_size, len(samples))
        chunk_index += 1
        print(
            f"  分段 {chunk_index}: {start / sample_rate:.1f}s–{end / sample_rate:.1f}s",
            flush=True,
        )
        part = model.transcribe(audio=(samples[start:end], sample_rate), language=language)[0].text
        merged = merge_overlapping_text(merged, part)
        if end >= len(samples):
            break
        start = max(end - overlap_size, start + 1)
    return merged


def default_output_path(source: Path) -> Path:
    stem = source.stem if source.is_file() else source.name
    return DEFAULT_OUTPUT_ROOT / f"{stem}-听力原文.md"


def load_checkpoint(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, records: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def render_markdown(source: Path, audio_files: list[Path], records: dict[str, str]) -> str:
    lines = [
        f"# {source.stem if source.is_file() else source.name} 听力原文",
        "",
        f"> 本地使用 Qwen3-ASR 转写；共 {len(audio_files)} 个音频文件。",
        "",
    ]
    for index, audio_path in enumerate(audio_files, start=1):
        title = audio_path.stem
        transcript = records.get(str(audio_path.resolve()), "*[尚未转写]*")
        lines.extend([f"## {index:02d}. {title}", "", transcript, ""])
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用本地 Qwen3-ASR-0.6B 将音频或文件夹批量转写为 Markdown。")
    parser.add_argument("input", type=Path, help="音频文件或包含音频的文件夹")
    parser.add_argument("--output", type=Path, help="输出 Markdown 文件")
    parser.add_argument("--language", default="English", help="语言名称；用 auto 自动识别（默认：English）")
    parser.add_argument(
        "--model",
        choices=("0.6B", "1.7B"),
        default="0.6B",
        help="本地模型大小（默认：0.6B）",
    )
    parser.add_argument("--chunk-seconds", type=float, default=75.0, help="长音频分段秒数（默认：75）")
    parser.add_argument(
        "--device",
        choices=("cuda", "cpu"),
        default="cuda",
        help="cuda 使用 NVIDIA 显卡；cpu 使用系统内存（默认：cuda）",
    )
    parser.add_argument("--overwrite", action="store_true", help="忽略断点并重新转写已有项目")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_d_drive_caches()

    source = args.input.expanduser().resolve()
    audio_files = collect_audio(source)
    if not audio_files:
        raise RuntimeError("文件夹中没有找到支持的音频文件。")

    output_path = (args.output or default_output_path(source)).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_path.with_suffix(".checkpoint.json")
    records = {} if args.overwrite else load_checkpoint(checkpoint_path)

    model_root = DEPLOY_ROOT / "models" / f"Qwen3-ASR-{args.model}"
    if not model_root.exists():
        raise RuntimeError(f"模型尚未部署：{model_root}")

    import torch
    from qwen_asr import Qwen3ASRModel

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("未检测到可用的 NVIDIA CUDA 显卡。")

    print(f"加载模型：{model_root}", flush=True)
    device_map = "cuda:0" if args.device == "cuda" else "cpu"
    dtype = torch.bfloat16 if args.device == "cuda" else torch.float32
    model = Qwen3ASRModel.from_pretrained(
        str(model_root),
        dtype=dtype,
        device_map=device_map,
        attn_implementation="sdpa",
        max_inference_batch_size=1,
        max_new_tokens=1024,
    )

    language = None if args.language.casefold() == "auto" else args.language
    for index, audio_path in enumerate(audio_files, start=1):
        key = str(audio_path.resolve())
        if key in records and not args.overwrite:
            print(f"[{index}/{len(audio_files)}] 已完成，跳过：{audio_path.name}", flush=True)
            continue
        print(f"[{index}/{len(audio_files)}] 转写：{audio_path.name}", flush=True)
        raw_text = transcribe_in_chunks(model, audio_path, language, args.chunk_seconds)
        records[key] = format_listening_script(raw_text)
        save_checkpoint(checkpoint_path, records)
        output_path.write_text(render_markdown(source, audio_files, records), encoding="utf-8")

    output_path.write_text(render_markdown(source, audio_files, records), encoding="utf-8")
    print(f"完成：{output_path}", flush=True)
    print(f"完成时间：{datetime.now().isoformat(timespec='seconds')}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已停止；下次运行会从断点继续。", file=sys.stderr)
        raise SystemExit(130)
