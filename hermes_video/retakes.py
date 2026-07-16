from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Any

def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))

def group_retakes(units: list[dict[str, Any]], threshold: float = 0.72) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    for unit in units:
        text = normalize(unit.get("text", ""))
        match = next((g for g in groups if SequenceMatcher(None, text, normalize(g[0].get("text", ""))).ratio() >= threshold), None)
        if match is None:
            groups.append([unit])
        else:
            match.append(unit)
    output = []
    for i, group in enumerate(groups, 1):
        ranked = sorted(group, key=lambda u: (u.get("confidence", 0), len(normalize(u.get("text", "")))), reverse=True)
        output.append({"id": f"retake_{i:04d}", "unit_ids": [u["id"] for u in group], "preferred_unit_id": ranked[0]["id"], "alternate_unit_ids": [u["id"] for u in ranked[1:]], "reason": "Ranked by transcript confidence and completeness; all takes preserved."})
    return output
