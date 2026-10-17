#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/stacy"
SCRIPT="$ROOT/android/termux_widget/stacy-core-daemon.sh"
URL="https://raw.githubusercontent.com/MrMorningw/STACY-/main/android/termux_widget/stacy-core-daemon.sh?ars=$(date +%s)"

mkdir -p "$(dirname "$SCRIPT")"
curl -fsSL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 1 "$URL" -o "$SCRIPT.tmp"
test -s "$SCRIPT.tmp"
mv "$SCRIPT.tmp" "$SCRIPT"
chmod +x "$SCRIPT"
exec bash "$SCRIPT"
