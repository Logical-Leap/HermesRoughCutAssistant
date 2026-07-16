# Hermes Rough Cut Assistant V2

Hermes is a **local-first assistant editor** for Final Cut Pro. It inventories footage, performs deterministic media analysis, transcribes speech with word timestamps, builds sentence-safe editorial units, proposes conservative and aggressive paper edits, provides a local approval interface, and exports editable FCPXML.

It does **not** create a finished professional edit or replace editorial judgment. Final creative decisions, sound design, color, graphics, captions, masking, reframing, and polish remain in Final Cut Pro.

## What it can do

- Store indexed project state in `<project>/.hermes/project.db` while exporting readable JSON and Markdown.
- Use FFprobe/FFmpeg for metadata, checksums, scene changes, silence, loudness, and clipping signals.
- Transcribe locally with Faster Whisper word timestamps and build sentence/clause boundaries.
- Group likely retakes while preserving every rejected take.
- Use a deterministic semantic fallback or an environment-configured OpenAI-compatible endpoint.
- Produce conservative, aggressive, horizontal-short, and vertical-short assistant-editor timelines.
- Explain every keep/remove/alternate and generate deterministic continuity warnings.
- Review source passages, transcripts, decisions, alternatives, ordering, and B-roll notes locally.
- Export rational-time horizontal and vertical FCPXML timelines with markers, roles, and placeholders.
- Compare automated and completed FCPXML, build descriptive style profiles, and measure benchmarks honestly.

## What it cannot do

Hermes does not click through Final Cut with computer vision, stream full videos frame-by-frame to an LLM, use fixed-percentage sampling as editorial intelligence, cut directly on raw Whisper segment boundaries, modify Final Cut libraries, or automatically declare an unreviewed timeline final. FFmpeg previews are optional; FCPXML is the primary handoff.

## Installation

Requirements: macOS, Python 3.11+, FFmpeg/FFprobe, and Final Cut Pro only for manual import testing.

```bash
brew install ffmpeg
gh repo clone Logical-Leap/HermesRoughCutAssistant
cd HermesRoughCutAssistant
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
cp config.example.toml config.toml
pytest -q
```

The default transcription engine is `faster-whisper` with `large-v3`. Choose a smaller model in `config.toml` when appropriate. No paid API is required.

## Standard workflow

```bash
python run.py init --project "/Users/chandler/VideoProjects/My Video"
# Put source media in the project root or the legacy 01_RAW layout.
python run.py ingest --project "/Users/chandler/VideoProjects/My Video"
python run.py analyze --project "/Users/chandler/VideoProjects/My Video"
python run.py plan --project "/Users/chandler/VideoProjects/My Video" --format youtube_longform --target-duration 900 --style chandler_default
python run.py review --project "/Users/chandler/VideoProjects/My Video"
python run.py export-fcpxml --project "/Users/chandler/VideoProjects/My Video" --timeline approved
python run.py open-in-fcp --project "/Users/chandler/VideoProjects/My Video" --timeline approved
```

Convenience preparation:

```bash
python run.py prepare --project "/Users/chandler/VideoProjects/My Video" --format youtube_longform --style chandler_default
```

`prepare` ingests, transcribes, performs technical and semantic analysis, generates conservative/aggressive plans, and creates short candidates. It returns `final: false`; review is mandatory.

## Demo

The demo uses synthetic FFmpeg media and metadata-only transcription, so it does not download a Whisper model:

```bash
scripts/run_demo.sh
```

It demonstrates the real V2 pipeline and creates conservative/aggressive FCPXML rather than rendering a fake final edit.

## Review workflow

`review` prints a local URL, normally `http://127.0.0.1:8765`. The interface shows conservative/aggressive timelines and transcripts, plays source media, records approvals/rejections/restores/alternate choices, supports ordering and B-roll notes, and creates an approved timeline. It is a paper-edit interface, not a nonlinear editor.

## Final Cut workflow

```bash
python run.py export-fcpxml --project "/path" --timeline conservative --orientation horizontal
python run.py export-fcpxml --project "/path" --timeline aggressive --orientation vertical
python run.py export-fcpxml --project "/path" --timeline approved
```

The exporter parses XML and checks resource references, positive durations, and local source existence. Existing XML is backed up. Import manually with **File → Import → XML**, or use `open-in-fcp`, which only opens the generated XML. XML validation does not claim a particular Final Cut release imported it; manual import remains an integration gate.

## Local and cloud model options

Without an endpoint, Hermes uses its deterministic fallback and labels the limitation. For a local or cloud OpenAI-compatible endpoint:

```bash
export EDITORIAL_MODEL_BASE_URL="http://127.0.0.1:1234/v1"
export EDITORIAL_MODEL_NAME="your-model"
export EDITORIAL_MODEL_API_KEY="..."   # only if required
```

Never commit API keys. Model responses are cached by input hash with provider, model, prompt version, token estimate, cost estimate, response, and timestamp. Configure token, call, retry, and cost limits in TOML. Budget exhaustion stops safely.

## Style learning

```bash
python run.py learn-edit --project "/path" --automated-xml automated.fcpxml --final-xml final.fcpxml
python run.py style list --project "/path"
python run.py style show chandler_default --project "/path"
python run.py style rebuild chandler_default --project "/path"
```

V2 uses descriptive statistics, explicit rules, prior-example retrieval, and prompt conditioning—not model fine-tuning.

## Benchmark workflow

```bash
python run.py benchmark init --project "/path"
python run.py benchmark record-baseline --project "/path" --minutes 120 --structure-units 20
python run.py benchmark evaluate --project "/path" --minutes 60 --retained-units 15 --final-xml final.fcpxml
```

Reports fail honestly when active editing-time reduction is below 40%, unflagged cut errors exist, or rough-cut structure retention is below 70%.

## Backward compatibility

- `edit` and `full` are deprecated aliases for `prepare`; they no longer invoke montage rendering.
- `marketing-edit` is deprecated. The old renderer is available only as `legacy-marketing-montage`.
- `scan`, `transcribe`, `build-edit`, and `build-fcpxml` remain compatibility adapters with notices.
- `render` is optional preview functionality and requires a named V2 timeline.

## Privacy and safety

Media and deterministic analysis stay local. Only structured editorial context is sent when an external endpoint is explicitly configured. Raw media is never deleted. Rejected material remains in project state. Generated artifacts are backed up before replacement. Hermes never edits a Final Cut library.

## Troubleshooting

- Missing `ffmpeg`/`ffprobe`: `brew install ffmpeg`.
- Whisper import/model failure: reinstall requirements; `--engine none` is diagnostics-only.
- Empty metadata-only transcript: expected; use Faster Whisper for spoken content.
- Review dependencies missing: install `fastapi` and `uvicorn` from requirements.
- FCPXML missing-media error: restore/relink media and re-ingest.
- Unsupported frame rate: transcode or add verified rational support; Hermes refuses to guess.
- Final Cut does not open: import XML manually and check macOS Automation permission.

See `docs/` for architecture, pipeline, handoff, style learning, benchmarks, audit, migration, and detailed troubleshooting.
