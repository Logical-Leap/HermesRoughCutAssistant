from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from .config import write_json_safe
from .ffmpeg_tools import command
from .logger import get_logger
from .models import EditDecisionList

VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".mxf"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"}
GENERATED_DIRS = {"02_AUDIO_EXTRACTS", "03_TRANSCRIPTS", "04_ANALYSIS", "05_EDIT_DECISIONS", "06_FCPXML", "07_APPLESCRIPT", "08_EXPORTS", ".git", "__pycache__"}


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(command(cmd), check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg/ffprobe not found. Install ffmpeg with: brew install ffmpeg") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "")[-2000:]
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr}") from exc


def _latest_edl(project_path: Path) -> Path:
    candidates = sorted((project_path / "05_EDIT_DECISIONS").glob("edit_decision_list_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No edit decision list found. Run build-edit first.")
    return candidates[0]


def _safe_output(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(path.read_bytes())
    return path


def _video_filter(orientation: str) -> str:
    if orientation == "horizontal":
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1"
    if orientation == "vertical":
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    raise ValueError(f"Unsupported orientation: {orientation}")


def _orientation_for_asset(asset: dict) -> str:
    width = int(asset.get("width") or 0)
    height = int(asset.get("height") or 0)
    rotation = int(asset.get("rotation_degrees") or 0) % 180
    if rotation == 90:
        width, height = height, width
    return "vertical" if height > width else "horizontal"


def _manifest_video_assets(project_path: Path) -> list[dict]:
    manifest_path = project_path / "project_manifest.json"
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text())
    videos = []
    for asset in data.get("assets", []):
        source = Path(asset.get("source_path", ""))
        if asset.get("media_type") == "video" and source.suffix.lower() in VIDEO_EXTS and source.exists():
            videos.append(asset)
    return sorted(videos, key=lambda a: (a.get("creation_time") or "", a.get("relative_path") or a.get("file_name") or ""))


def _has_audio(path: str) -> bool:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path]
    try:
        result = subprocess.run(command(cmd), check=True, capture_output=True, text=True)
        return bool(result.stdout.strip())
    except Exception:
        return False


def _music_files(project_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(project_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
            continue
        rel_parts = set(path.relative_to(project_path).parts)
        if rel_parts & GENERATED_DIRS:
            continue
        name = path.name.lower()
        parent = path.parent.name.lower()
        if "music" in name or "song" in name or "soundtrack" in name or parent in {"music", "soundtrack"}:
            files.append(path)
    return files


def _concat_segments(segment_paths: list[Path], concat_file: Path, output_path: Path) -> Path:
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segment_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_path)])
    return output_path


def _mix_music(base_video: Path, music: Path, output_path: Path) -> Path:
    _safe_output(output_path)
    _run([
        "ffmpeg", "-y", "-i", str(base_video), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", "[1:a]volume=0.18[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path)
    ])
    return output_path


def _render_video_assets(project_path: Path, assets: list[dict], orientation: str, final_output: Path, tmp_root: Path) -> Path:
    log = get_logger(__name__)
    seg_dir = tmp_root / orientation
    seg_dir.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []
    vf = _video_filter(orientation)
    for index, asset in enumerate(assets, start=1):
        source_path = asset["source_path"]
        duration = float(asset.get("duration_seconds") or 0)
        if duration <= 0:
            continue
        segment = seg_dir / f"segment_{index:04d}.mp4"
        log.info("Rendering %s source clip %d/%d: %s", orientation, index, len(assets), source_path)
        cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
        ]
        if not bool(asset.get("has_audio")) or not _has_audio(source_path):
            cmd = [
                "ffmpeg", "-y", "-i", source_path,
                "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-vf", vf, "-r", "30", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
            ]
        _run(cmd)
        segment_paths.append(segment)
    if not segment_paths:
        raise ValueError(f"No renderable {orientation} source video segments found")
    concat_output = tmp_root / f"{orientation}_concat.mp4"
    _concat_segments(segment_paths, tmp_root / f"{orientation}_concat.txt", concat_output)
    music = _music_files(project_path)
    music_path = music[0] if music else None
    _safe_output(final_output)
    if music_path:
        _mix_music(concat_output, music_path, final_output)
    else:
        shutil.copy2(concat_output, final_output)
    return final_output


