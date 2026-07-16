from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .config import AppConfig, write_json_safe, write_text_safe
from .editorial_model import ModelBudget, cached_analyze, model_from_config
from .local_analysis import analyze_audio, analyze_scenes
from .media_scanner import iter_media_files
from .metadata_extractor import extract_asset
from .models import Project, TimelineVersion, V2EditDecision, now_iso
from .project_scaffold import init_project
from .retakes import group_retakes
from .sentences import words_to_sentences
from .store import ProjectStore


def _project_id(path: Path) -> str:
    return hashlib.sha1(str(path).encode()).hexdigest()[:16]


def ingest_project(project: str | Path, config: AppConfig) -> dict[str, Any]:
    path = init_project(project)
    store, pid = ProjectStore(path), _project_id(path)
    p = Project(id=pid, name=path.name, path=str(path), root_path=str(path))
    store.upsert("project", {"id": pid, "name": p.name, "path": p.path, "created_at": p.created_at})
    previous_rows = store.rows("media_asset", "project_id=?", (pid,))
    previous = {row["id"]: row["payload"] for row in previous_rows}
    assets, cache_hits = [], 0
    for source in iter_media_files(path, config):
        cached = store.cached_asset(source)
        if cached:
            asset = cached
            cache_hits += 1
        else:
            asset = extract_asset(path, source, config).model_dump()
        stat = source.stat()
        store.upsert("media_asset", {"id": asset["id"], "project_id": pid, "checksum": asset["checksum"], "source_path": asset["source_path"], "payload": asset, "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
        assets.append(asset)

    current = {asset["id"]: asset for asset in assets}
    removed_ids = set(previous) - set(current)
    changed_ids = {asset_id for asset_id in set(previous) & set(current) if previous[asset_id].get("checksum") != current[asset_id].get("checksum")}
    added_ids = set(current) - set(previous)
    for asset_id in removed_ids:
        store.delete_where("media_asset", "id=?", (asset_id,))
    for asset_id in removed_ids | changed_ids:
        for table in ("transcript_word", "transcript_sentence", "scene", "audio_region"):
            store.delete_where(table, "media_asset_id=?", (asset_id,))
    if removed_ids or changed_ids or added_ids:
        for table in ("retake_group", "editorial_unit", "edit_decision", "timeline_version", "approval"):
            store.delete_where(table, "project_id=?", (pid,))
        store.delete_where("model_cache", "1=1")

    manifest = {"project_name": path.name, "project_path": str(path), "asset_count": len(assets), "cache_hits": cache_hits, "assets": assets}
    write_json_safe(path / "project_manifest.json", manifest)
    write_json_safe(path / ".hermes" / "exports" / "project.json", p.model_dump())
    return manifest


def transcribe_words(project: str | Path, config: AppConfig) -> dict[str, int]:
    path, written = Path(project).expanduser().resolve(), 0
    store, pid = ProjectStore(path), _project_id(path)
    assets = [r["payload"] for r in store.rows("media_asset", "project_id=?", (pid,))]
    for asset in assets:
        if not asset.get("has_audio") or (asset.get("media_type") == "audio" and any(x in asset["file_name"].lower() for x in ("music", "song", "score"))):
            continue
        existing = store.rows("transcript_word", "media_asset_id=?", (asset["id"],))
        if existing: continue
        engine = config.transcription_engine.lower()
        words = []
        if engine == "faster-whisper":
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("faster-whisper is required for speech transcription; use --engine none only for media-analysis demos") from exc
            from .audio_extractor import audio_extract_path, extract_audio
            source = Path(asset["source_path"])
            audio = source if asset["media_type"] == "audio" else extract_audio(source, audio_extract_path(path, asset["id"]))
            segments, _ = WhisperModel(config.whisper_model, device="auto", compute_type="auto").transcribe(str(audio), language=config.language or None, word_timestamps=True)
            n = 0
            for segment in segments:
                for word in segment.words or []:
                    n += 1
                    probability = float(getattr(word, "probability", 0) or 0)
                    words.append({"id": f"{asset['id']}_word_{n:06d}", "media_asset_id": asset["id"], "start_seconds": float(word.start), "end_seconds": float(word.end), "text": word.word.strip(), "probability": probability, "confidence": probability})
        elif engine not in {"none", "metadata-only", "metadata_only"}:
            raise ValueError(f"V2 word transcription does not support engine {engine!r}")
        for word in words:
            store.upsert("transcript_word", {"id": word["id"], "project_id": pid, "media_asset_id": asset["id"], "start": word["start_seconds"], "end": word["end_seconds"], "payload": word})
        sentences = words_to_sentences(words)
        for sentence in sentences:
            store.upsert("transcript_sentence", {"id": sentence["id"], "project_id": pid, "media_asset_id": asset["id"], "start": sentence["start_seconds"], "end": sentence["end_seconds"], "payload": sentence})
        written += len(words)
        write_json_safe(path / "03_TRANSCRIPTS" / f"{asset['id']}.json", {"media_asset_id": asset["id"], "words": words, "sentences": sentences}, backup=False)
        write_text_safe(path / "03_TRANSCRIPTS" / f"{asset['id']}.md", "# Word-level transcript\n\n" + "\n".join(f"- `{s['start_seconds']:.3f}-{s['end_seconds']:.3f}` {s['text']}" for s in sentences) + "\n", backup=False)
    return {"words_written": written}


def analyze_local(project: str | Path) -> dict[str, int]:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project)
    pid = _project_id(path); scenes, regions = [], []
    for row in store.rows("media_asset", "project_id=?", (pid,)):
        asset = row["payload"]; source = Path(asset["source_path"]); duration = float(asset.get("duration_seconds") or 0)
        if asset["media_type"] == "video" and duration:
            for i, scene in enumerate(analyze_scenes(source, duration), 1):
                item = {"id": f"{asset['id']}_scene_{i:05d}", "media_asset_id": asset["id"], **scene, "confidence": 1.0}; scenes.append(item)
        if asset.get("has_audio") and duration:
            for i, region in enumerate(analyze_audio(source, duration), 1):
                item = {"id": f"{asset['id']}_audio_{i:05d}", "media_asset_id": asset["id"], **region}; regions.append(item)
    store.replace_project_rows("scene", pid, [{"id": x["id"], "project_id": pid, "media_asset_id": x["media_asset_id"], "start": x["start_seconds"], "end": x["end_seconds"], "payload": x} for x in scenes])
    store.replace_project_rows("audio_region", pid, [{"id": x["id"], "project_id": pid, "media_asset_id": x["media_asset_id"], "start": x["start_seconds"], "end": x["end_seconds"], "payload": x} for x in regions])
    write_json_safe(path / "04_ANALYSIS" / "local_media_analysis.json", {"scenes": scenes, "audio_regions": regions})
    return {"scenes": len(scenes), "audio_regions": len(regions)}


def build_editorial_units(project: str | Path) -> list[dict[str, Any]]:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project); pid = _project_id(path)
    assets = {r["id"]: r["payload"] for r in store.rows("media_asset", "project_id=?", (pid,))}
    sentences = [r["payload"] for r in store.rows("transcript_sentence", "project_id=?", (pid,))]
    units = []
    for sentence in sentences:
        units.append({"id": sentence["id"].replace("sentence", "unit"), "media_asset_id": sentence["media_asset_id"], "start_seconds": sentence["start_seconds"], "end_seconds": sentence["end_seconds"], "text": sentence["text"], "transcript_sentence_ids": [sentence["id"]], "scene_ids": [], "audio_region_ids": [], "confidence": 0.8, "complete": True})
    for aid, asset in assets.items():
        if asset["media_type"] == "video" and not any(u["media_asset_id"] == aid for u in units):
            units.append({"id": f"{aid}_visual_unit", "media_asset_id": aid, "start_seconds": 0.0, "end_seconds": float(asset["duration_seconds"]), "text": "", "transcript_sentence_ids": [], "scene_ids": [r["id"] for r in store.rows("scene", "media_asset_id=?", (aid,))], "audio_region_ids": [r["id"] for r in store.rows("audio_region", "media_asset_id=?", (aid,))], "confidence": 0.35, "complete": True})
    store.replace_project_rows("editorial_unit", pid, [{"id": u["id"], "project_id": pid, "media_asset_id": u["media_asset_id"], "start": u["start_seconds"], "end": u["end_seconds"], "payload": u} for u in units])
    return units


