from __future__ import annotations

from pathlib import Path
from .config import AppConfig


def iter_media_files(project_path: Path, config: AppConfig):
    raw = project_path / "01_RAW"
    extensions = {e.lower() for e in config.supported_video_extensions + config.supported_audio_extensions}
    if not raw.exists():
        return
    for path in sorted(raw.rglob("*")):
        if path.is_file() and path.suffix.lower() in extensions and not path.name.startswith("."):
            yield path


def classify_media(path: Path, config: AppConfig) -> str:
    ext = path.suffix.lower()
    if ext in {e.lower() for e in config.supported_video_extensions}:
        return "video"
    if ext in {e.lower() for e in config.supported_audio_extensions}:
        return "audio"
    return "unknown"
