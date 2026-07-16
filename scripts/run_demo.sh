#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="$PWD/sample_project"
PYTHON="${PYTHON:-$PWD/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then PYTHON="python3"; fi

"$PYTHON" run.py init --project "$PROJECT"
if command -v ffmpeg >/dev/null 2>&1 && [ ! -f "$PROJECT/demo_clip.mp4" ]; then
  ffmpeg -y -f lavfi -i testsrc=size=1280x720:rate=30 -f lavfi -i sine=frequency=880:duration=6 -t 6 -c:v libx264 -pix_fmt yuv420p -c:a aac "$PROJECT/demo_clip.mp4" >/dev/null 2>&1
fi
if command -v ffmpeg >/dev/null 2>&1 && [ ! -f "$PROJECT/background_music.wav" ]; then
  ffmpeg -y -f lavfi -i sine=frequency=220:duration=6 -t 6 -ac 2 "$PROJECT/background_music.wav" >/dev/null 2>&1
fi

"$PYTHON" run.py prepare --project "$PROJECT" --format generic_rough_cut --engine none
"$PYTHON" run.py export-fcpxml --project "$PROJECT" --timeline conservative --orientation horizontal
"$PYTHON" run.py export-fcpxml --project "$PROJECT" --timeline aggressive --orientation vertical

echo "V2 demo complete: $PROJECT"
echo "Database:     $PROJECT/.hermes/project.db"
echo "Paper edit:   $PROJECT/04_ANALYSIS/paper_edit.md"
echo "Continuity:   $PROJECT/04_ANALYSIS/continuity_report.md"
echo "Conservative: $PROJECT/06_FCPXML/sample_project_conservative_horizontal.fcpxml"
echo "Aggressive:   $PROJECT/06_FCPXML/sample_project_aggressive_vertical.fcpxml"
echo "No timeline was declared final; run review before exporting approved FCPXML."
