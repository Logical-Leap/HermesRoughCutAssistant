from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    projects_root: str = "~/VideoProjects"
    transcription_engine: str = "faster-whisper"
    whisper_model: str = "large-v3"
    language: str = "en"
    word_timestamps: bool = True
    scene_detection: bool = True
    visual_quality_metrics: bool = True
    speaker_diarization: bool = False
    face_detection: bool = False
    retake_detection: bool = True
    editorial_provider: str = "deterministic"
    editorial_model: str = ""
    editorial_base_url: str = ""
    editorial_api_key_env: str = "EDITORIAL_MODEL_API_KEY"
    maximum_project_tokens: int = 150000
    maximum_model_calls: int = 24
    maximum_project_cost_usd: float = 5.0
    maximum_retries: int = 2
    default_style: str = "chandler_default"
    default_edit_format: str = "youtube_longform"
    minimum_pause_seconds: float = 0.18
    maximum_automatic_reorder_distance: int = 6
    preserve_chronology_by_default: bool = True
    generate_conservative_cut: bool = True
    generate_aggressive_cut: bool = True
    review_host: str = "127.0.0.1"
    review_port: int = 8765
    rendering_enabled_by_default: bool = False
    preview_resolution: str = "1280x720"
    min_clip_duration_seconds: float = 8
    max_clip_duration_seconds: float = 90
    filler_words: list[str] = Field(default_factory=lambda: ["um", "uh", "like", "you know", "kind of", "sort of", "basically", "actually"])
    hook_phrases: list[str] = Field(default_factory=lambda: ["the problem is", "the biggest thing", "what people do not understand", "the mistake is", "the real issue", "here is the solution", "the way I would do it", "this is why", "the point is"])
    supported_video_extensions: list[str] = Field(default_factory=lambda: [".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".mxf"])
    supported_audio_extensions: list[str] = Field(default_factory=lambda: [".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"])
    supported_image_extensions: list[str] = Field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"])
    final_cut_pro_app_name: str = "Final Cut Pro"


def _toml_to_config(raw: dict) -> dict:
    projects, transcription = raw.get("projects", {}), raw.get("transcription", {})
    analysis, editorial = raw.get("analysis", {}), raw.get("editorial", {})
    editing, review, rendering = raw.get("editing", {}), raw.get("review", {}), raw.get("rendering", {})
    return {
        "projects_root": projects.get("root", "~/VideoProjects"),
        "transcription_engine": transcription.get("engine", "faster-whisper"),
        "whisper_model": transcription.get("model", "large-v3"),
        "language": transcription.get("language", "en"),
        "word_timestamps": transcription.get("word_timestamps", True),
        "scene_detection": analysis.get("scene_detection", True),
        "visual_quality_metrics": analysis.get("visual_quality_metrics", True),
        "speaker_diarization": analysis.get("speaker_diarization", False),
        "face_detection": analysis.get("face_detection", False),
        "retake_detection": analysis.get("retake_detection", True),
        "editorial_provider": editorial.get("provider", "deterministic"),
        "editorial_model": editorial.get("model", ""),
        "editorial_base_url": editorial.get("base_url", ""),
        "editorial_api_key_env": editorial.get("api_key_env", "EDITORIAL_MODEL_API_KEY"),
        "maximum_project_tokens": editorial.get("maximum_project_tokens", 150000),
        "maximum_model_calls": editorial.get("maximum_total_model_calls", 24),
        "maximum_project_cost_usd": editorial.get("maximum_project_cost_usd", 5.0),
        "maximum_retries": editorial.get("maximum_retries", 2),
        "default_style": editorial.get("default_style", "chandler_default"),
        "default_edit_format": editing.get("default_format", "youtube_longform"),
        "minimum_pause_seconds": editing.get("minimum_pause_seconds", 0.18),
        "maximum_automatic_reorder_distance": editing.get("maximum_automatic_reorder_distance", 6),
        "preserve_chronology_by_default": editing.get("preserve_chronology_by_default", True),
        "generate_conservative_cut": editing.get("generate_conservative_cut", True),
        "generate_aggressive_cut": editing.get("generate_aggressive_cut", True),
        "review_host": review.get("host", "127.0.0.1"),
        "review_port": review.get("port", 8765),
        "rendering_enabled_by_default": rendering.get("enabled_by_default", False),
        "preview_resolution": rendering.get("preview_resolution", "1280x720"),
    }


def load_config(config_path: str | Path | None = None) -> AppConfig:
    candidates = [Path(config_path).expanduser()] if config_path else [Path("config.toml"), Path("config.json")]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".toml":
            import tomllib
            return AppConfig.model_validate(_toml_to_config(tomllib.loads(path.read_text())))
        return AppConfig.model_validate_json(path.read_text())
    return AppConfig()


def _backup_existing(path: Path) -> None:
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path.with_suffix(path.suffix + f".{stamp}.bak").write_bytes(path.read_bytes())


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(text)
    temp.replace(path)


def write_json_safe(path: Path, data: dict | list, *, backup: bool = True) -> Path:
    if backup:
        _backup_existing(path)
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


def write_text_safe(path: Path, text: str, *, backup: bool = True) -> Path:
    if backup:
        _backup_existing(path)
    _atomic_write(path, text)
    return path