def render_comprehensive_orientation_edits(project: str | Path, *, render_horizontal: bool = True, render_vertical: bool = True) -> dict:
    project_path = Path(project).expanduser().resolve()
    videos = _manifest_video_assets(project_path)
    if not videos:
        raise ValueError("No source video assets found in project manifest")
    grouped = {"horizontal": [], "vertical": []}
    for asset in videos:
        grouped[_orientation_for_asset(asset)].append(asset)
    tmp_root = project_path / "08_EXPORTS" / ".render_tmp"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str | int | None] = {
        "mode": "comprehensive_orientation_video",
        "horizontal_source_clip_count": len(grouped["horizontal"]),
        "vertical_source_clip_count": len(grouped["vertical"]),
    }
    if render_horizontal and grouped["horizontal"]:
        outputs["horizontal"] = str(_render_video_assets(project_path, grouped["horizontal"], "horizontal", project_path / "08_EXPORTS" / f"{project_path.name}_horizontal_1920x1080.mp4", tmp_root))
    if render_vertical and grouped["vertical"]:
        outputs["vertical"] = str(_render_video_assets(project_path, grouped["vertical"], "vertical", project_path / "08_EXPORTS" / f"{project_path.name}_vertical_1080x1920.mp4", tmp_root))
    summary = {
        "project_name": project_path.name,
        "outputs": outputs,
        "generated_at": datetime.now().isoformat(),
    }
    summary_path = project_path / "08_EXPORTS" / "render_summary.json"
    write_json_safe(summary_path, summary)
    outputs["summary"] = str(summary_path)
    return outputs


def render_project(project: str | Path, edl_path: str | Path | None = None, *, render_horizontal: bool = True, render_vertical: bool = True) -> dict:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    if edl_path is None and (project_path / "project_manifest.json").exists():
        videos = _manifest_video_assets(project_path)
        if videos:
            return render_comprehensive_orientation_edits(project_path, render_horizontal=render_horizontal, render_vertical=render_vertical)
    edl_file = Path(edl_path) if edl_path else _latest_edl(project_path)
    edl = EditDecisionList.model_validate_json(edl_file.read_text())
    video_decisions = [d for d in edl.decisions if Path(d.source_path).suffix.lower() in VIDEO_EXTS]
    if not video_decisions:
        raise ValueError("No video edit decisions found; cannot render final videos.")

    tmp_root = project_path / "08_EXPORTS" / ".render_tmp"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    orientations = []
    if render_horizontal:
        orientations.append(("horizontal", project_path / "08_EXPORTS" / f"{project_path.name}_horizontal_1920x1080.mp4"))
    if render_vertical:
        orientations.append(("vertical", project_path / "08_EXPORTS" / f"{project_path.name}_vertical_1080x1920.mp4"))

    music = _music_files(project_path)
    music_path = music[0] if music else None
    for orientation, final_output in orientations:
        log.info("Rendering %s final video", orientation)
        seg_dir = tmp_root / orientation
        seg_dir.mkdir(parents=True, exist_ok=True)
        segment_paths: list[Path] = []
        vf = _video_filter(orientation)
        for index, decision in enumerate(video_decisions, start=1):
            segment = seg_dir / f"segment_{index:04d}.mp4"
            duration = max(0.001, decision.out_seconds - decision.in_seconds)
            cmd = [
                "ffmpeg", "-y", "-ss", str(decision.in_seconds), "-t", str(duration), "-i", decision.source_path,
                "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
            ]
            if not _has_audio(decision.source_path):
                cmd = [
                    "ffmpeg", "-y", "-ss", str(decision.in_seconds), "-t", str(duration), "-i", decision.source_path,
                    "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-vf", vf, "-r", "30", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
                ]
            _run(cmd)
            segment_paths.append(segment)
        concat_output = tmp_root / f"{orientation}_concat.mp4"
        _concat_segments(segment_paths, tmp_root / f"{orientation}_concat.txt", concat_output)
        _safe_output(final_output)
        if music_path:
            _mix_music(concat_output, music_path, final_output)
            outputs[f"{orientation}_music"] = str(music_path)
        else:
            shutil.copy2(concat_output, final_output)
        outputs[orientation] = str(final_output)
        log.info("Rendered %s", final_output)

    summary = {
        "project_name": project_path.name,
        "edit_decision_list_path": str(edl_file),
        "outputs": outputs,
        "music_used": str(music_path) if music_path else None,
        "generated_at": datetime.now().isoformat(),
    }
    summary_path = project_path / "08_EXPORTS" / "render_summary.json"
    write_json_safe(summary_path, summary)
    outputs["summary"] = str(summary_path)
    return outputs