def _continuity(decisions: list[V2EditDecision], assets: dict[str, dict[str, Any]], units: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    active = [d for d in decisions if d.action in {"keep", "trim", "reorder", "alternate"}]
    if not active:
        issues.append("ERROR: timeline has no kept material")
    seen_ranges: set[tuple[str, float, float]] = set()
    expected_offset = 0.0
    last_source_start: dict[str, float] = {}
    reorder_count = 0
    for d in active:
        asset = assets.get(d.media_asset_id)
        if not asset:
            issues.append(f"ERROR: missing media asset {d.media_asset_id} for {d.id}")
            continue
        if not Path(asset["source_path"]).exists():
            issues.append(f"ERROR: missing media file {asset['source_path']}")
        if d.in_seconds < 0 or d.out_seconds <= d.in_seconds:
            issues.append(f"ERROR: invalid duration {d.id}")
        if d.out_seconds > float(asset.get("duration_seconds") or 0) + 0.001:
            issues.append(f"ERROR: source range exceeds media duration {d.id}")
        if abs(d.timeline_position_seconds - expected_offset) > 0.002:
            issues.append(f"ERROR: invalid timeline offset {d.id}")
        expected_offset += max(0.0, d.out_seconds - d.in_seconds)
        key = (d.media_asset_id, round(d.in_seconds, 3), round(d.out_seconds, 3))
        if key in seen_ranges:
            issues.append(f"ERROR: duplicate source range {d.id}")
        seen_ranges.add(key)
        previous = last_source_start.get(d.media_asset_id)
        if previous is not None and d.in_seconds < previous:
            reorder_count += 1
        last_source_start[d.media_asset_id] = d.in_seconds
        unit = units.get(d.editorial_unit_id, {})
        text = str(unit.get("text", "")).strip().lower()
        if text.startswith(("that ", "this ", "it ", "as i said", "earlier ")):
            issues.append(f"WARNING: unresolved-reference risk in {d.id}: {text[:80]}")
        if text.endswith("?") and d is active[-1]:
            issues.append(f"WARNING: question may lack an answer after {d.id}")
        if not d.reason:
            issues.append(f"ERROR: unexplained decision {d.id}")
    if reorder_count > 6:
        issues.append(f"WARNING: excessive reordering ({reorder_count} backwards source jumps)")
    return issues


def plan_project(project: str | Path, edit_format: str = "youtube_longform", target_duration: float | None = None, style: str = "chandler_default", config: AppConfig | None = None) -> dict[str, TimelineVersion]:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project)
    pid = _project_id(path)
    config = config or AppConfig()
    units = build_editorial_units(path)
    assets = {r["id"]: r["payload"] for r in store.rows("media_asset", "project_id=?", (pid,))}
    retakes = group_retakes(units)
    store.replace_project_rows("retake_group", pid, [{"id": r["id"], "project_id": pid, "payload": r} for r in retakes])
    style_path = path / ".hermes" / "style_profiles" / f"{style}.json"
    style_profile = json.loads(style_path.read_text()) if style_path.exists() else {"name": style, "rules": {}, "source_comparisons": []}
    style_rules = style_profile.get("rules", {})
    style_examples = style_profile.get("source_comparisons", [])
    semantic_units = [{**unit, "style_rules": style_rules, "style_examples": style_examples[:3]} for unit in units]
    budget = ModelBudget(max_calls=config.maximum_model_calls, max_tokens=config.maximum_project_tokens, max_cost_usd=config.maximum_project_cost_usd, max_retries=config.maximum_retries)
    semantic = cached_analyze(store, model_from_config(config), semantic_units, budget)
    sem = {s.unit_id: s for s in semantic.units}; preferred = {r["preferred_unit_id"] for r in retakes}; alternates = {u for r in retakes for u in r["alternate_unit_ids"]}
    outputs = {}
    for mode in ("conservative", "aggressive"):
        decisions, position = [], 0.0
        for i, unit in enumerate(units, 1):
            keep = mode == "conservative" or unit["id"] in preferred or unit["id"] not in alternates
            if target_duration and position >= target_duration: keep = False
            action = "keep" if keep else ("alternate" if unit["id"] in alternates else "remove")
            asset = assets[unit["media_asset_id"]]
            reason = ("Preserves complete sentence/visual unit for review" if keep else "Duplicate/retake alternate or beyond target; preserved in database")
            topic_value = sem[unit["id"]].topic if unit["id"] in sem else "general"
            duration = unit["end_seconds"] - unit["start_seconds"]
            d = V2EditDecision(id=f"{mode}_{i:05d}", editorial_unit_id=unit["id"], action=action, reason=reason, rationale=reason, source_path=asset["source_path"], media_asset_id=unit["media_asset_id"], in_seconds=unit["start_seconds"], out_seconds=unit["end_seconds"], timeline_position_seconds=position, timeline_out=position + (duration if keep else 0.0), confidence=float(unit.get("confidence", 0.5)), preserved_context="Complete sentence or scene boundary", tags=[mode, topic_value], alternate_unit_ids=next((r["alternate_unit_ids"] for r in retakes if r["preferred_unit_id"] == unit["id"]), []), notes=f"topic={topic_value}; style={style}")
            decisions.append(d)
            if keep: position += duration
        timeline = TimelineVersion(id=f"{pid}_{mode}", project_id=pid, version_name=f"{mode}_v2", mode=mode, format=edit_format, target_duration_seconds=target_duration, total_duration=position, brief=f"{edit_format} assistant-editor rough cut using style {style}", model_metadata={"provider": semantic.notes[0] if semantic.notes else "unknown", "budget": {"calls": budget.calls, "tokens": budget.tokens, "estimated_cost_usd": budget.cost_usd}, "style_profile": style, "style_rules": style_rules, "style_examples": style_examples[:3]}, decisions=decisions)
        store.upsert("timeline_version", {"id": timeline.id, "project_id": pid, "mode": mode, "status": timeline.status, "payload": timeline.model_dump()})
        for d in decisions: store.upsert("edit_decision", {"id": d.id, "project_id": pid, "timeline_id": timeline.id, "payload": d.model_dump()})
        write_json_safe(path / "05_EDIT_DECISIONS" / f"timeline_{mode}.json", timeline.model_dump())
        outputs[mode] = timeline
    unit_map = {u["id"]: u for u in units}
    issues = _continuity(outputs["conservative"].decisions, assets, unit_map) + _continuity(outputs["aggressive"].decisions, assets, unit_map)
    write_text_safe(path / "04_ANALYSIS" / "continuity_report.md", "# Continuity report\n\n" + ("No deterministic continuity errors found.\n" if not issues else "\n".join(f"- {x}" for x in issues) + "\n"))
    lines = ["# Paper edit", "", "These are assistant-editor rough cuts, not final professional edits.", "", "## Topic map"] + [f"- {t}" for t in semantic.topic_order]
    for mode, timeline in outputs.items():
        lines += ["", f"## {mode.title()}"] + [f"- **{d.action}** `{d.editorial_unit_id}` {d.in_seconds:.3f}–{d.out_seconds:.3f}: {d.reason}; alternates: {', '.join(d.alternate_unit_ids) or 'none'}" for d in timeline.decisions]
    write_text_safe(path / "04_ANALYSIS" / "paper_edit.md", "\n".join(lines) + "\n")
    write_json_safe(path / "04_ANALYSIS" / "topic_map.json", semantic.model_dump())
    return outputs


