from __future__ import annotations
import json
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from .config import write_json_safe

def parse_fcpxml_clips(path: str | Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot(); clips = []
    from fractions import Fraction
    def sec(v: str) -> float: return float(Fraction(v.removesuffix("s")))
    for clip in root.findall(".//spine/asset-clip"):
        clips.append({"ref": clip.get("ref"), "start": sec(clip.get("start", "0s")), "duration": sec(clip.get("duration", "0s")), "offset": sec(clip.get("offset", "0s"))})
    return clips

def compare_timelines(automated: str | Path, final: str | Path) -> dict[str, Any]:
    auto, human = parse_fcpxml_clips(automated), parse_fcpxml_clips(final)
    auto_keys = {(x["ref"], round(x["start"], 2), round(x["duration"], 2)) for x in auto}; human_keys = {(x["ref"], round(x["start"], 2), round(x["duration"], 2)) for x in human}
    retained = len(auto_keys & human_keys) / max(1, len(auto_keys))
    return {"automated_clip_count": len(auto), "human_clip_count": len(human), "exact_select_retention": retained, "average_human_clip_seconds": statistics.mean([x["duration"] for x in human]) if human else 0, "human_total_seconds": sum(x["duration"] for x in human)}

def learn_edit(project: str | Path, automated: str | Path, final: str | Path, name: str = "chandler_default") -> Path:
    project_path = Path(project).expanduser().resolve(); stats = compare_timelines(automated, final)
    profile = {"name": name, "version": 1, "source_comparisons": [{"automated": str(automated), "human_final": str(final)}], "descriptive_stats": stats, "rules": {"prefer_complete_sentences": True, "target_average_clip_seconds": stats["average_human_clip_seconds"]}, "method": "retrieval and prompt conditioning; no fine-tuning"}
    return write_json_safe(project_path / ".hermes" / "style_profiles" / f"{name}.json", profile)
def list_styles(project: str | Path) -> list[str]: return [p.stem for p in sorted((Path(project) / ".hermes" / "style_profiles").glob("*.json"))]
def show_style(project: str | Path, name: str) -> dict: return json.loads((Path(project) / ".hermes" / "style_profiles" / f"{name}.json").read_text())
