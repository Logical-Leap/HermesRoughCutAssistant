#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$HOME/VideoProjects}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.hermes.roughcut.watch.plist"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/bin/python3"
fi
mkdir -p "$ROOT" "$HOME/Library/LaunchAgents" "$APP_DIR/logs"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.hermes.roughcut.watch</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$APP_DIR/run.py</string>
    <string>watch</string>
    <string>--projects-root</string>
    <string>$ROOT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$APP_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$APP_DIR/logs/watch.out.log</string>
  <key>StandardErrorPath</key>
  <string>$APP_DIR/logs/watch.err.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/com.hermes.roughcut.watch"
echo "Watching $ROOT"
echo "Logs: $APP_DIR/logs/watch.out.log and $APP_DIR/logs/watch.err.log"
