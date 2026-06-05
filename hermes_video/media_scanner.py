from __future__ import annotations

from pathlib import Path
from .config import AppConfig

GENERATED_DIRS = {
    "02_AUDIO_EXTRACTS",
    "03_TRANSCRIPTS",
    "04_ANALYSIS",
    "05_EDIT_DECISIONS",
    "06_FCPXML",
    "07_APPLESCRIPT",
    "08_EXPORTS",
    ".git",
    "__pycache__",
}


def _is_generated_or_hidden(project_path: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(project_path)
    except ValueError:
        return True
    return any(part in GENERATED_DIRS or part.startswith(".") for part in rel.parts)


def iter_media_files(project_path: Path, config: AppConfig):
    """Yield media from the user's simple project folder.

    The preferred workflow is now: create a folder under the projects root and drop
    clips/music directly into it. The older 01_RAW subfolder layout still works,
    but it is no longer required.
    """
    extensions = {e.lower() for e in config.supported_video_extensions + config.supported_audio_extensions + config.supported_image_extensions}
    search_root = project_path
    for path in sorted(search_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions or path.name.startswith("."):
            continue
        if _is_generated_or_hidden(project_path, path):
            continue
        yield path


def classify_media(path: Path, config: AppConfig) -> str:
    ext = path.suffix.lower()
    if ext in {e.lower() for e in config.supported_video_extensions}:
        return "video"
    if ext in {e.lower() for e in config.supported_audio_extensions}:
        return "audio"
    if ext in {e.lower() for e in config.supported_image_extensions}:
        return "image"
    return "unknown"
