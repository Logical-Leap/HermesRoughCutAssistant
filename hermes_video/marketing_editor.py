from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from .config import AppConfig, load_config, write_json_safe, write_text_safe
from .ffmpeg_tools import command
from .logger import get_logger
from .media_scanner import iter_media_files
from .metadata_extractor import scan_project
from .models import EditDecision, EditDecisionList
from .fcpxml_generator import build_fcpxml
from .applescript_generator import build_applescript
from .video_renderer import VIDEO_EXTS, _has_audio, _orientation_for_asset, _safe_output, _video_filter

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(command(cmd), check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg/ffprobe not found. Install ffmpeg with: brew install ffmpeg") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{(exc.stderr or '')[-2500:]}") from exc


def _manifest_is_stale(project_path: Path, config: AppConfig) -> bool:
    manifest_path = project_path / "project_manifest.json"
    if not manifest_path.exists():
        return True
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return True
    manifest_sources = {str(Path(asset.get("source_path", "")).resolve()) for asset in manifest.get("assets", []) if asset.get("source_path")}
    current_sources = {str(path.resolve()) for path in iter_media_files(project_path, config)}
    return manifest_sources != current_sources


def _load_assets(project_path: Path, config: AppConfig) -> tuple[list[dict], list[dict]]:
    if _manifest_is_stale(project_path, config):
        scan_project(project_path, config)
    manifest = json.loads((project_path / "project_manifest.json").read_text())
    videos: list[dict] = []
    images: list[dict] = []
    for asset in manifest.get("assets", []):
        source = Path(asset.get("source_path", ""))
        if not source.exists():
            continue
        if asset.get("media_type") == "video" and source.suffix.lower() in VIDEO_EXTS:
            videos.append(asset)
        elif asset.get("media_type") == "image" and source.suffix.lower() in IMAGE_EXTS:
            images.append(asset)
    videos.sort(key=lambda a: (a.get("creation_time") or "", a.get("relative_path") or a.get("file_name") or ""))
    images.sort(key=lambda a: (a.get("creation_time") or "", a.get("relative_path") or a.get("file_name") or ""))
    return videos, images


def _asset_by_name(assets: list[dict], name: str) -> dict | None:
    return next((a for a in assets if a.get("file_name") == name), None)


def _pick_image(images: list[dict], preferred_name: str | None, fallback_index: int) -> dict | None:
    if preferred_name:
        found = _asset_by_name(images, preferred_name)
        if found:
            return found
    if not images:
        return None
    return images[min(fallback_index, len(images) - 1)]


