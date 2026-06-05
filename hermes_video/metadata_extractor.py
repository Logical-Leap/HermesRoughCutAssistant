from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from .config import AppConfig, write_json_safe
from .logger import get_logger
from .media_scanner import iter_media_files, classify_media
from .models import MediaAsset


def _run_ffprobe(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return json.loads(result.stdout or "{}")
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe not found. Install ffmpeg with: brew install ffmpeg") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed for {path}: {exc.stderr.strip()}") from exc


def _checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _frame_rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            denom = float(b)
            return round(float(a) / denom, 3) if denom else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def _rotation_degrees(stream: dict) -> int:
    tags = stream.get("tags") or {}
    if tags.get("rotate") is not None:
        try:
            return int(float(tags["rotate"])) % 360
        except (TypeError, ValueError):
            return 0
    for item in stream.get("side_data_list") or []:
        if item.get("rotation") is not None:
            try:
                return int(float(item["rotation"])) % 360
            except (TypeError, ValueError):
                return 0
    return 0


def extract_asset(project_path: Path, media_path: Path, config: AppConfig) -> MediaAsset:
    probe = _run_ffprobe(media_path)
    streams = probe.get("streams", [])
    fmt = probe.get("format", {})
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    duration = float(fmt.get("duration") or video.get("duration") or (audio_streams[0].get("duration") if audio_streams else 0) or 0)
    rel = media_path.relative_to(project_path)
    try:
        raw_rel = media_path.relative_to(project_path / "01_RAW")
    except ValueError:
        raw_rel = media_path.relative_to(project_path)
    camera_group = raw_rel.parts[0] if len(raw_rel.parts) > 1 else None
    asset_id = hashlib.sha1(str(rel).encode("utf-8")).hexdigest()[:12]
    tags = fmt.get("tags", {}) or video.get("tags", {})
    audio_codec = audio_streams[0].get("codec_name") if audio_streams else None
    return MediaAsset(
        id=asset_id,
        source_path=str(media_path.resolve()),
        relative_path=str(rel),
        file_name=media_path.name,
        file_extension=media_path.suffix.lower(),
        media_type=classify_media(media_path, config),
        duration_seconds=round(duration, 3),
        frame_rate=_frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        width=video.get("width"),
        height=video.get("height"),
        rotation_degrees=_rotation_degrees(video),
        video_codec=video.get("codec_name"),
        audio_codec=audio_codec,
        audio_stream_count=len(audio_streams),
        has_audio=bool(audio_streams),
        creation_time=tags.get("creation_time"),
        camera_group=camera_group,
        checksum=_checksum(media_path),
    )


def scan_project(project: str | Path, config: AppConfig) -> Path:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    assets = []
    for media_path in iter_media_files(project_path, config) or []:
        log.info("Scanning media: %s", media_path)
        assets.append(extract_asset(project_path, media_path, config))
    manifest = {
        "project_name": project_path.name,
        "project_path": str(project_path),
        "asset_count": len(assets),
        "assets": [a.model_dump() for a in assets],
    }
    out = write_json_safe(project_path / "project_manifest.json", manifest)
    log.info("Wrote manifest with %d assets to %s", len(assets), out)
    return out


def load_manifest(project_path: Path) -> dict:
    path = project_path / "project_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run scan first.")
    return json.loads(path.read_text())
