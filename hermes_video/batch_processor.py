from __future__ import annotations

from pathlib import Path
from .config import AppConfig
from .logger import get_logger
from .media_scanner import iter_media_files
from .project_scaffold import init_project
from .metadata_extractor import scan_project
from .transcription import transcribe_project
from .transcript_analyzer import analyze_project
from .edit_decision_builder import build_edit_decisions
from .fcpxml_generator import build_fcpxml
from .applescript_generator import build_applescript
from .video_renderer import render_project


def process_project(project: str | Path, config: AppConfig, edit_format: str | None = None) -> dict:
    project_path = init_project(project)
    media_files = list(iter_media_files(project_path, config) or [])
    if not media_files:
        return {"project": str(project_path), "status": "skipped", "reason": "no media files"}
    scan_project(project_path, config)
    transcribe_project(project_path, config)
    analyze_project(project_path, config)
    build_edit_decisions(project_path, edit_format or config.default_edit_format, config)
    build_fcpxml(project_path)
    build_applescript(project_path, config)
    outputs = render_project(project_path)
    return {"project": str(project_path), "status": "processed", "media_files": len(media_files), "outputs": outputs}


def process_all_projects(projects_root: str | Path, config: AppConfig, edit_format: str | None = None) -> list[dict]:
    log = get_logger(__name__)
    root = Path(projects_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        try:
            result = process_project(child, config, edit_format)
            results.append(result)
            log.info("%s: %s", result["status"], child)
        except Exception as exc:
            log.exception("Failed processing %s: %s", child, exc)
            results.append({"project": str(child), "status": "failed", "error": str(exc)})
    return results
