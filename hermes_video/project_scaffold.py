from __future__ import annotations

from pathlib import Path
from .logger import get_logger

PROJECT_DIRS = [
    "01_RAW/A_CAM", "01_RAW/B_CAM", "01_RAW/IPHONE", "01_RAW/AUDIO",
    "02_AUDIO_EXTRACTS", "03_TRANSCRIPTS", "04_ANALYSIS", "05_EDIT_DECISIONS",
    "06_FCPXML", "07_APPLESCRIPT", "08_EXPORTS"
]


def init_project(project: str | Path) -> Path:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    for folder in PROJECT_DIRS:
        (project_path / folder).mkdir(parents=True, exist_ok=True)
    log.info("Initialized project scaffold at %s", project_path)
    return project_path
