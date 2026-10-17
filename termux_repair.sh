#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/MrMorningw/STACY-/main"
ROOT="$HOME/stacy"

mkdir -p "$ROOT"
cd "$ROOT"

# Always synchronize the authoritative CORE runtime files from main.
for f in core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py; do
  echo "[STACY ARS] sincronizando $f"
  curl -fsSL "$REPO_RAW/$f" -o "$f"
done

# Force the CORE to load the orchestrator.py that was just downloaded into
# ~/stacy. This avoids a stale/conflicting Python module elsewhere on the
# Termux import path being selected as `orchestrator`.
python - <<'PY'
from pathlib import Path
p = Path("core_server.py")
s = p.read_text(encoding="utf-8")
old = "from orchestrator import StacyOrchestrator"
new = '''import importlib.util\n            orchestrator_path = ROOT / "orchestrator.py"\n            spec = importlib.util.spec_from_file_location("stacy_orchestrator", orchestrator_path)\n            if spec is None or spec.loader is None:\n                raise ImportError(f"Não foi possível carregar {orchestrator_path}")\n            orchestrator_module = importlib.util.module_from_spec(spec)\n            spec.loader.exec_module(orchestrator_module)\n            StacyOrchestrator = orchestrator_module.StacyOrchestrator'''
if old not in s:
    raise SystemExit("[STACY ARS] ERRO: ponto de import do orchestrator.py não encontrado")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("[STACY ARS] import do orchestrator fixado para ~/stacy/orchestrator.py")
PY

# Verify the runtime before starting it.
python -m py_compile core_server.py orchestrator.py android_session.py stacy_ecc.py entity_store.py memory.py ai.py config.py

python - <<'PY'
import inspect
from pathlib import Path
import importlib.util
path = Path.cwd() / "orchestrator.py"
spec = importlib.util.spec_from_file_location("stacy_orchestrator_check", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
params = inspect.signature(module.StacyOrchestrator.__init__).parameters
if "phase_callback" not in params:
    raise SystemExit("[STACY ARS] ERRO: ~/stacy/orchestrator.py incompatível: phase_callback ausente")
print("[STACY ARS] ~/stacy/orchestrator.py compatível: phase_callback OK")
PY

# Stop any stale/failed STACY CORE occupying port 8765 before starting the
# repaired instance. Do not touch unrelated Termux processes.
pkill -f "$ROOT/core_server.py" 2>/dev/null || true
sleep 1

termux-wake-lock
exec python core_server.py
