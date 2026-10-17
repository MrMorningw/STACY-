#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
ROOT="$HOME/stacy"

mkdir -p "$ROOT"
cd "$ROOT"

# Pull the authoritative CORE daemon directly from main so a stale/local
# feature branch cannot leave the phone without core_server.py.
curl -fsSL "$REPO_RAW/core_server.py" -o core_server.py

# Refuse to start if the daemon or its Python dependencies are absent.
python -m py_compile core_server.py

for f in orchestrator.py ai.py config.py memory.py entity_store.py stacy_ecc.py android_session.py; do
  if [ ! -f "$f" ]; then
    curl -fsSL "$REPO_RAW/$f" -o "$f"
  fi
done

termux-wake-lock
exec python core_server.py
