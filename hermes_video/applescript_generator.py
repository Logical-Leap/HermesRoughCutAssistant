from __future__ import annotations

import subprocess
from pathlib import Path
from .config import AppConfig, write_text_safe
from .logger import get_logger


def latest_fcpxml(project_path: Path) -> Path:
    candidates = sorted((project_path / "06_FCPXML").glob("*.fcpxml"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No FCPXML found. Run build-fcpxml first.")
    return candidates[0]


def build_applescript(project: str | Path, config: AppConfig) -> Path:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    fcpxml = latest_fcpxml(project_path)
    script = f'tell application "{config.final_cut_pro_app_name}"\nactivate\nopen POSIX file "{fcpxml}"\nend tell\n'
    out = project_path / "07_APPLESCRIPT" / "import_to_final_cut.applescript"
    write_text_safe(out, script)
    log.info("Generated AppleScript: %s", out)
    return out


def open_in_fcp(project: str | Path, config: AppConfig) -> None:
    project_path = Path(project).expanduser().resolve()
    script = project_path / "07_APPLESCRIPT" / "import_to_final_cut.applescript"
    if not script.exists():
        script = build_applescript(project_path, config)
    subprocess.run(["osascript", str(script)], check=True)
