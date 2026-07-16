# Architecture

Hermes V2 separates five layers.

1. **Deterministic local media analysis** — scanner and FFprobe metadata, SHA-256, SQLite cache, Faster Whisper words, sentence building, and FFmpeg scene/silence/loudness/clipping signals.
2. **Semantic content analysis** — `EditorialModel`, deterministic fallback, OpenAI-compatible adapter, Pydantic response validation, cache, and budget envelope.
3. **Editorial planning** — retake groups, editorial units, topic map, conservative/aggressive/short plans, explanations, and continuity checks.
4. **Timeline construction** — versioned decisions, approval state, rational-time FCPXML, markers/roles/placeholders, and optional previews.
5. **Personalization and evaluation** — completed-edit comparison, style profiles, prior examples, and benchmark thresholds.

`ProjectStore` owns `.hermes/project.db`. JSON and Markdown in `03_TRANSCRIPTS`, `04_ANALYSIS`, `05_EDIT_DECISIONS`, and `06_FCPXML` are inspectable exports rather than competing state stores. Source checksum and file metadata control reuse. Model cache keys include provider type and structured input.

The default flow is `ingest → transcribe → technical analysis → editorial units/retakes → semantic topic map → conservative/aggressive/short plans → review → approved FCPXML`. Legacy montage code is isolated and opt-in.

Failure policy is conservative: missing media, invalid ranges, unsupported timebases, malformed model JSON, exceeded budgets, and empty timelines stop or create explicit warnings. Raw media and rejected takes remain untouched.
