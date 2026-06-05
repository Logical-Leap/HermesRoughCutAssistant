# Hermes Rough Cut Assistant

Hermes Rough Cut Assistant is a local macOS automation tool for Final Cut Pro. It takes source media from disk, transcribes dialogue, analyzes clip metadata, creates a rough cut plan, writes an edit decision list, generates FCPXML, and prepares an AppleScript handoff into Final Cut Pro.

It is built for deterministic, file-based workflows. No fragile GUI clicking. No pretending to replace editors. The goal is simple: give you a clean starting timeline so you can spend more time editing and less time assembling.

## What it does

- Creates a repeatable project folder scaffold.
- Scans raw footage with `ffprobe`.
- Writes `project_manifest.json` with paths, durations, codecs, frame rates, resolution, audio streams, creation time, camera group, and checksums.
- Extracts mono 16 kHz WAV audio for transcription.
- Transcribes speech with `faster-whisper` or `whisper.cpp`.
- Writes transcript JSON and Markdown with segment timestamps.
- Analyzes transcripts for hooks, strong thesis statements, weak sections, filler-heavy sections, repeated starts, B-roll notes, and rough cut sections.
- Builds a deterministic edit decision list.
- Generates FCPXML with source media references, sequential clips, and markers.
- Generates AppleScript to open the FCPXML in Final Cut Pro.
- Watches a projects root and processes new footage automatically.

## What it does not do

- It does not replace a human editor.
- It does not modify Final Cut Pro libraries directly.
- It does not delete raw footage.
- It does not click around the Final Cut Pro interface.
- It does not attempt advanced visual scene understanding in this first version.

## Folder structure

```text
VideoProjects/
  ProjectName/
    01_RAW/
      A_CAM/
      B_CAM/
      IPHONE/
      AUDIO/
    02_AUDIO_EXTRACTS/
    03_TRANSCRIPTS/
    04_ANALYSIS/
    05_EDIT_DECISIONS/
    06_FCPXML/
    07_APPLESCRIPT/
    08_EXPORTS/
    project_manifest.json
```

## Installation

```bash
cd HermesRoughCutAssistant
chmod +x scripts/install_dependencies.sh scripts/run_demo.sh
scripts/install_dependencies.sh
source .venv/bin/activate
```

The installer uses Homebrew for `ffmpeg`, creates `.venv`, and installs Python requirements.

## Required macOS permissions

- Terminal or your shell app needs file access to your media/project folders.
- Final Cut Pro must be installed for `open-in-fcp`.
- macOS may ask for Automation permission when `osascript` tells Final Cut Pro to open the generated FCPXML. Approve it in System Settings -> Privacy & Security -> Automation if prompted.

## ffmpeg installation

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

## Whisper/transcription setup

Default engine is `faster-whisper`:

```bash
source .venv/bin/activate
python -m pip install faster-whisper
```

You can also use whisper.cpp if `whisper-cli` is installed and available on `PATH`; set `transcription_engine` to `whisper.cpp` in `config.json`.

For metadata-only demos without speech transcription, use `--engine none`.

## Configuration

Copy the example config if you want local overrides:

```bash
cp config.example.json config.json
```

Safe defaults include supported file extensions, hook phrases, filler words, clip duration limits, and the Final Cut Pro app name.

## Commands

```bash
python run.py init --project "/Users/chandler/VideoProjects/MyProject"
python run.py scan --project "/Users/chandler/VideoProjects/MyProject"
python run.py transcribe --project "/Users/chandler/VideoProjects/MyProject"
python run.py analyze --project "/Users/chandler/VideoProjects/MyProject"
python run.py build-edit --project "/Users/chandler/VideoProjects/MyProject" --format "youtube_longform"
python run.py build-fcpxml --project "/Users/chandler/VideoProjects/MyProject"
python run.py build-applescript --project "/Users/chandler/VideoProjects/MyProject"
python run.py open-in-fcp --project "/Users/chandler/VideoProjects/MyProject"
python run.py full --project "/Users/chandler/VideoProjects/MyProject" --format "youtube_longform"
python run.py watch --projects-root "/Users/chandler/VideoProjects"
```

Supported edit formats:

- `youtube_longform`
- `youtube_short`
- `podcast`
- `client_testimonial`
- `vlog`
- `generic_rough_cut`

## Demo mode

```bash
source .venv/bin/activate
scripts/run_demo.sh
```

The demo initializes `sample_project`, creates a tiny generated test video if `ffmpeg` is available, scans it, runs metadata-only transcription, analyzes, builds an EDL, generates FCPXML, and writes AppleScript.

## Final Cut Pro workflow

1. Drop camera/audio files into `01_RAW` subfolders.
2. Run the full pipeline.
3. Review `04_ANALYSIS/transcript_analysis.md`.
4. Review `05_EDIT_DECISIONS/*.json`.
5. Import `06_FCPXML/*.fcpxml` into Final Cut Pro, or run `open-in-fcp`.
6. Finish pacing, trimming, color, audio mix, titles, and delivery inside Final Cut Pro.

## Manual FCPXML import

In Final Cut Pro:

1. Open Final Cut Pro.
2. Choose File -> Import -> XML.
3. Select the generated file in `06_FCPXML`.
4. Review the event/project and relink media if your storage paths changed.

## Safety behavior

- Raw footage is never deleted.
- Existing generated files are backed up with timestamped `.bak` suffixes before overwrite.
- The system only writes reviewable artifacts: manifest, audio extracts, transcripts, analysis, EDL, FCPXML, and AppleScript.
- Generated outputs are reproducible from source media, manifest, transcripts, and EDL files.

## Troubleshooting

- `ffprobe not found`: run `brew install ffmpeg`.
- `faster-whisper is not installed`: run `scripts/install_dependencies.sh` or `python -m pip install faster-whisper`.
- `No edit decision list found`: run `build-edit` before `build-fcpxml`.
- Empty transcripts in demo: expected when using `--engine none`. Use faster-whisper for real speech.
- Final Cut Pro does not open: check the generated AppleScript path, install Final Cut Pro, and approve macOS Automation permission.
- FCPXML imports but media is offline: keep source media at the original paths or relink media in Final Cut Pro.

## Extending with more agents

The pipeline is modular:

- Add new analysis agents after transcript generation and before EDL creation.
- Write new agent outputs into `04_ANALYSIS`.
- Keep intermediate files deterministic and inspectable.
- Add new edit formats in `edit_decision_builder.py`.
- Add richer timeline features in `fcpxml_generator.py`.
- Preserve the rule: filesystem artifacts are source of truth, Final Cut Pro import is a handoff, and the editor remains the final creative decision maker.

## Marketing promise

Drop in footage. Get a Final Cut Pro timeline you can start editing. Hermes handles the repetitive setup work before the real edit begins.
