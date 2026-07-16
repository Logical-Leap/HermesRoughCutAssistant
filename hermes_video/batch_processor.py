from __future__ import annotations
from pathlib import Path
from .config import AppConfig
from .media_scanner import iter_media_files
from .pipeline import prepare

def process_project(project: str | Path, config: AppConfig, edit_format: str | None = None) -> dict:
    path = Path(project).expanduser().resolve()
    if not list(iter_media_files(path, config) or []): return {"project": str(path), "status": "skipped", "reason": "no media files"}
    result = prepare(path, config, edit_format or config.default_edit_format)
    return {"project": str(path), **result}

def process_all_projects(projects_root: str | Path, config: AppConfig, edit_format: str | None = None) -> list[dict]:
    root = Path(projects_root).expanduser().resolve(); root.mkdir(parents=True, exist_ok=True); results = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."): continue
        try: results.append(process_project(child, config, edit_format))
        except Exception as exc: results.append({"project": str(child), "status": "failed", "error": str(exc)})
    return results
