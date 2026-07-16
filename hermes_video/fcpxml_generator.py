from __future__ import annotations
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote
from .config import write_json_safe
from .models import EditDecisionList, FinalCutProject, TimelineVersion
from .store import ProjectStore

FPS_RATES = {
    23.976: Fraction(24000, 1001), 24.0: Fraction(24, 1), 25.0: Fraction(25, 1),
    29.97: Fraction(30000, 1001), 30.0: Fraction(30, 1), 50.0: Fraction(50, 1),
    59.94: Fraction(60000, 1001), 60.0: Fraction(60, 1),
}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"}

def rate_fraction(fps: float | None) -> Fraction:
    if not fps: return Fraction(30000, 1001)
    closest = min(FPS_RATES, key=lambda x: abs(x - fps))
    if abs(closest - fps) > 0.02: raise ValueError(f"Unsupported source FPS: {fps}")
    return FPS_RATES[closest]

def frame_duration(fps: float | None) -> str:
    rate = rate_fraction(fps); return f"{rate.denominator}/{rate.numerator}s"

def rational_seconds(value: float) -> str:
    f = Fraction(str(max(0.0, value))).limit_denominator(1_000_000)
    return f"{f.numerator}/{f.denominator}s" if f.denominator != 1 else f"{f.numerator}s"

def _file_url(path: str) -> str:
    return "file://" + quote(str(Path(path).resolve()))

def validate_fcpxml(path: Path, require_media: bool = True) -> None:
    root = ET.parse(path).getroot(); resources = root.find("resources")
    if resources is None: raise ValueError("FCPXML has no resources")
    ids = {x.get("id") for x in resources}
    for clip in root.findall(".//*[@ref]"):
        if clip.get("ref") not in ids: raise ValueError(f"Unknown resource reference {clip.get('ref')}")
        if float(Fraction(clip.get("duration", "0s")[:-1])) <= 0: raise ValueError("Clip duration must be positive")
    if require_media:
        for asset in resources.findall("asset"):
            src = asset.get("src", "").replace("file://", "")
            from urllib.parse import unquote
            if not Path(unquote(src)).exists(): raise FileNotFoundError(f"Missing media referenced by FCPXML: {unquote(src)}")

