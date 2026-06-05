from __future__ import annotations

from pathlib import Path
from .logger import get_logger

OUTPUT_DIRS = [
    "02_AUDIO_EXTRACTS",
    "03_TRANSCRIPTS",
    "04_ANALYSIS",
    "05_EDIT_DECISIONS",
    "06_FCPXML",
    "07_APPLESCRIPT",
    "08_EXPORTS",
]

OPTIONAL_RAW_DIRS = ["01_RAW/A_CAM", "01_RAW/B_CAM", "01_RAW/IPHONE", "01_RAW/AUDIO"]

PROJECT_DIRS = OPTIONAL_RAW_DIRS + OUTPUT_DIRS


def init_projects_root(projects_root: str | Path) -> Path:
    root = Path(projects_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    get_logger(__name__).info("Video projects root is ready at %s", root)
    return root


def init_project(project: str | Path, *, raw_subfolders: bool = False) -> Path:
    """Create a project folder that accepts direct file drops.

    By default this does not force the old 01_RAW layout. Users can create a
    folder under the projects root, drop videos/music directly into it, and run
    the pipeline. The generated output folders are still created so results stay
    organized and do not get rescanned as source media.
    """
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    dirs = PROJECT_DIRS if raw_subfolders else OUTPUT_DIRS
    for folder in dirs:
        (project_path / folder).mkdir(parents=True, exist_ok=True)
    log.info("Initialized project at %s", project_path)
    return project_path
