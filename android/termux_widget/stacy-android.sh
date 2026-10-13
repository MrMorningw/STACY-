#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/stacy"
exec python android_core.py "$@"