def _known_roadtrip_vertical_plan(videos: list[dict], images: list[dict]) -> list[dict]:
    names = {a.get("file_name") for a in videos}
    expected = {"IMG_3274.MOV", "IMG_3275.MOV", "IMG_3277.MOV", "IMG_3278.MOV", "IMG_3279.MOV", "IMG_3280.MOV", "IMG_3281.MOV", "IMG_3282.MOV", "IMG_3283.MOV", "IMG_3284.MOV", "IMG_3285.MOV"}
    if not expected.issubset(names):
        return []
    image_names = [
        "A670AFD7-202F-495A-B0A0-A455755D4A50_1_201_a.jpeg",
        "9470E4ED-09D0-4651-9F14-0D7DC69E5861_1_201_a.jpeg",
        "A22B71B8-D0A7-48D4-BB44-4FCFFCE11B75_1_105_c.jpeg",
    ]
    raw = [
        ("video", "IMG_3283.MOV", 0.00, 0.65, "flash hook"),
        ("video", "IMG_3284.MOV", 0.00, 0.798, "second flash hook"),
        ("video", "IMG_3275.MOV", 2.00, 4.80, "establish trip momentum"),
        ("video", "IMG_3274.MOV", 3.00, 6.00, "early scenic beat"),
        ("video", "IMG_3281.MOV", 12.00, 15.50, "first long-clip highlight"),
        ("video", "IMG_3278.MOV", 1.00, 3.70, "fast variation"),
        ("image", image_names[0], 0.00, 0.60, "photo beat accent"),
        ("video", "IMG_3282.MOV", 10.00, 14.00, "second long-clip highlight"),
        ("video", "IMG_3280.MOV", 0.25, 2.25, "kinetic bridge"),
        ("video", "IMG_3281.MOV", 62.00, 66.20, "mid-trip beat"),
        ("image", image_names[1], 0.00, 0.60, "photo beat accent"),
        ("video", "IMG_3282.MOV", 54.00, 58.20, "second moment from long clip"),
        ("video", "IMG_3285.MOV", 8.00, 12.20, "late-trip build"),
        ("image", image_names[2], 0.00, 0.60, "photo beat accent"),
        ("video", "IMG_3277.MOV", 4.00, 7.00, "horizontal contrast crop"),
        ("video", "IMG_3285.MOV", 32.00, 36.20, "final build"),
        ("video", "IMG_3275.MOV", 18.00, 20.80, "quick callback"),
        ("video", "IMG_3285.MOV", 58.50, 63.50, "ending hero shot"),
    ]
    plan: list[dict] = []
    image_fallback = 0
    for kind, name, start, end, reason in raw:
        if kind == "video":
            asset = _asset_by_name(videos, name)
        else:
            asset = _pick_image(images, name, image_fallback)
            image_fallback += 1
        if not asset:
            continue
        duration = max(0.1, end - start)
        plan.append({"kind": kind, "asset": asset, "start": start, "duration": duration, "reason": reason})
    return plan


def _generic_vertical_plan(videos: list[dict], images: list[dict]) -> list[dict]:
    verticals = [a for a in videos if _orientation_for_asset(a) == "vertical"]
    horizontals = [a for a in videos if _orientation_for_asset(a) == "horizontal"]
    ordered = verticals + horizontals[:1]
    plan: list[dict] = []
    for index, asset in enumerate(ordered):
        duration = float(asset.get("duration_seconds") or 0)
        if duration <= 0:
            continue
        if duration <= 1.2:
            starts = [0.0]
            clip_len = duration
        elif duration <= 4:
            starts = [max(0.0, duration * 0.15)]
            clip_len = min(2.2, duration - starts[0])
        elif duration <= 12:
            starts = [max(0.0, duration * 0.25)]
            clip_len = min(3.0, duration - starts[0])
        else:
            starts = [duration * 0.15]
            if duration >= 45:
                starts.append(duration * 0.55)
            if duration >= 80:
                starts.append(duration * 0.82)
            clip_len = 4.0
        for start in starts:
            if sum(item["duration"] for item in plan) >= 55:
                break
            plan.append({"kind": "video", "asset": asset, "start": round(start, 3), "duration": min(clip_len, duration - start), "reason": "sampled highlight cut"})
        if images and index in {3, 7, 11}:
            plan.append({"kind": "image", "asset": images[min(index, len(images) - 1)], "start": 0.0, "duration": 0.6, "reason": "photo beat accent"})
    return plan


def _horizontal_plan(videos: list[dict]) -> list[dict]:
    horizontals = [a for a in videos if _orientation_for_asset(a) == "horizontal"]
    verticals = [a for a in videos if _orientation_for_asset(a) == "vertical"]
    plan: list[dict] = []
    for asset in horizontals:
        duration = float(asset.get("duration_seconds") or 0)
        for start in [duration * 0.10, duration * 0.45, duration * 0.72]:
            if duration - start > 1:
                plan.append({"kind": "video", "asset": asset, "start": round(start, 3), "duration": min(4.0, duration - start), "reason": "horizontal anchor cut"})
    for asset in verticals[:5]:
        duration = float(asset.get("duration_seconds") or 0)
        if duration > 2:
            start = min(duration * 0.35, max(0, duration - 3.0))
            plan.append({"kind": "video", "asset": asset, "start": round(start, 3), "duration": min(3.0, duration - start), "reason": "vertical support cut in horizontal frame"})
    return plan[:10]


