#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="$PWD/sample_project"
python run.py init --project "$PROJECT"
if command -v ffmpeg >/dev/null 2>&1 && [ ! -f "$PROJECT/01_RAW/A_CAM/demo.mp4" ]; then
  ffmpeg -y -f lavfi -i testsrc=size=1280x720:rate=30 -f lavfi -i sine=frequency=880:duration=3 -t 3 -c:v libx264 -pix_fmt yuv420p -c:a aac "$PROJECT/01_RAW/A_CAM/demo.mp4" >/dev/null 2>&1
fi
python run.py scan --project "$PROJECT"
python run.py transcribe --project "$PROJECT" --engine none
python run.py analyze --project "$PROJECT"
python run.py build-edit --project "$PROJECT" --format generic_rough_cut
python run.py build-fcpxml --project "$PROJECT"
python run.py build-applescript --project "$PROJECT"
echo "Demo complete: $PROJECT"
