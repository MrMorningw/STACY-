#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="${HOME}/stacy"
LOG="${ROOT}/stacy-core-daemon.log"
PIDFILE="${ROOT}/.stacy-core-daemon.pid"
PYTHON="$(command -v python || true)"

mkdir -p "$ROOT"
if [ -z "$PYTHON" ]; then
  echo "STACY CORE: Python não encontrado no Termux." >&2
  exit 1
fi

# Idempotent start: opening STACY repeatedly must not create supervisors.
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0
  fi
  rm -f "$PIDFILE"
fi

echo "$$" > "$PIDFILE"
cleanup() { rm -f "$PIDFILE"; }
trap cleanup EXIT INT TERM

cd "$ROOT" || exit 1
while true; do
  if "$PYTHON" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1).read()' >/dev/null 2>&1; then
    sleep 3
    continue
  fi
  echo "[$(date '+%F %T')] iniciando core_server.py" >> "$LOG"
  "$PYTHON" "$ROOT/core_server.py" >> "$LOG" 2>&1 &
  CORE_PID=$!
  wait "$CORE_PID"
  STATUS=$?
  echo "[$(date '+%F %T')] core_server.py terminou ($STATUS); reiniciando" >> "$LOG"
  sleep 1
done
