#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="$PWD/sample_project"
python run.py init --project "$PROJECT"
if command -v ffmpeg >/dev/null 2>&1 && [ ! -f "$PROJECT/demo_clip.mp4" ]; then
  ffmpeg -y -f lavfi -i testsrc=size=1280x720:rate=30 -f lavfi -i sine=frequency=880:duration=6 -t 6 -c:v libx264 -pix_fmt yuv420p -c:a aac "$PROJECT/demo_clip.mp4" >/dev/null 2>&1
fi
if command -v ffmpeg >/dev/null 2>&1 && [ ! -f "$PROJECT/background_music.wav" ]; then
  ffmpeg -y -f lavfi -i sine=frequency=220:duration=6 -t 6 -ac 2 "$PROJECT/background_music.wav" >/dev/null 2>&1
fi
python run.py edit --project "$PROJECT" --format generic_rough_cut --engine none
echo "Demo complete: $PROJECT"
echo "Horizontal: $PROJECT/08_EXPORTS/sample_project_horizontal_1920x1080.mp4"
echo "Vertical:   $PROJECT/08_EXPORTS/sample_project_vertical_1080x1920.mp4"
echo "FCPXML:     $PROJECT/06_FCPXML/sample_project_rough_cut.fcpxml"
