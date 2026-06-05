from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

COMMON_BIN_DIRS = (Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin"), Path("/bin"))


def resolve_binary(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for directory in COMMON_BIN_DIRS:
        candidate = directory / name
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(name)


def command(args: list[str]) -> list[str]:
    if args and args[0] in {"ffmpeg", "ffprobe"}:
        return [resolve_binary(args[0]), *args[1:]]
    return args


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command(args), check=True, capture_output=True, text=True)
