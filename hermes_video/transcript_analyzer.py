from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from .config import AppConfig, write_json_safe, write_text_safe
from .logger import get_logger
from .metadata_extractor import load_manifest
from .models import AnalysisReport, HighlightCandidate, Transcript


def _load_transcripts(project_path: Path) -> list[Transcript]:
    return [Transcript.model_validate_json(path.read_text()) for path in sorted((project_path / "03_TRANSCRIPTS").glob("*.json"))]


def _title(text: str, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9']+", text)[:8]
    return " ".join(words).strip().title() or fallback


def _fallback_candidates(project_path: Path, report: AnalysisReport) -> None:
    manifest = load_manifest(project_path)
    for asset in manifest.get("assets", []):
        if asset.get("duration_seconds", 0) <= 0:
            continue
        end = min(float(asset["duration_seconds"]), 30.0)
        report.highlight_candidates.append(HighlightCandidate(
            id=f"hl_{asset['id']}_fallback",
            media_asset_id=asset["id"],
            start_seconds=0.0,
            end_seconds=end,
            title=f"Opening Select - {asset['file_name']}",
            reason="metadata-only fallback select because no transcript segments were available",
            score=40.0,
            transcript_excerpt="",
        ))


def analyze_project(project: str | Path, config: AppConfig) -> tuple[Path, Path]:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    manifest = load_manifest(project_path)
    durations = {a["id"]: float(a.get("duration_seconds") or 0) for a in manifest.get("assets", [])}
    report = AnalysisReport(project_name=project_path.name)
    repeated_tracker: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for transcript in _load_transcripts(project_path):
        total = durations.get(transcript.media_asset_id, 0) or max([s.end_seconds for s in transcript.segments], default=0)
        for seg in transcript.segments:
            text = seg.text.strip()
            lower = text.lower()
            duration = max(0.1, seg.end_seconds - seg.start_seconds)
            words = re.findall(r"[a-z']+", lower)
            filler_count = sum(lower.count(w) for w in config.filler_words)
            phrase_hits = [p for p in config.hook_phrases if p in lower]
            info_density = len(set(words)) / max(1, len(words))
            score = 35 + len(phrase_hits) * 30 + min(20, len(words) / 3) + info_density * 20 - filler_count * 8
            if seg.start_seconds <= total * 0.3:
                score += 10
            if 8 <= duration <= 90:
                score += 10
            if duration < 3:
                score -= 15
            first_phrase = " ".join(words[:6])
            if first_phrase:
                repeated_tracker[first_phrase].append((transcript.media_asset_id, seg.start_seconds))
            if phrase_hits or score >= 62:
                reason = "; ".join([f"contains '{p}'" for p in phrase_hits]) or "high information density and clean duration"
                candidate = HighlightCandidate(
                    id=f"hl_{transcript.media_asset_id}_{len(report.highlight_candidates)+1:04d}",
                    media_asset_id=transcript.media_asset_id,
                    start_seconds=round(seg.start_seconds, 3),
                    end_seconds=round(seg.end_seconds, 3),
                    title=_title(text, "Strong Moment"),
                    reason=reason,
                    score=round(max(0, min(100, score)), 2),
                    transcript_excerpt=text[:500],
                )
                report.highlight_candidates.append(candidate)
                if seg.start_seconds <= total * 0.3 or phrase_hits:
                    report.likely_hook_moments.append(candidate)
            if filler_count >= 3 or info_density < 0.35:
                report.weak_sections.append({"media_asset_id": transcript.media_asset_id, "start_seconds": seg.start_seconds, "end_seconds": seg.end_seconds, "reason": "filler-heavy or low information density", "text": text[:300]})

    for phrase, occurrences in repeated_tracker.items():
        if len(occurrences) > 1:
            times = sorted(occurrences, key=lambda x: x[1])
            if any((times[i + 1][1] - times[i][1]) <= 180 for i in range(len(times) - 1)):
                report.repeated_phrases.append({"phrase": phrase, "occurrences": [{"media_asset_id": a, "start_seconds": s} for a, s in times]})

    if not report.highlight_candidates:
        _fallback_candidates(project_path, report)
    report.highlight_candidates.sort(key=lambda c: c.score, reverse=True)
    report.recommended_rough_cut_sections = report.highlight_candidates[:12]
    report.suggested_clip_titles = [c.title for c in report.recommended_rough_cut_sections]
    report.suggested_structure = ["Hook", "Problem", "Credibility/context", "Core points", "Solution", "Close / call to action"]
    report.notes_for_broll = ["Cover jump cuts around repeated starts.", "Add B-roll over weak or filler-heavy sections if content must remain.", "Use markers as review notes inside Final Cut Pro."]

    json_path = project_path / "04_ANALYSIS" / "transcript_analysis.json"
    md_path = project_path / "04_ANALYSIS" / "transcript_analysis.md"
    write_json_safe(json_path, report.model_dump())
    write_text_safe(md_path, _analysis_markdown(report))
    log.info("Wrote analysis report to %s", md_path)
    return json_path, md_path


def _analysis_markdown(report: AnalysisReport) -> str:
    lines = [f"# Transcript Analysis: {report.project_name}", "", "## Recommended rough cut sections"]
    for c in report.recommended_rough_cut_sections:
        lines.append(f"- **{c.title}** (`{c.media_asset_id}` {c.start_seconds:.2f}-{c.end_seconds:.2f}, score {c.score}) - {c.reason}")
        if c.transcript_excerpt:
            lines.append(f"  - Excerpt: {c.transcript_excerpt}")
    lines += ["", "## Weak sections"]
    for w in report.weak_sections:
        lines.append(f"- `{w['media_asset_id']}` {w['start_seconds']:.2f}-{w['end_seconds']:.2f}: {w['reason']}")
    lines += ["", "## Repeated phrases"]
    for r in report.repeated_phrases:
        lines.append(f"- `{r['phrase']}` repeated {len(r['occurrences'])} times")
    lines += ["", "## Suggested structure"] + [f"- {s}" for s in report.suggested_structure]
    lines += ["", "## B-roll notes"] + [f"- {n}" for n in report.notes_for_broll]
    return "\n".join(lines) + "\n"
