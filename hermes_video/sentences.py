from __future__ import annotations
import re
from typing import Any

TERMINAL = re.compile(r"[.!?][\"']?$")

def words_to_sentences(words: list[dict[str, Any]], max_pause: float = 0.9, max_words: int = 45) -> list[dict[str, Any]]:
    """Build clause-safe units. Boundaries always coincide with word boundaries."""
    if not words: return []
    result, current = [], []
    for word in sorted(words, key=lambda w: (w["start_seconds"], w["end_seconds"])):
        pause = word["start_seconds"] - current[-1]["end_seconds"] if current else 0
        if current and (pause >= max_pause or len(current) >= max_words):
            result.append(_sentence(current, len(result))); current = []
        current.append(word)
        if TERMINAL.search(str(word.get("text", "")).strip()):
            result.append(_sentence(current, len(result))); current = []
    if current: result.append(_sentence(current, len(result)))
    return result

def _sentence(words: list[dict[str, Any]], index: int) -> dict[str, Any]:
    asset = words[0]["media_asset_id"]
    return {"id": f"{asset}_sentence_{index+1:05d}", "media_asset_id": asset, "start_seconds": float(words[0]["start_seconds"]), "end_seconds": float(words[-1]["end_seconds"]), "text": " ".join(str(w["text"]).strip() for w in words).strip(), "word_ids": [w["id"] for w in words], "speaker_label": words[0].get("speaker_label")}

def refine_boundary(value: float, words: list[dict[str, Any]], side: str) -> float:
    if not words: return value
    candidates = [float(w["start_seconds"] if side == "start" else w["end_seconds"]) for w in words]
    return min(candidates, key=lambda t: abs(t - value))
