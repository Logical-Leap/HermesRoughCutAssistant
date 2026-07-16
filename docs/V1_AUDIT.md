# V1 Audit

Baseline: `main` commit `50fdee9`. The complete README and all tracked Python modules were inspected before V2 changes.

## Measured baseline

| Command | Result |
|---|---|
| `python run.py --help` | PASS, 0.26 s |
| `.venv/bin/python -m pytest -q` | FAIL: pytest not installed; no tracked tests |
| `scripts/run_demo.sh` | PASS, 2.31 s, but exercised marketing montage rather than the documented pipeline |
| `init`, `scan`, `transcribe --engine none`, `analyze`, `build-edit`, `build-fcpxml`, `build-applescript`, `render` | Returned 0 on isolated synthetic media |
| `marketing-edit`, `edit`, `full`, `process-all` | Returned 0, but all video paths used marketing sampling |
| `watch` | Code path audited; bounded baseline unavailable because macOS lacks GNU `timeout` |

The demo printed standard horizontal/vertical filenames that did not exist. Actual outputs were `*_marketing_short_*`.

## Exact command routing

- `edit` and `full`: `cli.py → _run_edit → batch_processor.process_project`. Any video took the early branch in `batch_processor.py:27-30`, called `render_marketing_edits`, and returned before transcription, transcript analysis, normal decisions, or normal rendering.
- `marketing-edit`: created fixed temporal samples and generated FCPXML from the vertical marketing EDL.
- `render`: without `--edl`, `video_renderer.render_project` used whole-asset orientation concatenation instead of decisions.
- `watch`: eventually called the same defective `process_project` path.
- `process-all`: called `process_project` for each child and could exit successfully despite per-project failures.

## Defects

V1 mixed ingest, analysis, selection, rendering, and handoff. Generic code contained an `IMG_3274.MOV`–`IMG_3285.MOV` road-trip plan and fixed selections at percentages including 10%, 15%, 25%, 35%, 45%, 55%, 72%, and 82%. Transcript scoring used substring phrase counts, lexical diversity mislabeled as information density, first-30% hook bias, and score sorting that destroyed chronology. Minimum-duration enforcement extended clips beyond analyzed transcript boundaries. Repeated-phrase logic mixed independent source timelines.

FCPXML was fixed to 1080p30 Rec.709, could understate resource duration, assumed media capabilities, prioritized marketing vertical EDL names, and validated only XML syntax. Default rendering concatenated full clips, accepted contradictory orientation flags, and did not safely escape apostrophes in concat manifests.

Caching was path/mtime-oriented: replaced media could reuse stale audio and transcripts. Watchdog handled creation but not reliable modified/moved events and could process partially copied media. Artifacts were unversioned, provenance was absent, writes were non-atomic, and backup names could collide within one second.

## README drift

The README claimed video transcription, semantic selection, EDL rendering, standard horizontal/vertical outputs, music mixing, and an editable equivalent of the render. The active video path did not perform those stages; output names differed; default render ignored decisions; and marketing FCPXML represented only one simplified variant.

## Useful behavior retained

Safe project scaffolding, flat-folder plus legacy ingest, FFmpeg/FFprobe wrappers, source preservation, backups, AppleScript handoff, and opt-in montage access remain. The montage is quarantined behind `legacy-marketing-montage` and is not a V2 default.
