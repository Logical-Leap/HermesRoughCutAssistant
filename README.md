# Hermes Rough Cut Assistant

Hermes Rough Cut Assistant is a local macOS video-project folder workflow. You create one folder that contains all your video projects, make a new folder for each edit, drop clips and music directly into that project folder, and run one command. Hermes builds a rough edit, renders horizontal and vertical MP4 exports, and creates an editable Final Cut Pro XML handoff so you can change the edit in Final Cut Pro.

The system is intentionally file-based. It does not click around Final Cut Pro. It renders preview/final MP4s with ffmpeg and creates FCPXML for the editable Final Cut Pro timeline.

## The simple workflow

```text
VideoProjects/
  Client Interview/
    clip_001.mov
    clip_002.mov
    broll.mp4
    background_music.wav
    02_AUDIO_EXTRACTS/
    03_TRANSCRIPTS/
    04_ANALYSIS/
    05_EDIT_DECISIONS/
    06_FCPXML/
    07_APPLESCRIPT/
    08_EXPORTS/
```

You do not have to use `01_RAW` anymore. Just drop media into the project folder. The older `01_RAW/A_CAM/B_CAM/IPHONE/AUDIO` layout still works if you want it.

## What it now produces

For each project, Hermes can produce:

- `08_EXPORTS/Project_horizontal_1920x1080.mp4` — horizontal render
- `08_EXPORTS/Project_vertical_1080x1920.mp4` — vertical render
- `06_FCPXML/Project_rough_cut.fcpxml` — editable Final Cut Pro XML timeline
- `07_APPLESCRIPT/import_to_final_cut.applescript` — opens that XML in Final Cut Pro
- `project_manifest.json` — scanned media metadata
- `03_TRANSCRIPTS/*.md` and `*.json` — transcripts
- `04_ANALYSIS/transcript_analysis.md` — why clips were selected
- `05_EDIT_DECISIONS/*.json` — the cut list used for rendering and FCPXML

Important: Final Cut Pro does not expose a normal `.fcpbundle` project-file generator for tools like this. The correct editable handoff is FCPXML. Importing the FCPXML into Final Cut Pro creates the editable project/timeline inside your Final Cut library.

## Installation

```bash
gh repo clone Logical-Leap/HermesRoughCutAssistant
cd HermesRoughCutAssistant
chmod +x scripts/install_dependencies.sh scripts/run_demo.sh
scripts/install_dependencies.sh
source .venv/bin/activate
```

The installer uses Homebrew for `ffmpeg`, creates `.venv`, and installs Python requirements.

## Create your video projects folder

```bash
python run.py setup-root --projects-root "/Users/chandler/VideoProjects"
```

Then create one folder per edit:

```bash
mkdir -p "/Users/chandler/VideoProjects/Client Interview 01"
```

Drop clips/music directly into that folder:

```text
/Users/chandler/VideoProjects/Client Interview 01/interview_a_cam.mov
/Users/chandler/VideoProjects/Client Interview 01/interview_b_cam.mov
/Users/chandler/VideoProjects/Client Interview 01/broll_warehouse.mp4
/Users/chandler/VideoProjects/Client Interview 01/background_music.wav
```

Music detection is filename/folder-name based. Name background tracks something like `music.wav`, `background_music.mp3`, `soundtrack.m4a`, or put them in a `Music/` folder.

## One command to edit and render

```bash
python run.py edit --project "/Users/chandler/VideoProjects/Client Interview 01" --format youtube_longform
```

That command runs the whole pipeline:

1. Creates generated-output folders.
2. Scans all clips/music in the project folder.
3. Extracts audio from video clips.
4. Transcribes speech.
5. Analyzes transcript moments.
6. Builds an edit decision list.
7. Generates FCPXML for Final Cut Pro.
8. Generates AppleScript to open the FCPXML.
9. Renders horizontal MP4.
10. Renders vertical MP4.
11. Mixes detected music quietly under the render when a music file exists.

The old command still works too:

```bash
python run.py full --project "/Users/chandler/VideoProjects/Client Interview 01" --format youtube_longform
```

`full` is now an alias for `edit`.

## Open the editable cut in Final Cut Pro

```bash
python run.py open-in-fcp --project "/Users/chandler/VideoProjects/Client Interview 01"
```

Or manually import:

1. Open Final Cut Pro.
2. File -> Import -> XML.
3. Select `06_FCPXML/Client Interview 01_rough_cut.fcpxml`.
4. Final Cut Pro creates an editable project/timeline.
5. Trim, rearrange, relink, color, mix, title, and finish inside Final Cut Pro.

## Render only

If you already have an edit decision list and only want exports:

```bash
python run.py render --project "/Users/chandler/VideoProjects/Client Interview 01"
```

Horizontal only:

```bash
python run.py render --project "/Users/chandler/VideoProjects/Client Interview 01" --horizontal-only
```

Vertical only:

```bash
python run.py render --project "/Users/chandler/VideoProjects/Client Interview 01" --vertical-only
```

## Watch mode

```bash
python run.py watch --projects-root "/Users/chandler/VideoProjects"
```

Now the watcher treats each top-level folder as a project. When new video/audio files are added to a project folder, it processes that project after the folder is quiet.

## Edit formats

Supported formats:

- `youtube_longform`
- `youtube_short`
- `podcast`
- `client_testimonial`
- `vlog`
- `generic_rough_cut`

Example:

```bash
python run.py edit --project "/Users/chandler/VideoProjects/Testimonial" --format client_testimonial
```

## Demo

```bash
source .venv/bin/activate
scripts/run_demo.sh
```

The demo creates a sample clip and music file directly in `sample_project/`, runs the full edit command, renders horizontal and vertical MP4s, and writes FCPXML.

## Required macOS permissions

- Terminal or your shell needs file access to the video project folders.
- Final Cut Pro must be installed for `open-in-fcp`.
- macOS may ask for Automation permission when `osascript` tells Final Cut Pro to open the generated FCPXML. Approve it in System Settings -> Privacy & Security -> Automation.

## What it does not do

- It does not delete raw footage.
- It does not modify existing Final Cut libraries directly.
- It does not click around the Final Cut Pro UI.
- It does not guarantee a polished human-quality final edit. It produces an automated rough edit plus render outputs.
- It does not generate a native `.fcpbundle`; it generates FCPXML, which is the safe editable interchange format Final Cut Pro imports.

## Troubleshooting

- `ffprobe not found` or `ffmpeg not found`: run `brew install ffmpeg`.
- `faster-whisper is not installed`: run `scripts/install_dependencies.sh`.
- Empty transcripts in demo: expected when using `--engine none`; real projects use faster-whisper by default.
- Render fails on a strange codec: transcode source clips to ProRes or H.264 and rerun.
- FCPXML imports but media is offline: keep source media at the original paths or relink media in Final Cut Pro.
- Final Cut Pro does not open: run manual XML import or approve Automation permission.

## The practical version

For everyday use:

```bash
cd HermesRoughCutAssistant
source .venv/bin/activate
python run.py setup-root --projects-root "/Users/chandler/VideoProjects"
mkdir -p "/Users/chandler/VideoProjects/My New Video"
# Drop all clips and music into /Users/chandler/VideoProjects/My New Video
python run.py edit --project "/Users/chandler/VideoProjects/My New Video" --format youtube_longform
python run.py open-in-fcp --project "/Users/chandler/VideoProjects/My New Video"
```

Final renders are in `08_EXPORTS`. Editable Final Cut handoff is in `06_FCPXML`.
