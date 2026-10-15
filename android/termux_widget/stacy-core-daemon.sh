#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="${HOME}/stacy"
LOG="${ROOT}/stacy-core-daemon.log"
PIDFILE="${ROOT}/.stacy-core.pid"
PYTHON="$(command -v python || true)"

mkdir -p "$ROOT"

if [ -z "$PYTHON" ]; then
  echo "STACY CORE: Python não encontrado no Termux." >&2
  exit 1
fi

cd "$ROOT" || exit 1

echo "$$" > "$PIDFILE"
cleanup() { rm -f "$PIDFILE"; }
trap cleanup EXIT INT TERM

while true; do
  if ! curl -fsS --max-time 1 http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo "[$(date '+%F %T')] iniciando core_server.py" >> "$LOG"
    "$PYTHON" "$ROOT/core_server.py" >> "$LOG" 2>&1 &
    CORE_PID=$!
    wait "$CORE_PID"
    STATUS=$?
    echo "[$(date '+%F %T')] core_server.py terminou ($STATUS); reiniciando" >> "$LOG"
    sleep 1
  else
    sleep 2
  fi
done
