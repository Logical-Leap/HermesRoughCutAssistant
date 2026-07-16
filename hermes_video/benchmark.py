from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .config import write_json_safe

def _path(project: str | Path) -> Path: return Path(project).expanduser().resolve() / ".hermes" / "benchmark.json"
def init_benchmark(project: str | Path) -> Path:
    return write_json_safe(_path(project), {"version": 1, "baseline": None, "runs": []})
def record_baseline(project: str | Path, minutes: float, cost_usd: float, structure_units: int, errors: int = 0) -> Path:
    p = _path(project); data = json.loads(p.read_text()) if p.exists() else {"version": 1, "runs": []}
    data["baseline"] = {"minutes": minutes, "cost_usd": cost_usd, "structure_units": structure_units, "errors": errors}; return write_json_safe(p, data)
def evaluate(project: str | Path, minutes: float, cost_usd: float, retained_units: int, unflagged_errors: int) -> dict:
    p = _path(project); data = json.loads(p.read_text()); base = data.get("baseline")
    if not base: raise ValueError("Record a baseline before evaluation")
    reduction = (base["minutes"] - minutes) / max(base["minutes"], 0.001); retention = retained_units / max(base["structure_units"], 1)
    metrics = {"time_reduction": reduction, "cost_usd": cost_usd, "structure_retained": retention, "unflagged_errors": unflagged_errors}
    failures = []
    if reduction < .40: failures.append("time reduction is below 40%")
    if unflagged_errors: failures.append("timeline contains unflagged errors")
    if retention < .70: failures.append("structure retained is below 70%")
    run = {"created_at": datetime.now(timezone.utc).isoformat(), "metrics": metrics, "passed": not failures, "failures": failures}; data["runs"].append(run); write_json_safe(p, data)
    return run
