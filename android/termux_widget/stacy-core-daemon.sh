#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="${HOME}/stacy"
REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
LOG="${ROOT}/stacy-core-daemon.log"
PIDFILE="${ROOT}/.stacy-core-daemon.pid"
PYTHON="$(command -v python || true)"
CURL="$(command -v curl || true)"
STAGE="${ROOT}/.stacy-core-sync.$$"

mkdir -p "$ROOT"
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG" >&2; }

if [ -z "$PYTHON" ] || [ -z "$CURL" ]; then
  log "ERRO: Termux precisa ter python e curl instalados."
  exit 1
fi

# Stop the old supervisor and any orphaned CORE listener before replacing files.
OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null && [ "$OLD_PID" != "$$" ]; then
  log "encerrando supervisor anterior ($OLD_PID)"
  kill "$OLD_PID" 2>/dev/null || true
  sleep 2
  kill -9 "$OLD_PID" 2>/dev/null || true
fi
pkill -f '[p]ython.*core_server\.py' 2>/dev/null || true
sleep 1
pkill -9 -f '[p]ython.*core_server\.py' 2>/dev/null || true
rm -f "$PIDFILE"

# Download the full runtime graph to a staging directory. No partial graph is run.
CORE_FILES=(
  action.py ai.py android_core.py android_session.py android_tools.py
  anpes.py autonomy.py command.py component_registry.py config.py context.py
  conversation.py cortex.py entity.py entity_resolver.py entity_store.py
  intent.py interface.py knowledge.py memory.py mepo.py orchestration.py
  orchestrator.py response_guard.py stacy.py stacy_ecc.py tasks.py voice.py
  core_server.py
)
rm -rf "$STAGE"
mkdir -p "$STAGE"
log "sincronizando CORE oficial do GitHub"
for f in "${CORE_FILES[@]}"; do
  stamp="$(date +%s)"
  if ! "$CURL" -fsSL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 1 "$REPO_RAW/$f?ars=$stamp" -o "$STAGE/$f"; then
    log "ERRO ao baixar $f; atualização cancelada sem iniciar o CORE."
    rm -rf "$STAGE"
    exit 1
  fi
  if [ ! -s "$STAGE/$f" ]; then
    log "ERRO: arquivo vazio recebido para $f."
    rm -rf "$STAGE"
    exit 1
  fi
done

if ! "$PYTHON" -m py_compile "$STAGE"/*.py; then
  log "ERRO: py_compile falhou; CORE não iniciado."
  rm -rf "$STAGE"
  exit 1
fi

if ! (cd "$STAGE" && PYTHONPATH="$STAGE" "$PYTHON" - <<'PY'
import inspect
import orchestrator
import android_tools
import android_session
import component_registry
import stacy_ecc
params = inspect.signature(orchestrator.StacyOrchestrator.__init__).parameters
required = {"processar", "_processar_interno", "_registrar_resultado_conversa", "_usar_ai"}
missing = sorted(name for name in required if not hasattr(orchestrator.StacyOrchestrator, name))
if "phase_callback" not in params or missing:
    raise SystemExit(f"CORE incompatível: phase_callback={('phase_callback' in params)}, missing={missing}")
print("CORE import smoke test OK")
PY
); then
  log "ERRO: grafo/imports do CORE inválidos; CORE não iniciado."
  rm -rf "$STAGE"
  exit 1
fi

for f in "${CORE_FILES[@]}"; do
  cp "$STAGE/$f" "$ROOT/$f.tmp" || { log "ERRO ao preparar $f"; rm -rf "$STAGE"; exit 1; }
  mv "$ROOT/$f.tmp" "$ROOT/$f" || { log "ERRO ao aplicar $f"; rm -rf "$STAGE"; exit 1; }
done
rm -rf "$STAGE" "$ROOT/__pycache__"
find "$ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -name '*.pyc' -delete 2>/dev/null || true
export PYTHONPATH="$ROOT"

termux-wake-lock
echo "$$" > "$PIDFILE"
cleanup() { rm -f "$PIDFILE"; }
trap cleanup EXIT INT TERM
log "CORE sincronizado e validado; iniciando servidor HTTP"

while true; do
  HEALTH="$("$PYTHON" -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)); print("ok" if d.get("ok") is True and d.get("service") == "stacy-core" else "bad")' 2>/dev/null || true)"
  if [ "$HEALTH" = "ok" ]; then
    sleep 3
    continue
  fi
  "$PYTHON" "$ROOT/core_server.py" >> "$LOG" 2>&1 &
  CORE_PID=$!
  log "core_server.py iniciado (pid=$CORE_PID)"
  wait "$CORE_PID"
  STATUS=$?
  log "core_server.py terminou ($STATUS); verificando/reiniciando"
  sleep 2
done
