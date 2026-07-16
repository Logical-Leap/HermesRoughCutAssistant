from __future__ import annotations

import subprocess
from pathlib import Path

from .config import AppConfig, write_text_safe
from .logger import get_logger


def latest_fcpxml(project_path: Path, timeline: str | None = None) -> Path:
    root = project_path / "06_FCPXML"
    candidates = list(root.glob("*.fcpxml"))
    if timeline:
        matching = [path for path in candidates if f"_{timeline}_" in path.name or path.name.endswith(f"_{timeline}.fcpxml")]
        if not matching:
            raise FileNotFoundError(f"No {timeline} FCPXML found. Run export-fcpxml --timeline {timeline} first.")
        candidates = matching
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No FCPXML found. Run export-fcpxml first.")
    return candidates[0]


def build_applescript(project: str | Path, config: AppConfig, timeline: str | None = None) -> Path:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    fcpxml = latest_fcpxml(project_path, timeline)
    script = f'tell application "{config.final_cut_pro_app_name}"\nactivate\nopen POSIX file "{fcpxml}"\nend tell\n'
    out = project_path / "07_APPLESCRIPT" / "import_to_final_cut.applescript"
    write_text_safe(out, script)
    log.info("Generated AppleScript for %s: %s", timeline or "latest", out)
    return out


def open_in_fcp(project: str | Path, config: AppConfig, timeline: str | None = None) -> None:
    project_path = Path(project).expanduser().resolve()
    script = build_applescript(project_path, config, timeline)
    subprocess.run(["osascript", str(script)], check=True)
