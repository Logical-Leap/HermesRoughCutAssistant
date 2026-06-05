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


def watch_projects(projects_root: str | Path, config: AppConfig):
    root = Path(projects_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    handler = RoughCutEventHandler(root, config)
    if Observer is None:
        raise RuntimeError("watchdog is not installed. Run scripts/install_dependencies.sh or python -m pip install watchdog.")
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
