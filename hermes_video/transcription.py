from __future__ import annotations

import json
import subprocess
from pathlib import Path
from .audio_extractor import audio_extract_path, extract_audio
from .config import AppConfig, write_json_safe, write_text_safe
from .logger import get_logger
from .metadata_extractor import load_manifest
from .models import Transcript, TranscriptSegment


def _transcript_paths(project_path: Path, asset_id: str) -> tuple[Path, Path]:
    base = project_path / "03_TRANSCRIPTS" / asset_id
    return base.with_suffix(".json"), base.with_suffix(".md")


def _markdown(transcript: Transcript, source_name: str) -> str:
    lines = [f"# Transcript: {source_name}", "", f"Media asset: `{transcript.media_asset_id}`", f"Language: {transcript.language}", ""]
    for seg in transcript.segments:
        lines.append(f"- `{seg.start_seconds:.2f}-{seg.end_seconds:.2f}` {seg.text}")
    if not transcript.segments:
        lines.append("No speech segments were produced for this asset.")
    lines.append("")
    return "\n".join(lines)


def _transcribe_faster_whisper(audio_path: Path, asset_id: str, source_path: str, config: AppConfig) -> Transcript:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed. Run scripts/install_dependencies.sh or use --engine none for metadata-only testing.") from exc
    model = WhisperModel(config.whisper_model, device="auto", compute_type="auto")
    segments_iter, info = model.transcribe(str(audio_path), language=config.language or None, word_timestamps=True)
    segments = []
    texts = []
    for idx, seg in enumerate(segments_iter, start=1):
        text = (seg.text or "").strip()
        if not text:
            continue
        avg_logprob = float(getattr(seg, "avg_logprob", -0.5) or -0.5)
        confidence = max(0.0, min(1.0, 1.0 + avg_logprob / 5.0))
        segments.append(TranscriptSegment(id=f"{asset_id}_seg_{idx:04d}", media_asset_id=asset_id, start_seconds=float(seg.start), end_seconds=float(seg.end), text=text, confidence=confidence))
        texts.append(text)
    return Transcript(media_asset_id=asset_id, source_path=source_path, segments=segments, full_text=" ".join(texts), language=getattr(info, "language", config.language))


def _transcribe_whisper_cpp(audio_path: Path, asset_id: str, source_path: str, config: AppConfig) -> Transcript:
    cmd = ["whisper-cli", "-f", str(audio_path), "-oj", "-l", config.language]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("whisper-cli not found. Install whisper.cpp or use faster-whisper.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"whisper.cpp failed: {exc.stderr[-1000:]}") from exc
    data_path = audio_path.with_suffix(audio_path.suffix + ".json")
    data = json.loads(data_path.read_text()) if data_path.exists() else {}
    segments = []
    texts = []
    for idx, seg in enumerate(data.get("transcription", []), start=1):
        text = (seg.get("text") or "").strip()
        if text:
            start = float(seg.get("offsets", {}).get("from", 0)) / 1000.0
            end = float(seg.get("offsets", {}).get("to", start)) / 1000.0
            segments.append(TranscriptSegment(id=f"{asset_id}_seg_{idx:04d}", media_asset_id=asset_id, start_seconds=start, end_seconds=end, text=text, confidence=0.8))
            texts.append(text)
    return Transcript(media_asset_id=asset_id, source_path=source_path, segments=segments, full_text=" ".join(texts), language=config.language)


def transcribe_project(project: str | Path, config: AppConfig) -> list[Path]:
    log = get_logger(__name__)
    project_path = Path(project).expanduser().resolve()
    manifest = load_manifest(project_path)
    written = []
    for asset in manifest.get("assets", []):
        if not asset.get("has_audio"):
            log.info("Skipping transcription for silent asset: %s", asset.get("file_name"))
            continue
        name_for_music_check = (asset.get("file_name", "") + " " + asset.get("relative_path", "")).lower()
        if asset.get("media_type") == "audio" and any(token in name_for_music_check for token in ["music", "song", "soundtrack", "score"]):
            log.info("Skipping transcription for likely music bed: %s", asset.get("file_name"))
            continue
        source = Path(asset["source_path"])
        audio_path = source if asset.get("media_type") == "audio" else extract_audio(source, audio_extract_path(project_path, asset["id"]))
        engine = config.transcription_engine.lower()
        if engine == "faster-whisper":
            transcript = _transcribe_faster_whisper(audio_path, asset["id"], asset["source_path"], config)
        elif engine in {"whisper.cpp", "whisper-cpp", "whisper_cpp"}:
            transcript = _transcribe_whisper_cpp(audio_path, asset["id"], asset["source_path"], config)
        elif engine in {"none", "metadata-only", "metadata_only"}:
            transcript = Transcript(media_asset_id=asset["id"], source_path=asset["source_path"], language=config.language)
        else:
            raise ValueError(f"Unsupported transcription engine: {config.transcription_engine}")
        json_path, md_path = _transcript_paths(project_path, asset["id"])
        write_json_safe(json_path, transcript.model_dump())
        write_text_safe(md_path, _markdown(transcript, asset["file_name"]))
        log.info("Wrote transcript JSON and Markdown for %s", asset["file_name"])
        written.extend([json_path, md_path])
    return written
