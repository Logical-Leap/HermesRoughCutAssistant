from __future__ import annotations

import subprocess
from pathlib import Path
from .ffmpeg_tools import command
from .logger import get_logger


def audio_extract_path(project_path: Path, asset_id: str) -> Path:
    return project_path / "02_AUDIO_EXTRACTS" / f"{asset_id}.wav"


def extract_audio(source_path: Path, output_path: Path) -> Path:
    log = get_logger(__name__)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        log.info("Audio extract already exists: %s", output_path)
        return output_path
    cmd = ["ffmpeg", "-y", "-i", str(source_path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output_path)]
    try:
        subprocess.run(command(cmd), check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found. Install with: brew install ffmpeg") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg audio extraction failed for {source_path}: {exc.stderr[-1000:]}") from exc
    log.info("Extracted audio %s -> %s", source_path, output_path)
    return output_path
