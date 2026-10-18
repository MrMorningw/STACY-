"""Runtime component registry for STACY CORE.

The registry is intentionally dependency-free so diagnostics still work when
an optional CORE component is unavailable. It reports facts from the current
checkout/process instead of claiming a component is healthy merely because a
file exists.
"""
from __future__ import annotations

import importlib.util
import socket
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMPONENTS = {
    "core": {"kind": "python", "path": "core_server.py"},
    "orchestrator": {"kind": "python", "path": "orchestrator.py"},
    "memory": {"kind": "python", "path": "memory.py"},
    "entities": {"kind": "python", "path": "entity_store.py"},
    "android_bridge": {"kind": "python", "path": "android_core.py"},
    "android_tools": {"kind": "python", "path": "android_tools.py"},
    "session": {"kind": "python", "path": "android_session.py"},
    "ecc_adaptation": {"kind": "python", "path": "stacy_ecc.py"},
    "skills_registry": {"kind": "python", "path": "skills_registry.py"},
    "verification_gate": {"kind": "python", "path": "verification_gate.py"},
    "agent_modes": {"kind": "python", "path": "agent_modes.py"},
    "ui": {"kind": "android", "path": "android/app/src/main/assets/stacy_prototipo36.html"},
    "updater": {"kind": "android", "path": "android/app/src/main/java/com/mrmorning/stacy/StacyUpdater.kt"},
}


def _python_importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _tcp_listening(host: str, port: int, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def snapshot() -> dict:
    components = {}
    for name, spec in COMPONENTS.items():
        path = ROOT / spec["path"]
        exists = path.exists()
        importable = True
        if spec["kind"] == "python" and name not in {"core"}:
            importable = _python_importable(path.stem) if exists else False
        healthy = exists and importable
        components[name] = {
            "name": name,
            "kind": spec["kind"],
            "path": spec["path"],
            "present": exists,
            "healthy": healthy,
            "status": "online" if healthy else "offline",
        }

    daemon = _tcp_listening("127.0.0.1", 8765)
    components["core"]["healthy"] = daemon
    components["core"]["status"] = "online" if daemon else "offline"

    ecc = None
    if components["ecc_adaptation"]["healthy"]:
        try:
            import stacy_ecc
            ecc = stacy_ecc.diagnostics()
        except Exception as exc:
            components["ecc_adaptation"]["healthy"] = False
            components["ecc_adaptation"]["status"] = "error"
            components["ecc_adaptation"]["error"] = f"{type(exc).__name__}: {exc}"

    skills = None
    if components["skills_registry"]["healthy"]:
        try:
            import skills_registry
            skills = skills_registry.diagnostics()
        except Exception as exc:
            components["skills_registry"]["healthy"] = False
            components["skills_registry"]["status"] = "error"
            components["skills_registry"]["error"] = f"{type(exc).__name__}: {exc}"

    agent_modes = None
    if components["agent_modes"]["healthy"]:
        try:
            import agent_modes
            agent_modes = agent_modes.diagnostics()
        except Exception as exc:
            components["agent_modes"]["healthy"] = False
            components["agent_modes"]["status"] = "error"
            components["agent_modes"]["error"] = f"{type(exc).__name__}: {exc}"

    return {
        "registryVersion": "1.3.0",
        "generatedAt": time.time(),
        "root": str(ROOT),
        "core": {"host": "127.0.0.1", "port": 8765, "online": daemon},
        "components": components,
        "eccAdaptation": ecc,
        "skills": skills,
        "agentModes": agent_modes,
    }


def render_status() -> str:
    data = snapshot()
    online = sum(1 for c in data["components"].values() if c["healthy"])
    total = len(data["components"])
    lines = [f"STACY CORE — {online}/{total} componentes saudáveis."]
    if data.get("skills"):
        lines.append(f"• skills: {data['skills']['count']} descobertas")
    if data.get("agentModes"):
        lines.append(f"• modos de agente: {len(data['agentModes']['modes'])}")
    for name, component in data["components"].items():
        lines.append(f"• {name}: {component['status']} — {component['path']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
