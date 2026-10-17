#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
ROOT="$HOME/stacy"

mkdir -p "$ROOT"
cd "$ROOT"

echo "[STACY ARS] sincronizando CORE oficial..."
for f in core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py; do
  echo "[STACY ARS] -> $f"
  curl -fsSL --retry 3 --retry-delay 1 "$REPO_RAW/$f" -o "$f.tmp"
  test -s "$f.tmp"
  mv "$f.tmp" "$f"
done

# Always load sibling modules from ~/stacy first.
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Validate syntax and the authoritative orchestrator before touching the daemon.
python -m py_compile core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py
python - <<'PY'
import inspect
import orchestrator
params = inspect.signature(orchestrator.StacyOrchestrator.__init__).parameters
if "phase_callback" not in params:
    raise SystemExit("[STACY ARS] ERRO: orchestrator.py sem phase_callback")
print("[STACY ARS] orchestrator.py compatível: phase_callback OK")
PY

# Stop stale STACY CORE instances. The previous repair only matched an
# absolute path; Termux often launches it as `python core_server.py`.
pkill -f 'core_server\.py' 2>/dev/null || true
sleep 2

# If anything still owns the port, report it instead of hiding the failure.
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[STACY ARS] ERRO: porta 8765 ainda está ocupada."
  lsof -iTCP:8765 -sTCP:LISTEN || true
  exit 1
fi

termux-wake-lock
echo "[STACY ARS] iniciando CORE..."
exec python "$ROOT/core_server.py"
