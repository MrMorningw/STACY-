#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
ROOT="$HOME/stacy"

mkdir -p "$ROOT"
cd "$ROOT"

# Always synchronize the authoritative CORE runtime files from main.
# This is intentional: a stale local Python module can be incompatible with
# the current core_server.py even when git reports "Already up to date".
for f in core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py; do
  echo "[STACY ARS] sincronizando $f"
  curl -fsSL "$REPO_RAW/$f" -o "$f"
done

# Verify the runtime before starting it.
python -m py_compile core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py

# Verify the current orchestrator exposes the callback expected by core_server.
python - <<'PY'
import inspect
from orchestrator import StacyOrchestrator
params = inspect.signature(StacyOrchestrator.__init__).parameters
if "phase_callback" not in params:
    raise SystemExit("[STACY ARS] ERRO: orchestrator.py incompatível: phase_callback ausente")
print("[STACY ARS] orchestrator.py compatível: phase_callback OK")
PY

termux-wake-lock
exec python core_server.py