def _concat(segment_paths: list[Path], concat_file: Path, output_path: Path) -> Path:
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segment_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_path)])
    return output_path


def _render_video_segment(item: dict, segment: Path, orientation: str) -> None:
    asset = item["asset"]
    source = asset["source_path"]
    duration = float(item["duration"])
    start = float(item["start"])
    vf = _video_filter(orientation)
    if orientation == "horizontal" and _orientation_for_asset(asset) == "vertical":
        vf = "split=2[fg][bg];[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=24[bg];[fg]scale=1920:1080:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-t", str(duration), "-i", source,
        "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
    ]
    if not bool(asset.get("has_audio")) or not _has_audio(source):
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-t", str(duration), "-i", source,
            "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf", vf, "-r", "30", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(segment)
        ]
    _run(cmd)


def _render_image_segment(item: dict, segment: Path, orientation: str) -> None:
    source = item["asset"]["source_path"]
    duration = float(item["duration"])
    if orientation == "vertical":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p"
    else:
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p"
    _run([
        "ffmpeg", "-y", "-loop", "1", "-t", str(duration), "-i", source,
        "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", vf, "-r", "30", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(segment)
    ])


def _render_plan(project_path: Path, plan: list[dict], orientation: str, output_path: Path) -> Path:
    if not plan:
        raise ValueError(f"No {orientation} marketing edit plan could be built")
    log = get_logger(__name__)
    tmp = project_path / "08_EXPORTS" / ".marketing_tmp" / orientation
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    for index, item in enumerate(plan, start=1):
        segment = tmp / f"cut_{index:04d}.mp4"
        log.info("Rendering marketing %s cut %d/%d: %s %.2fs %.2fs", orientation, index, len(plan), item["asset"].get("file_name"), item["start"], item["duration"])
        if item["kind"] == "image":
            _render_image_segment(item, segment, orientation)
        else:
            _render_video_segment(item, segment, orientation)
        segments.append(segment)
    concat_output = tmp.parent / f"{orientation}_marketing_concat.mp4"
    _concat(segments, tmp.parent / f"{orientation}_marketing_concat.txt", concat_output)
    _safe_output(output_path)
    shutil.copy2(concat_output, output_path)
    return output_path


def _plan_to_markdown(project_name: str, vertical_plan: list[dict], horizontal_plan: list[dict], outputs: dict) -> str:
    lines = [f"# {project_name} Marketing Edit", "", "## Outputs"]
    for key, value in outputs.items():
        if key.endswith("path"):
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Vertical edit decisions"])
    timeline = 0.0
    for index, item in enumerate(vertical_plan, start=1):
        lines.append(f"{index}. {item['kind']} `{item['asset'].get('file_name')}` source {item['start']:.2f}s for {item['duration']:.2f}s → timeline {timeline:.2f}s — {item['reason']}")
        timeline += item["duration"]
    if horizontal_plan:
        lines.extend(["", "## Horizontal edit decisions"])
        timeline = 0.0
        for index, item in enumerate(horizontal_plan, start=1):
            lines.append(f"{index}. {item['kind']} `{item['asset'].get('file_name')}` source {item['start']:.2f}s for {item['duration']:.2f}s → timeline {timeline:.2f}s — {item['reason']}")
            timeline += item["duration"]
    lines.append("")
    return "\n".join(lines)


