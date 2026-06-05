from __future__ import annotations

import json
from pathlib import Path
from .config import AppConfig, write_json_safe
from .models import AnalysisReport, EditDecision, EditDecisionList
from .logger import get_logger

SUPPORTED_FORMATS = {"youtube_longform", "youtube_short", "podcast", "client_testimonial", "vlog", "generic_rough_cut"}
FORMAT_LIMITS = {
    "youtube_short": (8, 60, 5),
    "youtube_longform": (15, 240, 18),
    "podcast": (30, 600, 24),
    "client_testimonial": (8, 120, 10),
    "vlog": (8, 90, 16),
    "generic_rough_cut": (1, 180, 20),
}


def build_edit_decisions(project: str | Path, edit_format: str, config: AppConfig) -> Path:
    log = get_logger(__name__)
    if edit_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported edit format '{edit_format}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")
    project_path = Path(project).expanduser().resolve()
    analysis_path = project_path / "04_ANALYSIS" / "transcript_analysis.json"
    if not analysis_path.exists():
        raise FileNotFoundError(f"Missing {analysis_path}. Run analyze first.")
    report = AnalysisReport.model_validate_json(analysis_path.read_text())
    min_dur, max_dur, max_count = FORMAT_LIMITS[edit_format]
    manifest = json.loads((project_path / "project_manifest.json").read_text())
    source_by_id = {a["id"]: a["source_path"] for a in manifest.get("assets", [])}
    asset_duration = {a["id"]: float(a.get("duration_seconds") or 0) for a in manifest.get("assets", [])}
    decisions = []
    timeline_pos = 0.0
    seen = set()
    for c in sorted(report.recommended_rough_cut_sections or report.highlight_candidates, key=lambda x: x.score, reverse=True):
        available_end = asset_duration.get(c.media_asset_id, c.end_seconds) or c.end_seconds
        out_seconds = min(max(c.end_seconds, c.start_seconds + min_dur), c.start_seconds + max_dur, available_end)
        if out_seconds <= c.start_seconds:
            continue
        key = (c.media_asset_id, round(c.start_seconds, 1), round(out_seconds, 1))
        if key in seen:
            continue
        seen.add(key)
        decisions.append(EditDecision(
            id=f"ed_{len(decisions)+1:04d}",
            media_asset_id=c.media_asset_id,
            source_path=source_by_id.get(c.media_asset_id, ""),
            in_seconds=round(c.start_seconds, 3),
            out_seconds=round(out_seconds, 3),
            timeline_position_seconds=round(timeline_pos, 3),
            decision_type="select",
            reason=c.reason,
            title=c.title,
            notes=f"Score {c.score}; excerpt: {c.transcript_excerpt[:180]}",
        ))
        timeline_pos += out_seconds - c.start_seconds
        if len(decisions) >= max_count:
            break
    edl = EditDecisionList(project_name=project_path.name, format=edit_format, timeline_name=f"{project_path.name} Rough Cut ({edit_format})", decisions=decisions, total_estimated_duration_seconds=round(timeline_pos, 3))
    out = project_path / "05_EDIT_DECISIONS" / f"edit_decision_list_{edit_format}.json"
    write_json_safe(out, edl.model_dump())
    log.info("Wrote %d edit decisions to %s", len(decisions), out)
    return out
