#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/1ba1c65eb7528b3c0dc8900046407f8ce75bfb25"
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

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

python -m py_compile core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py
python - <<'PY'
import inspect
import orchestrator
params = inspect.signature(orchestrator.StacyOrchestrator.__init__).parameters
if "phase_callback" not in params:
    raise SystemExit("[STACY ARS] ERRO: orchestrator.py incompatível")
print("[STACY ARS] orchestrator.py compatível: phase_callback OK")
PY

# Kill only the STACY daemon; do not match this repair shell itself.
pids="$(pgrep -f '/home/.*/stacy/core_server\.py' 2>/dev/null || true)"
if [ -n "$pids" ]; then
  echo "$pids" | xargs -r kill 2>/dev/null || true
  sleep 2
  echo "$pids" | xargs -r kill -9 2>/dev/null || true
fi

termux-wake-lock
echo "[STACY ARS] iniciando CORE..."
exec python "$ROOT/core_server.py"
