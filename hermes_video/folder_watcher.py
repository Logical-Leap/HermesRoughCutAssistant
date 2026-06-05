from __future__ import annotations

import time
from pathlib import Path
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass
    Observer = None  # type: ignore[assignment]
from .config import AppConfig
from .logger import get_logger
from .project_scaffold import init_project
from .metadata_extractor import scan_project
from .transcription import transcribe_project
from .transcript_analyzer import analyze_project
from .edit_decision_builder import build_edit_decisions
from .fcpxml_generator import build_fcpxml
from .applescript_generator import build_applescript
from .video_renderer import render_project


class RoughCutEventHandler(FileSystemEventHandler):
    def __init__(self, projects_root: Path, config: AppConfig):
        self.projects_root = projects_root
        self.config = config
        self.log = get_logger(__name__)
        self.pending: dict[Path, float] = {}

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        extensions = {e.lower() for e in self.config.supported_video_extensions + self.config.supported_audio_extensions}
        if path.suffix.lower() not in extensions:
            return
        if any(part in {"02_AUDIO_EXTRACTS", "03_TRANSCRIPTS", "04_ANALYSIS", "05_EDIT_DECISIONS", "06_FCPXML", "07_APPLESCRIPT", "08_EXPORTS", ".git"} for part in path.parts):
            return
        project = self._project_for(path)
        if project:
            self.pending[project] = time.time()
            self.log.info("Queued project after new media: %s", project)

    def _project_for(self, path: Path) -> Path | None:
        try:
            rel = path.relative_to(self.projects_root)
        except ValueError:
            return None
        return self.projects_root / rel.parts[0] if rel.parts else None

    def process_due(self, quiet_seconds: int = 20):
        now = time.time()
        for project, changed_at in list(self.pending.items()):
            if now - changed_at >= quiet_seconds:
                self.pending.pop(project, None)
                try:
                    init_project(project)
                    scan_project(project, self.config)
                    transcribe_project(project, self.config)
                    analyze_project(project, self.config)
                    build_edit_decisions(project, self.config.default_edit_format, self.config)
                    build_fcpxml(project)
                    build_applescript(project, self.config)
                    render_project(project)
                except Exception as exc:
                    self.log.exception("Automatic processing failed for %s: %s", project, exc)


def _project_media_snapshot(project: Path, config: AppConfig) -> tuple[int, float]:
    extensions = {e.lower() for e in config.supported_video_extensions + config.supported_audio_extensions}
    generated = {"02_AUDIO_EXTRACTS", "03_TRANSCRIPTS", "04_ANALYSIS", "05_EDIT_DECISIONS", "06_FCPXML", "07_APPLESCRIPT", "08_EXPORTS", ".git"}
    count = 0
    latest = 0.0
    for path in project.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            rel = path.relative_to(project)
        except ValueError:
            continue
        if any(part in generated or part.startswith(".") for part in rel.parts):
            continue
        count += 1
        latest = max(latest, path.stat().st_mtime)
    return count, latest


def _poll_projects(root: Path, config: AppConfig):
    from .batch_processor import process_project
    log = get_logger(__name__)
    seen: dict[Path, tuple[int, float]] = {}
    log.info("watchdog not installed; using polling watcher for %s", root)
    while True:
        for project in sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]):
            snap = _project_media_snapshot(project, config)
            if snap[0] == 0:
                continue
            if seen.get(project) != snap:
                seen[project] = snap
                try:
                    log.info("Processing changed project: %s", project)
                    process_project(project, config, config.default_edit_format)
                except Exception as exc:
                    log.exception("Polling processing failed for %s: %s", project, exc)
        time.sleep(15)


def watch_projects(projects_root: str | Path, config: AppConfig):
    root = Path(projects_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if Observer is None:
        _poll_projects(root, config)
        return
    handler = RoughCutEventHandler(root, config)
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    log = get_logger(__name__)
    log.info("Watching %s for new raw footage", root)
    try:
        while True:
            time.sleep(5)
            handler.process_due()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
