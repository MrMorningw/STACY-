#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="${HOME}/stacy"
REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
LOG="${ROOT}/stacy-core-daemon.log"
PIDFILE="${ROOT}/.stacy-core-daemon.pid"
VERSION_MARKER="${ROOT}/.stacy-core-app-version"
START_LOCK="${ROOT}/.stacy-core-start.lock"
PYTHON="$(command -v python || true)"
CURL="$(command -v curl || true)"
STAGE="${ROOT}/.stacy-core-sync.$$"
APP_VERSION_CODE=""

for arg in "$@"; do
  case "$arg" in
    --app-version-code=*) APP_VERSION_CODE="${arg#*=}" ;;
  esac
done

mkdir -p "$ROOT"
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG" >&2; }

if [ -z "$PYTHON" ] || [ -z "$CURL" ]; then
  log "ERRO: Termux precisa ter python e curl instalados."
  exit 1
fi

core_health() {
  "$PYTHON" -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)); print("ok" if d.get("ok") is True and d.get("service") == "stacy-core" else "bad")' 2>/dev/null || true
}

HEALTH="$(core_health)"
CURRENT_APP_VERSION="$(cat "$VERSION_MARKER" 2>/dev/null || true)"
if [ "$HEALTH" = "ok" ] && [ -n "$APP_VERSION_CODE" ] && [ "$CURRENT_APP_VERSION" = "$APP_VERSION_CODE" ]; then
  log "CORE já está saudável para o aplicativo código $APP_VERSION_CODE; mantendo o processo atual."
  exit 0
fi

# If the same release is already starting, don't kill it or launch a competing sync.
OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null && [ "$CURRENT_APP_VERSION" = "$APP_VERSION_CODE" ]; then
  log "another CORE startup is already running; preserving the active supervisor."
  exit 0
fi

# Atomic startup lock: two Activity launches must never synchronize over each other.
if ! mkdir "$START_LOCK" 2>/dev/null; then
  LOCK_PID="$(cat "$START_LOCK/pid" 2>/dev/null || true)"
  if [[ "$LOCK_PID" =~ ^[0-9]+$ ]] && kill -0 "$LOCK_PID" 2>/dev/null; then
    log "another CORE startup is already running; this launch will reuse it."
    exit 0
  fi
  rm -rf "$START_LOCK"
  if ! mkdir "$START_LOCK" 2>/dev/null; then
    log "CORE startup lock is busy; refusing a parallel synchronization."
    exit 0
  fi
fi
echo "$$" > "$START_LOCK/pid"
trap 'rm -rf "$START_LOCK"' EXIT INT TERM

# Only a release-version change or a dead supervisor may replace the runtime.
OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null && [ "$OLD_PID" != "$$" ]; then
  log "updating CORE for app code $APP_VERSION_CODE; stopping previous supervisor ($OLD_PID)"
  kill "$OLD_PID" 2>/dev/null || true
  sleep 2
  if kill -0 "$OLD_PID" 2>/dev/null; then kill -9 "$OLD_PID" 2>/dev/null || true; fi
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
  agent_modes.py skills_registry.py verification_gate.py core_server.py
  skills/README.md
  skills/android/SKILL.md skills/automation/SKILL.md
  skills/engineering/SKILL.md skills/memory/SKILL.md
  skills/research/SKILL.md skills/verification/SKILL.md
)
rm -rf "$STAGE"
mkdir -p "$STAGE"
log "sincronizando CORE oficial do GitHub"
for f in "${CORE_FILES[@]}"; do
  mkdir -p "$(dirname "$STAGE/$f")"
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
import agent_modes
import skills_registry
import verification_gate
params = inspect.signature(orchestrator.StacyOrchestrator.__init__).parameters
required = {"processar", "_processar_interno", "_registrar_resultado_conversa", "_usar_ai"}
missing = sorted(name for name in required if not hasattr(orchestrator.StacyOrchestrator, name))
if "phase_callback" not in params or missing:
    raise SystemExit(f"CORE incompatível: phase_callback={('phase_callback' in params)}, missing={missing}")
if len(skills_registry.discover()) < 6:
    raise SystemExit("CORE incompatível: conjunto de Skills incompleto")
if not verification_gate.verify_result({"tipo": "resposta", "resposta": "ok"}).ok:
    raise SystemExit("CORE incompatível: Verification Gate não passou no smoke test")
if len(agent_modes.diagnostics().get("modes", [])) != 3:
    raise SystemExit("CORE incompatível: Agent Modes incompletos")
print("CORE import/skills/verification smoke test OK")
PY
); then
  log "ERRO: grafo/imports do CORE inválidos; CORE não iniciado."
  rm -rf "$STAGE"
  exit 1
fi

for f in "${CORE_FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$f")" || { log "ERRO ao criar diretório para $f"; rm -rf "$STAGE"; exit 1; }
  cp "$STAGE/$f" "$ROOT/$f.tmp" || { log "ERRO ao preparar $f"; rm -rf "$STAGE"; exit 1; }
  mv "$ROOT/$f.tmp" "$ROOT/$f" || { log "ERRO ao aplicar $f"; rm -rf "$STAGE"; exit 1; }
done
if [[ "$APP_VERSION_CODE" =~ ^[0-9]+$ ]]; then
  printf '%s\n' "$APP_VERSION_CODE" > "$VERSION_MARKER.tmp"
  mv "$VERSION_MARKER.tmp" "$VERSION_MARKER"
fi
rm -rf "$STAGE" "$ROOT/__pycache__"
find "$ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -name '*.pyc' -delete 2>/dev/null || true
export PYTHONPATH="$ROOT"

termux-wake-lock
echo "$$" > "$PIDFILE"
cleanup() { rm -f "$PIDFILE"; rm -rf "$START_LOCK"; }
trap cleanup EXIT INT TERM
log "CORE sincronizado e validado; iniciando servidor HTTP"

while true; do
  HEALTH="$(core_health)"
  if [ "$HEALTH" = "ok" ]; then
    rm -rf "$START_LOCK"
    sleep 3
    continue
  fi
  "$PYTHON" "$ROOT/core_server.py" >> "$LOG" 2>&1 &
  CORE_PID=$!
  log "core_server.py iniciado (pid=$CORE_PID)"
  # Keep the startup lock until the HTTP health endpoint confirms readiness.
  for ((attempt=0; attempt<40; attempt++)); do
    HEALTH="$(core_health)"
    if [ "$HEALTH" = "ok" ]; then
      rm -rf "$START_LOCK"
      break
    fi
    if ! kill -0 "$CORE_PID" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done
  wait "$CORE_PID"
  STATUS=$?
  log "core_server.py terminou ($STATUS); verificando/reiniciando"
  sleep 2
done