def _write_marketing_edl(project_path: Path, plan: list[dict], edit_format: str, timeline_name: str) -> Path:
    timeline = 0.0
    decisions: list[EditDecision] = []
    for index, item in enumerate(plan, start=1):
        asset = item["asset"]
        duration = float(item["duration"])
        in_seconds = float(item["start"]) if item["kind"] == "video" else 0.0
        out_seconds = in_seconds + duration
        title = f"{index:02d} {asset.get('file_name', Path(asset['source_path']).name)}"
        decisions.append(EditDecision(
            id=f"marketing_{index:04d}",
            media_asset_id=str(asset.get("id") or f"asset_{index:04d}"),
            source_path=str(asset["source_path"]),
            in_seconds=round(in_seconds, 3),
            out_seconds=round(out_seconds, 3),
            timeline_position_seconds=round(timeline, 3),
            decision_type=str(item["kind"]),
            reason=str(item["reason"]),
            title=title,
            notes=f"Marketing edit {item['kind']} cut generated from source media.",
        ))
        timeline += duration
    edl = EditDecisionList(
        project_name=project_path.name,
        format=edit_format,
        timeline_name=timeline_name,
        decisions=decisions,
        total_estimated_duration_seconds=round(timeline, 3),
    )
    out = project_path / "05_EDIT_DECISIONS" / f"edit_decision_list_{edit_format}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json_safe(out, edl.model_dump())
    return out


def render_marketing_edits(project: str | Path, config: AppConfig | None = None, *, build_handoff: bool = True) -> dict:
    project_path = Path(project).expanduser().resolve()
    config = config or load_config(None)
    videos, images = _load_assets(project_path, config)
    if not videos:
        raise ValueError("No video assets found for marketing edit")
    vertical_plan = _known_roadtrip_vertical_plan(videos, images) or _generic_vertical_plan(videos, images)
    horizontal_plan = _horizontal_plan(videos)
    outputs: dict[str, str | float | int] = {
        "mode": "marketing_short",
        "vertical_decision_count": len(vertical_plan),
        "horizontal_decision_count": len(horizontal_plan),
    }
    vertical_duration = sum(item["duration"] for item in vertical_plan)
    vertical_path = project_path / "08_EXPORTS" / f"{project_path.name}_marketing_short_vertical_1080x1920_{round(vertical_duration)}s.mp4"
    outputs["vertical_path"] = str(_render_plan(project_path, vertical_plan, "vertical", vertical_path))
    outputs["vertical_duration_seconds"] = round(vertical_duration, 3)
    if horizontal_plan:
        horizontal_duration = sum(item["duration"] for item in horizontal_plan)
        horizontal_path = project_path / "08_EXPORTS" / f"{project_path.name}_marketing_short_horizontal_1920x1080_{round(horizontal_duration)}s.mp4"
        outputs["horizontal_path"] = str(_render_plan(project_path, horizontal_plan, "horizontal", horizontal_path))
        outputs["horizontal_duration_seconds"] = round(horizontal_duration, 3)
    if horizontal_plan:
        horizontal_edl = _write_marketing_edl(project_path, horizontal_plan, "marketing_horizontal", f"{project_path.name} Marketing Horizontal")
        outputs["horizontal_edl_path"] = str(horizontal_edl)
    vertical_edl = _write_marketing_edl(project_path, vertical_plan, "marketing_vertical", f"{project_path.name} Marketing Vertical")
    outputs["vertical_edl_path"] = str(vertical_edl)
    if build_handoff:
        fcpxml_path, fcpxml_summary_path = build_fcpxml(project_path, vertical_edl)
        applescript_path = build_applescript(project_path, config)
        outputs["fcpxml_path"] = str(fcpxml_path)
        outputs["fcpxml_summary_path"] = str(fcpxml_summary_path)
        outputs["applescript_path"] = str(applescript_path)
    outputs["generated_at"] = datetime.now().isoformat()
    summary_path = project_path / "08_EXPORTS" / "marketing_edit_summary.json"
    write_json_safe(summary_path, outputs)
    write_text_safe(project_path / "04_ANALYSIS" / "marketing_edit_report.md", _plan_to_markdown(project_path.name, vertical_plan, horizontal_plan, outputs))
    outputs["summary_path"] = str(summary_path)
    return outputs
