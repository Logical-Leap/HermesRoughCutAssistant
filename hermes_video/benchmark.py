from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import write_json_safe, write_text_safe
from .style import parse_fcpxml_clips


def _path(project: str | Path) -> Path:
    return Path(project).expanduser().resolve() / ".hermes" / "benchmark.json"


def _raw_duration(project: str | Path) -> float:
    db = Path(project).expanduser().resolve() / ".hermes" / "project.db"
    if not db.exists():
        return 0.0
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT payload FROM media_asset").fetchall()
    return sum(float(json.loads(row[0]).get("duration_seconds") or 0) for row in rows)


def init_benchmark(project: str | Path) -> Path:
    return write_json_safe(_path(project), {"version": 2, "project_type": "spoken_content", "raw_footage_duration_seconds": _raw_duration(project), "baseline": None, "runs": []})


def record_baseline(project: str | Path, minutes: float | None = None, cost_usd: float = 0.0, structure_units: int | None = None, errors: int = 0, human_review_minutes: float = 0.0, human_correction_minutes: float = 0.0) -> Path:
    p = _path(project)
    data = json.loads(p.read_text()) if p.exists() else {"version": 2, "runs": [], "raw_footage_duration_seconds": _raw_duration(project)}
    data["baseline"] = {
        "active_human_editing_minutes": float(minutes or 0),
        "estimated_llm_cost_usd": float(cost_usd),
        "structure_units": int(structure_units or 0),
        "incorrect_removals": int(errors),
        "human_review_minutes": float(human_review_minutes),
        "human_correction_minutes": float(human_correction_minutes),
    }
    return write_json_safe(p, data)


def evaluate(project: str | Path, minutes: float | None = None, cost_usd: float = 0.0, retained_units: int | None = None, unflagged_errors: int = 0, final_xml: str | Path | None = None, restored_passages: int = 0, missing_keeper_moments: int = 0) -> dict[str, Any]:
    p = _path(project)
    data = json.loads(p.read_text())
    base = data.get("baseline")
    if not base:
        raise ValueError("Record a baseline before evaluation")
    final_clips = parse_fcpxml_clips(final_xml) if final_xml else []
    baseline_minutes = float(base.get("active_human_editing_minutes") or 0)
    active_minutes = float(minutes or 0)
    baseline_units = int(base.get("structure_units") or 0)
    retained = int(retained_units if retained_units is not None else len(final_clips))
    reduction = (baseline_minutes - active_minutes) / max(baseline_minutes, 0.001)
    retention = retained / max(baseline_units, 1)
    metrics = {
        "raw_footage_duration_seconds": data.get("raw_footage_duration_seconds", 0),
        "automated_processing_time_minutes": 0.0,
        "estimated_llm_token_usage": 0,
        "estimated_llm_cost_usd": float(cost_usd),
        "human_review_time_minutes": 0.0,
        "human_correction_time_minutes": active_minutes,
        "total_active_human_editing_time_minutes": active_minutes,
        "active_time_reduction": reduction,
        "time_reduction": reduction,
        "automated_structure_retained": retention,
        "structure_retained": retention,
        "restored_passages": restored_passages,
        "incorrect_removals": int(unflagged_errors),
        "mid_sentence_cuts": int(unflagged_errors),
        "missing_keeper_moments": missing_keeper_moments,
        "final_timeline_duration_seconds": sum(x["duration"] for x in final_clips),
    }
    failures = []
    if reduction < 0.40:
        failures.append("active human editing-time reduction is below 40%")
    if unflagged_errors:
        failures.append("timeline contains unflagged mid-word/mid-sentence errors")
    if retention < 0.70:
        failures.append("rough-cut structure retained is below 70%")
    run = {"created_at": datetime.now(timezone.utc).isoformat(), "metrics": metrics, "passed": not failures, "failures": failures}
    data.setdefault("runs", []).append(run)
    write_json_safe(p, data)
    report = ["# Benchmark report", "", f"**Result:** {'PASS' if run['passed'] else 'FAIL'}", "", "## Metrics"]
    report += [f"- {key}: {value}" for key, value in metrics.items()]
    report += ["", "## Threshold failures"] + ([f"- {x}" for x in failures] if failures else ["- None"])
    write_text_safe(Path(project).expanduser().resolve() / "04_ANALYSIS" / "benchmark_report.md", "\n".join(report) + "\n")
    return run
