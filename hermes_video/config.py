from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    projects_root: str = "~/VideoProjects"
    transcription_engine: str = "faster-whisper"
    whisper_model: str = "base"
    language: str = "en"
    default_edit_format: str = "youtube_longform"
    min_clip_duration_seconds: float = 8
    max_clip_duration_seconds: float = 90
    filler_words: list[str] = Field(default_factory=lambda: ["um", "uh", "like", "you know", "kind of", "sort of", "basically", "actually"])
    hook_phrases: list[str] = Field(default_factory=lambda: [
        "the problem is", "the biggest thing", "what people do not understand", "the mistake is",
        "the real issue", "here is the solution", "the way I would do it", "this is why", "the point is"
    ])
    supported_video_extensions: list[str] = Field(default_factory=lambda: [".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".mxf"])
    supported_audio_extensions: list[str] = Field(default_factory=lambda: [".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"])
    final_cut_pro_app_name: str = "Final Cut Pro"


def load_config(config_path: str | Path | None = None) -> AppConfig:
    if config_path:
        path = Path(config_path).expanduser()
        if path.exists():
            return AppConfig.model_validate_json(path.read_text())
    local = Path("config.json")
    if local.exists():
        return AppConfig.model_validate_json(local.read_text())
    example = Path(__file__).resolve().parents[1] / "config.example.json"
    if example.exists():
        return AppConfig.model_validate_json(example.read_text())
    return AppConfig()


def _backup_existing(path: Path) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(path.read_bytes())


def write_json_safe(path: Path, data: dict | list, *, backup: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        _backup_existing(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


def write_text_safe(path: Path, text: str, *, backup: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        _backup_existing(path)
    path.write_text(text)
    return path
