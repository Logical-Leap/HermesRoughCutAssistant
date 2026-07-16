from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .config import AppConfig, write_json_safe, write_text_safe
from .editorial_model import ModelBudget, cached_analyze, model_from_env
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
    p = Project(id=pid, name=path.name, path=str(path))
    store.upsert("project", {"id": pid, "name": p.name, "path": p.path, "created_at": p.created_at})
    assets, cache_hits = [], 0
    for source in iter_media_files(path, config):
        cached = store.cached_asset(source)
        if cached:
            asset = cached; cache_hits += 1
        else:
            asset = extract_asset(path, source, config).model_dump()
        stat = source.stat()
        store.upsert("media_asset", {"id": asset["id"], "project_id": pid, "checksum": asset["checksum"], "source_path": asset["source_path"], "payload": asset, "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
        assets.append(asset)
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
                    words.append({"id": f"{asset['id']}_word_{n:06d}", "media_asset_id": asset["id"], "start_seconds": float(word.start), "end_seconds": float(word.end), "text": word.word.strip(), "confidence": float(getattr(word, "probability", 0) or 0)})
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


def _continuity(decisions: list[V2EditDecision]) -> list[str]:
    issues = []
    if not decisions: issues.append("ERROR: timeline has no kept material")
    for d in decisions:
        if d.action in {"keep", "trim", "reorder", "alternate"} and d.out_seconds <= d.in_seconds: issues.append(f"ERROR: non-positive duration {d.id}")
        if not d.reason: issues.append(f"ERROR: unexplained decision {d.id}")
    return issues


def plan_project(project: str | Path, edit_format: str = "youtube_longform", target_duration: float | None = None, style: str = "chandler_default") -> dict[str, TimelineVersion]:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project); pid = _project_id(path)
    units = build_editorial_units(path); assets = {r["id"]: r["payload"] for r in store.rows("media_asset", "project_id=?", (pid,))}
    retakes = group_retakes(units)
    store.replace_project_rows("retake_group", pid, [{"id": r["id"], "project_id": pid, "payload": r} for r in retakes])
    semantic = cached_analyze(store, model_from_env(), units, ModelBudget())
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
            d = V2EditDecision(id=f"{mode}_{i:05d}", editorial_unit_id=unit["id"], action=action, reason=reason, source_path=asset["source_path"], media_asset_id=unit["media_asset_id"], in_seconds=unit["start_seconds"], out_seconds=unit["end_seconds"], timeline_position_seconds=position, alternate_unit_ids=next((r["alternate_unit_ids"] for r in retakes if r["preferred_unit_id"] == unit["id"]), []), notes=f"topic={topic_value}; style={style}")
            decisions.append(d)
            if keep: position += d.out_seconds - d.in_seconds
        timeline = TimelineVersion(id=f"{pid}_{mode}", project_id=pid, mode=mode, format=edit_format, target_duration_seconds=target_duration, decisions=decisions)
        store.upsert("timeline_version", {"id": timeline.id, "project_id": pid, "mode": mode, "status": timeline.status, "payload": timeline.model_dump()})
        for d in decisions: store.upsert("edit_decision", {"id": d.id, "project_id": pid, "timeline_id": timeline.id, "payload": d.model_dump()})
        write_json_safe(path / "05_EDIT_DECISIONS" / f"timeline_{mode}.json", timeline.model_dump())
        outputs[mode] = timeline
    issues = _continuity(outputs["conservative"].decisions) + _continuity(outputs["aggressive"].decisions)
    write_text_safe(path / "04_ANALYSIS" / "continuity_report.md", "# Continuity report\n\n" + ("No deterministic continuity errors found.\n" if not issues else "\n".join(f"- {x}" for x in issues) + "\n"))
    lines = ["# Paper edit", "", "These are assistant-editor rough cuts, not final professional edits.", "", "## Topic map"] + [f"- {t}" for t in semantic.topic_order]
    for mode, timeline in outputs.items():
        lines += ["", f"## {mode.title()}"] + [f"- **{d.action}** `{d.editorial_unit_id}` {d.in_seconds:.3f}–{d.out_seconds:.3f}: {d.reason}; alternates: {', '.join(d.alternate_unit_ids) or 'none'}" for d in timeline.decisions]
    write_text_safe(path / "04_ANALYSIS" / "paper_edit.md", "\n".join(lines) + "\n")
    write_json_safe(path / "04_ANALYSIS" / "topic_map.json", semantic.model_dump())
    return outputs


def create_shorts(project: str | Path) -> Path:
    path, store = Path(project).expanduser().resolve(), ProjectStore(project); pid = _project_id(path)
    timelines = store.rows("timeline_version", "project_id=? AND mode='aggressive'", (pid,))
    if not timelines: raise FileNotFoundError("Plan timelines before generating shorts")
    kept = [d for d in timelines[0]["payload"]["decisions"] if d["action"] == "keep"][:3]
    candidates = []
    for orientation in ("vertical", "horizontal"):
        for i, d in enumerate(kept, 1):
            candidates.append({"id": f"short_{orientation}_{i:03d}", "orientation": orientation, "title": f"Candidate {i}", "hook": d["reason"], "caption": d["notes"], "description": "Self-contained assistant-selected complete editorial unit.", "media_asset_id": d["media_asset_id"], "start_seconds": d["in_seconds"], "end_seconds": d["out_seconds"], "confidence": 0.55, "context_warning": "Review surrounding context before publishing.", "reframe_notes": "Vertical center crop is only a suggestion; verify face/subject framing."})
    return write_json_safe(path / "04_ANALYSIS" / "short_candidates.json", {"candidates": candidates})


def prepare(project: str | Path, config: AppConfig, edit_format: str, target_duration: float | None = None, style: str = "chandler_default") -> dict[str, Any]:
    manifest = ingest_project(project, config)
    transcription = transcribe_words(project, config)
    local = analyze_local(project)
    timelines = plan_project(project, edit_format, target_duration, style)
    shorts = create_shorts(project)
    return {"status": "prepared_for_review", "final": False, "manifest": manifest, "transcription": transcription, "analysis": local, "timelines": list(timelines), "shorts": str(shorts)}
