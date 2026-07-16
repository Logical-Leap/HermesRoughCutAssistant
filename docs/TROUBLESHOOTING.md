# Troubleshooting

## Media and ingest

Run `ffprobe -version` and `ffmpeg -version`. If metadata is stale after replacing source media, rerun `ingest`. Generated folders are excluded from scans.

## Transcription

Faster Whisper downloads its configured model on first use. Verify disk and network capacity. `--engine none` is diagnostics-only and yields visual units, not spoken-content intelligence.

## Model provider

Unset `EDITORIAL_MODEL_BASE_URL` for deterministic fallback. Compatible servers commonly expect a `/v1` base URL. Invalid JSON, timeout, retries, or token/cost/call ceilings fail safely. Never put keys in TOML or Git.

## Review server

Use `python run.py review --project /path --host 127.0.0.1 --port 8765`. If occupied, choose another port. The server is local by default; do not expose it publicly without authentication and network controls.

## FCPXML

Missing media and unsupported FPS are deliberate hard failures. Keep source paths stable or re-ingest after moving a project. Validate and import XML manually before relying on a production timeline. `open-in-fcp` requires macOS Automation permission.

## Watcher

The watcher prepares projects; it does not approve timelines or render final deliverables. Existing projects can be backfilled with `process-all`. Inspect `logs/watch.out.log` and `logs/watch.err.log` for LaunchAgent failures.