def create_shorts(project: str | Path) -> Path:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project)
    pid = _project_id(path)
    timelines = store.rows("timeline_version", "project_id=? AND mode='aggressive'", (pid,))
    if not timelines:
        raise FileNotFoundError("Plan timelines before generating shorts")
    kept = [d for d in timelines[-1]["payload"]["decisions"] if d["action"] == "keep"][:3]
    candidates = []
    for orientation in ("vertical", "horizontal"):
        short_decisions: list[V2EditDecision] = []
        position = 0.0
        for i, d in enumerate(kept, 1):
            duration = float(d["out_seconds"]) - float(d["in_seconds"])
            candidates.append({"id": f"short_{orientation}_{i:03d}", "orientation": orientation, "title": f"Candidate {i}", "hook": d["reason"], "caption": d["notes"], "description": "Self-contained assistant-selected complete editorial unit.", "media_asset_id": d["media_asset_id"], "start_seconds": d["in_seconds"], "end_seconds": d["out_seconds"], "confidence": d.get("confidence", 0.55), "context_warning": "Review surrounding context before publishing.", "reframe_notes": "Use center crop only when safe; otherwise use a blur-background layout and verify framing."})
            short_decisions.append(V2EditDecision.model_validate({**d, "id": f"short_{orientation}_{i:03d}", "action": "short_candidate", "timeline_position_seconds": position, "timeline_out": position + duration, "tags": [orientation, "short_candidate"]}))
            position += duration
        mode = "short_vertical" if orientation == "vertical" else "short_horizontal"
        timeline = TimelineVersion(id=f"{pid}_{mode}", project_id=pid, version_name=f"{mode}_v2", mode=mode, format=mode, total_duration=position, brief="Short-form candidates require human context and framing review", decisions=short_decisions)
        store.upsert("timeline_version", {"id": timeline.id, "project_id": pid, "mode": mode, "status": "draft", "payload": timeline.model_dump()})
        write_json_safe(path / "05_EDIT_DECISIONS" / f"timeline_{mode}.json", timeline.model_dump())
    return write_json_safe(path / "04_ANALYSIS" / "short_candidates.json", {"candidates": candidates})


def prepare(project: str | Path, config: AppConfig, edit_format: str, target_duration: float | None = None, style: str = "chandler_default") -> dict[str, Any]:
    manifest = ingest_project(project, config)
    transcription = transcribe_words(project, config)
    local = analyze_local(project)
    timelines = plan_project(project, edit_format, target_duration, style, config=config)
    shorts = create_shorts(project)
    return {"status": "prepared_for_review", "final": False, "manifest": manifest, "transcription": transcription, "analysis": local, "timelines": list(timelines), "shorts": str(shorts)}
