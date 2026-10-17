#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
ROOT="$HOME/stacy"

mkdir -p "$ROOT"
cd "$ROOT"

echo "[STACY ARS] sincronizando CORE completo..."
PY_FILES=(
  action.py ai.py anpes.py autonomy.py command.py config.py context.py
  conversation.py cortex.py ctac.py entity_resolver.py entity_store.py
  intent.py knowledge.py memory.py mepo.py orchestration.py orchestrator.py
  stacy_ecc.py tasks.py android_session.py core_server.py
)

for f in "${PY_FILES[@]}"; do
  echo "[STACY ARS] -> $f"
  curl -fsSL --retry 3 --retry-delay 1 "$REPO_RAW/$f" -o "$f.tmp"
  test -s "$f.tmp"
  mv "$f.tmp" "$f"
done

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

python -m py_compile "${PY_FILES[@]}"

python - <<'PY'
import inspect
import orchestrator
params = inspect.signature(orchestrator.StacyOrchestrator.__init__).parameters
if "phase_callback" not in params:
    raise SystemExit("[STACY ARS] ERRO: orchestrator.py incompatível: phase_callback ausente")
print("[STACY ARS] grafo do CORE carregado: OK")
print("[STACY ARS] phase_callback: OK")
PY

# Stop only STACY daemon processes from this checkout.
pids="$(pgrep -f 'python(3)?[[:space:]]+.*[/]stacy[/]core_server\.py' 2>/dev/null || true)"
if [ -n "$pids" ]; then
  echo "[STACY ARS] encerrando CORE antigo: $pids"
  echo "$pids" | xargs -r kill 2>/dev/null || true
  sleep 2
  echo "$pids" | xargs -r kill -9 2>/dev/null || true
fi

termux-wake-lock
echo "[STACY ARS] iniciando CORE..."
exec python "$ROOT/core_server.py"
