from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from .config import AppConfig, write_json_safe, write_text_safe
from .logger import get_logger

GENERATED_DIRS = {"02_AUDIO_EXTRACTS", "03_TRANSCRIPTS", "04_ANALYSIS", "05_EDIT_DECISIONS", "06_FCPXML", "07_APPLESCRIPT", "08_EXPORTS", ".git", "__pycache__"}


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg/ffprobe not found. Install ffmpeg with: brew install ffmpeg") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{(exc.stderr or '')[-2000:]}") from exc


def _safe_output(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(path.read_bytes())
    return path


def _image_files(project_path: Path, config: AppConfig) -> list[Path]:
    exts = {e.lower() for e in getattr(config, "supported_image_extensions", [])}
    images: list[Path] = []
    for path in sorted(project_path.rglob("*"), key=lambda p: (p.stat().st_mtime if p.exists() else 0, p.name.lower())):
        if not path.is_file() or path.suffix.lower() not in exts or path.name.startswith("."):
            continue
        rel = path.relative_to(project_path)
        if any(part in GENERATED_DIRS or part.startswith(".") for part in rel.parts):
            continue
        images.append(path)
    return images


def _music_files(project_path: Path) -> list[Path]:
    audio_exts = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"}
    files: list[Path] = []
    for path in sorted(project_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in audio_exts:
            continue
        rel = path.relative_to(project_path)
        if any(part in GENERATED_DIRS or part.startswith(".") for part in rel.parts):
            continue
        marker = (path.name + " " + path.parent.name).lower()
        if any(token in marker for token in ["music", "song", "soundtrack", "score"]):
            files.append(path)
    return files


def _select_images(images: list[Path], max_count: int) -> list[Path]:
    if len(images) <= max_count:
        return images
    step = (len(images) - 1) / float(max_count - 1)
    return [images[round(i * step)] for i in range(max_count)]


def _filter_for(orientation: str) -> str:
    if orientation == "horizontal":
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    if orientation == "vertical":
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p"
    raise ValueError(f"Unsupported orientation: {orientation}")


def _concat(segment_paths: list[Path], concat_file: Path, output_path: Path) -> Path:
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segment_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_path)])
    return output_path


def _mix_music(base_video: Path, music: Path, output_path: Path) -> Path:
    _safe_output(output_path)
    _run([
        "ffmpeg", "-y", "-i", str(base_video), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", "[1:a]volume=0.22[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path)
    ])
    return output_path


def _render_orientation(project_path: Path, images: list[Path], orientation: str, output_path: Path, seconds_per_image: float) -> Path:
    tmp_dir = project_path / "08_EXPORTS" / ".photo_montage_tmp" / orientation
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    vf = _filter_for(orientation)
    for index, image in enumerate(images, start=1):
        segment = tmp_dir / f"photo_{index:04d}.mp4"
        _run([
            "ffmpeg", "-y", "-loop", "1", "-t", str(seconds_per_image), "-i", str(image),
            "-f", "lavfi", "-t", str(seconds_per_image), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf", vf, "-r", "30", "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(segment)
        ])
        segments.append(segment)
    concat_output = tmp_dir.parent / f"{orientation}_concat.mp4"
    _concat(segments, tmp_dir.parent / f"{orientation}_concat.txt", concat_output)
    music = _music_files(project_path)
    if music:
        _mix_music(concat_output, music[0], output_path)
    else:
        _safe_output(output_path)
        shutil.copy2(concat_output, output_path)
    return output_path


def render_photo_montage(project: str | Path, config: AppConfig) -> dict:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    images = _image_files(project_path, config)
    if not images:
        raise ValueError(f"No still images found in {project_path}")
    horizontal_images = _select_images(images, 60)
    vertical_images = _select_images(images, 30)
    outputs = {
        "horizontal": str(_render_orientation(project_path, horizontal_images, "horizontal", project_path / "08_EXPORTS" / f"{project_path.name}_photo_montage_horizontal_1920x1080.mp4", 2.5)),
        "vertical": str(_render_orientation(project_path, vertical_images, "vertical", project_path / "08_EXPORTS" / f"{project_path.name}_photo_montage_vertical_1080x1920.mp4", 2.0)),
    }
    summary = {
        "project_name": project_path.name,
        "mode": "photo_montage",
        "source_image_count": len(images),
        "horizontal_image_count": len(horizontal_images),
        "vertical_image_count": len(vertical_images),
        "outputs": outputs,
        "generated_at": datetime.now().isoformat(),
    }
    summary_path = project_path / "08_EXPORTS" / "photo_montage_summary.json"
    write_json_safe(summary_path, summary)
    report = [
        f"# {project_path.name} Photo Montage",
        "",
        f"Source images: {len(images)}",
        f"Horizontal selects: {len(horizontal_images)}",
        f"Vertical selects: {len(vertical_images)}",
        "",
        "## Outputs",
        f"- Horizontal: `{outputs['horizontal']}`",
        f"- Vertical: `{outputs['vertical']}`",
        "",
        "Selection is deterministic: images are sorted by file modified time/name and sampled evenly for a marketing-style recap.",
    ]
    write_text_safe(project_path / "04_ANALYSIS" / "photo_montage_report.md", "\n".join(report) + "\n")
    log.info("Rendered photo montage for %s from %d images", project_path, len(images))
    outputs["summary"] = str(summary_path)
    return outputs
