from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Any
from .ffmpeg_tools import command

SILENCE_START = re.compile(r"silence_start: ([0-9.]+)")
SILENCE_END = re.compile(r"silence_end: ([0-9.]+)")
SCENE = re.compile(r"pts_time:([0-9.]+)")

def analyze_audio(path: Path, duration: float) -> list[dict[str, Any]]:
    """Deterministic FFmpeg silence/loudness/clipping analysis; failures are surfaced."""
    proc = subprocess.run(command(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=n=-38dB:d=0.35,astats=metadata=1:reset=1", "-f", "null", "-"]), capture_output=True, text=True)
    if proc.returncode: raise RuntimeError(f"FFmpeg audio analysis failed for {path}: {proc.stderr[-1000:]}")
    starts = [float(x) for x in SILENCE_START.findall(proc.stderr)]; ends = [float(x) for x in SILENCE_END.findall(proc.stderr)]
    regions, cursor = [], 0.0
    for i, start in enumerate(starts):
        if start > cursor: regions.append({"start_seconds": cursor, "end_seconds": start, "kind": "speech"})
        end = ends[i] if i < len(ends) else duration
        regions.append({"start_seconds": start, "end_seconds": min(end, duration), "kind": "silence"}); cursor = end
    if cursor < duration: regions.append({"start_seconds": cursor, "end_seconds": duration, "kind": "speech"})
    if "Peak level dB: 0.000000" in proc.stderr or "Peak level dB: -0.0" in proc.stderr:
        regions.append({"start_seconds": 0, "end_seconds": duration, "kind": "clipping"})
    return regions or [{"start_seconds": 0, "end_seconds": duration, "kind": "unknown"}]

def analyze_scenes(path: Path, duration: float, threshold: float = 0.35) -> list[dict[str, float]]:
    proc = subprocess.run(command(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"]), capture_output=True, text=True)
    if proc.returncode: raise RuntimeError(f"FFmpeg scene analysis failed for {path}: {proc.stderr[-1000:]}")
    cuts = [0.0] + [float(x) for x in SCENE.findall(proc.stderr)] + [duration]
    cuts = sorted(set(max(0, min(duration, x)) for x in cuts))
    return [{"start_seconds": cuts[i], "end_seconds": cuts[i+1]} for i in range(len(cuts)-1) if cuts[i+1] > cuts[i]]
