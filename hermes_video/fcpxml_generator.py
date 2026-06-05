from __future__ import annotations

from datetime import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from .config import write_json_safe
from .logger import get_logger
from .models import EditDecisionList, FinalCutProject


def _sec(value: float) -> str:
    ticks = int(round(max(0, value) * 1000))
    return f"{ticks}/1000s"


def _file_url(path: str) -> str:
    return "file://" + quote(str(Path(path).resolve()))


def _validate_xml(path: Path) -> None:
    ET.parse(path)


def build_fcpxml(project: str | Path, edl_path: str | Path | None = None) -> tuple[Path, Path]:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    if edl_path is None:
        candidates = sorted((project_path / "05_EDIT_DECISIONS").glob("edit_decision_list_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("No edit decision list found. Run build-edit first.")
        edl_path = candidates[0]
    edl_path = Path(edl_path)
    edl = EditDecisionList.model_validate_json(edl_path.read_text())
    if not edl.decisions:
        raise ValueError("Edit decision list has no decisions; cannot build FCPXML.")

    fcpxml = ET.Element("fcpxml", {"version": "1.10"})
    resources = ET.SubElement(fcpxml, "resources")
    ET.SubElement(resources, "format", {"id": "r1", "name": "FFVideoFormat1080p30", "frameDuration": "100/3000s", "width": "1920", "height": "1080", "colorSpace": "1-1-1 (Rec. 709)"})
    asset_refs = {}
    resource_index = 2
    for decision in edl.decisions:
        if decision.media_asset_id in asset_refs:
            continue
        ref = f"r{resource_index}"
        resource_index += 1
        asset_refs[decision.media_asset_id] = ref
        audio_exts = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac"}
        has_video = "0" if Path(decision.source_path).suffix.lower() in audio_exts else "1"
        attrs = {"id": ref, "name": Path(decision.source_path).name, "src": _file_url(decision.source_path), "start": "0s", "duration": _sec(max(decision.out_seconds, 1)), "hasAudio": "1"}
        if has_video == "1":
            attrs["hasVideo"] = "1"
            attrs["format"] = "r1"
        ET.SubElement(resources, "asset", attrs)

    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", {"name": edl.project_name})
    project_el = ET.SubElement(event, "project", {"name": edl.timeline_name})
    sequence = ET.SubElement(project_el, "sequence", {"format": "r1", "duration": _sec(edl.total_estimated_duration_seconds), "tcStart": "0s", "tcFormat": "NDF", "audioLayout": "stereo", "audioRate": "48k"})
    spine = ET.SubElement(sequence, "spine")
    for decision in edl.decisions:
        dur = max(0.001, decision.out_seconds - decision.in_seconds)
        clip = ET.SubElement(spine, "asset-clip", {"name": decision.title, "ref": asset_refs[decision.media_asset_id], "offset": _sec(decision.timeline_position_seconds), "start": _sec(decision.in_seconds), "duration": _sec(dur), "tcFormat": "NDF"})
        ET.SubElement(clip, "marker", {"start": "0s", "duration": "1/1000s", "value": f"{decision.title}: {decision.reason}"})

    ET.indent(fcpxml, space="  ")
    out = project_path / "06_FCPXML" / f"{project_path.name}_rough_cut.fcpxml"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        backup = out.with_suffix(out.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(out.read_bytes())
    ET.ElementTree(fcpxml).write(out, encoding="utf-8", xml_declaration=True)
    _validate_xml(out)
    summary = FinalCutProject(project_name=project_path.name, timeline_name=edl.timeline_name, fcpxml_path=str(out), edit_decision_list_path=str(edl_path))
    summary_path = project_path / "06_FCPXML" / "final_cut_project.json"
    write_json_safe(summary_path, summary.model_dump())
    log.info("Generated FCPXML: %s", out)
    return out, summary_path
