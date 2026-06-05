#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required for ffmpeg installation: https://brew.sh" >&2
  exit 1
fi
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
if ! command -v python3 >/dev/null 2>&1; then
  brew install python@3.11
fi
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "Installed. Activate with: source .venv/bin/activate"
