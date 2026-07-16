# V1 audit and baseline

Audit date: 2026-07-16. Baseline commit: `50fdee9`. Branch: `feature/personalized-assistant-editor-v2`.

## Reproduction

- `scripts/run_demo.sh`: exit 0, 1.47 s wall / 5.51 s user / 1.13 s system on this Mac (Python 3.11.15, FFmpeg 8.1.2). It created one six-second synthetic clip and music bed.
- `python3 -m pytest -q`: exit 5 in 0.17 s; **no tests collected**. No `tests/` directory existed.
- No `.venv` existed. The demo happened to run against globally available dependencies.

The apparent demo success is misleading: `edit` detected video and immediately invoked the marketing editor. It skipped audio extraction, transcription, transcript analysis, and generic edit planning. Produced files were marketing MP4s and an FCPXML derived from the marketing EDL; the script printed nonexistent generic horizontal/vertical output paths.

## Exact command map

| User path | CLI dispatch | Implementation | Actual behavior |
|---|---|---|---|
| `edit`, `full` | `cli._run_edit` | `batch_processor.process_project` | Any video → `marketing_editor.render_marketing_edits`; image-only → photo montage; assistant path only for audio-only timed media. |
| `marketing-edit` | direct | `marketing_editor.render_marketing_edits` | Hardcoded/sampled montage and MP4 render, then FCPXML. |
| `render` | direct | `video_renderer.render_project` | With a manifest and any video, concatenates every source clip by orientation and ignores EDL. Explicit `--edl` uses decisions. |
| `watch` | direct | `folder_watcher.watch_projects` | Watchdog or polling invokes `process_project`, therefore video becomes marketing montage. |
| `process-all` | direct | `batch_processor.process_all_projects` | Iterates folders and invokes the same montage-default processor. |
| `build-edit` | direct | `edit_decision_builder.build_edit_decisions` | Sorts highlights by score and enforces fixed min/max durations/counts. |
| `build-fcpxml` | direct | `fcpxml_generator.build_fcpxml` | Chooses newest EDL with a marketing-biased sort, fixed 1080p30 timebase. |

## Architecture and correctness findings

- No SQLite project state, migrations, timeline versioning, approvals, style profiles, benchmarks, or semantic provider abstraction.
- Models have media, raw Whisper `TranscriptSegment`, highlights, and an unconstrained edit decision. Required word/sentence/scene/audio/retake/editorial-unit types are absent.
- Faster Whisper requests word timestamps but discards words and stores raw Whisper segments as editing units.
- Media checksums are recalculated on every scan; metadata and transcripts are not cached by checksum.
- Generic analysis uses transcript-segment scores and fixed first-30-second fallback selections.
- Generic planning is score-only ordering with forced minimum clip extensions, which can create mid-sentence/mid-word cuts and padded content.
- `marketing_editor._known_roadtrip_vertical_plan` contains personal filenames and exact timestamps. Generic montage plans sample fixed percentages (15/25/35/45/55/72/82%).
- Retakes are neither grouped nor preserved as alternates. Removed material is not represented or explained.
- FFmpeg analysis is metadata-only; no VAD, silence, loudness, clipping, noise, or scene-change regions.
- FCPXML hardcodes 30 fps (`100/3000s`), 1920×1080, approximate millisecond times, and marks every source as audio. It does not model roles, placeholders, vertical formats, external audio, source-specific formats, or reference validation beyond XML parsing.
- `render_project` silently bypasses its EDL when a manifest exists. This is dead/misleading generic rendering behavior.
- Watcher has unused direct imports for the old pipeline and photo montage.
- No local review UI or persistent human decisions.
- No provider budgets, schema validation of semantic output, topic map, shorts candidate metadata, style learning, or benchmark gates.

## README drift

README says `edit` runs scan → audio → transcription → analysis → EDL → FCPXML → render. For video it actually runs scan → marketing montage/render → marketing EDL → FCPXML. It calls `full` a correct alias but both silently montage. Demo output names printed at the end do not match generated marketing filenames. README examples contain `/Users/chandler/...`, contrary to portable configuration. It implies generated XML import creates a project but no import was tested. It calls MP4s final in places despite rough-cut limitations.

## Quarantine decision

V2 keeps the old module only behind explicit `legacy-marketing-montage`. No primary, watcher, batch, prepare, render, or FCPXML selection path may call it implicitly. Raw media is never deleted and generated files are backed up before replacement.