def _backup(out: Path) -> None:
    if out.exists():
        backup = out.with_suffix(out.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(out.read_bytes())

def export_timeline_fcpxml(project: str | Path, timeline_mode: str = "conservative", orientation: str = "horizontal") -> Path:
    project_path = Path(project).expanduser().resolve(); store = ProjectStore(project_path)
    rows = store.rows("timeline_version", "mode=?", (timeline_mode,))
    if not rows and timeline_mode == "approved":
        rows = store.rows("timeline_version", "status='approved'")
    if not rows: raise FileNotFoundError(f"No {timeline_mode} timeline. Run plan first.")
    timeline = TimelineVersion.model_validate(rows[-1]["payload"])
    assets = {r["id"]: r["payload"] for r in store.rows("media_asset")}
    active = [d for d in timeline.decisions if d.action in {"keep", "trim", "reorder", "short_candidate", "broll_placeholder"}]
    if not active: raise ValueError("Timeline has no active decisions")
    root = ET.Element("fcpxml", {"version": "1.10"}); resources = ET.SubElement(root, "resources")
    width, height = ((1080, 1920) if orientation == "vertical" else (1920, 1080))
    primary_fps = next((assets[d.media_asset_id].get("frame_rate") for d in active if d.media_asset_id in assets and assets[d.media_asset_id].get("frame_rate")), 29.97)
    ET.SubElement(resources, "format", {"id": "timeline_format", "name": f"Hermes{height}p", "frameDuration": frame_duration(primary_fps), "width": str(width), "height": str(height), "colorSpace": "1-1-1 (Rec. 709)"})
    refs = {}; index = 1
    for d in active:
        if d.action == "broll_placeholder" or not d.media_asset_id: continue
        if d.media_asset_id in refs: continue
        if d.media_asset_id not in assets: raise ValueError(f"Decision references unknown media asset {d.media_asset_id}")
        asset = assets[d.media_asset_id]; source = Path(asset["source_path"])
        if not source.exists(): raise FileNotFoundError(f"Missing media: {source}")
        fmt_ref = ""
        if asset["media_type"] == "video":
            fmt_ref = f"source_format_{index}"
            ET.SubElement(resources, "format", {"id": fmt_ref, "name": f"SourceFormat{index}", "frameDuration": frame_duration(asset.get("frame_rate")), "width": str(asset.get("width") or width), "height": str(asset.get("height") or height), "colorSpace": "1-1-1 (Rec. 709)"})
        ref = f"asset_{index}"; index += 1; refs[d.media_asset_id] = ref
        attrs = {"id": ref, "name": source.name, "src": _file_url(str(source)), "start": "0s", "duration": rational_seconds(float(asset.get("duration_seconds") or d.out_seconds)), "hasAudio": "1" if asset.get("has_audio") else "0"}
        if asset["media_type"] == "video": attrs.update({"hasVideo": "1", "format": fmt_ref})
        ET.SubElement(resources, "asset", attrs)
    library = ET.SubElement(root, "library"); event = ET.SubElement(library, "event", {"name": project_path.name})
    project_el = ET.SubElement(event, "project", {"name": f"{project_path.name} {timeline_mode.title()} Assistant Rough Cut"})
    total = sum(d.out_seconds - d.in_seconds for d in active)
    sequence = ET.SubElement(project_el, "sequence", {"format": "timeline_format", "duration": rational_seconds(total), "tcStart": "0s", "tcFormat": "NDF", "audioLayout": "stereo", "audioRate": "48k"})
    spine = ET.SubElement(sequence, "spine"); offset = 0.0
    for d in active:
        duration = d.out_seconds - d.in_seconds
        if d.action == "broll_placeholder":
            gap = ET.SubElement(spine, "gap", {"name": "B-roll placeholder", "offset": rational_seconds(offset), "start": "0s", "duration": rational_seconds(duration)})
            ET.SubElement(gap, "marker", {"start": "0s", "duration": frame_duration(primary_fps), "value": d.reason}); offset += duration; continue
        asset = assets[d.media_asset_id]; tag = "asset-clip"
        attrs = {"name": Path(d.source_path).name or d.editorial_unit_id, "ref": refs[d.media_asset_id], "offset": rational_seconds(offset), "start": rational_seconds(d.in_seconds), "duration": rational_seconds(duration), "role": "dialogue" if asset.get("has_audio") else "video"}
        clip = ET.SubElement(spine, tag, attrs)
        ET.SubElement(clip, "marker", {"start": "0s", "duration": frame_duration(primary_fps), "value": f"{d.action}: {d.reason}"})
        offset += duration
    ET.indent(root, space="  "); out = project_path / "06_FCPXML" / f"{project_path.name}_{timeline_mode}_{orientation}.fcpxml"
    out.parent.mkdir(parents=True, exist_ok=True); _backup(out); ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True); validate_fcpxml(out)
    write_json_safe(project_path / "06_FCPXML" / "final_cut_project.json", {"project_name": project_path.name, "timeline_name": timeline.id, "fcpxml_path": str(out), "edit_decision_list_path": str(project_path / "05_EDIT_DECISIONS" / f"timeline_{timeline_mode}.json")})
    return out

def build_fcpxml(project: str | Path, edl_path: str | Path | None = None) -> tuple[Path, Path]:
    """Deprecated V1 adapter; V2 timelines are preferred."""
    project_path = Path(project).expanduser().resolve()
    try:
        out = export_timeline_fcpxml(project_path, "conservative")
        return out, project_path / "06_FCPXML" / "final_cut_project.json"
    except FileNotFoundError:
        if edl_path is None:
            candidates = sorted((project_path / "05_EDIT_DECISIONS").glob("edit_decision_list_*.json"))
            if not candidates: raise
            edl_path = candidates[-1]
        edl = EditDecisionList.model_validate_json(Path(edl_path).read_text())
        # Convert old EDL to a temporary V2 timeline without changing raw media.
        store = ProjectStore(project_path); pid = hashlib.sha1(str(project_path).encode()).hexdigest()[:16]
        decisions = [dict(id=f"legacy_{i}", editorial_unit_id=d.id, action="keep", reason=d.reason, source_path=d.source_path, media_asset_id=d.media_asset_id, in_seconds=d.in_seconds, out_seconds=d.out_seconds, timeline_position_seconds=d.timeline_position_seconds) for i, d in enumerate(edl.decisions)]
        timeline = TimelineVersion.model_validate({"id": f"{pid}_conservative", "project_id": pid, "mode": "conservative", "decisions": decisions})
        store.upsert("timeline_version", {"id": timeline.id, "project_id": pid, "mode": "conservative", "status": "draft", "payload": timeline.model_dump()})
        out = export_timeline_fcpxml(project_path, "conservative")
        return out, project_path / "06_FCPXML" / "final_cut_project.json"
