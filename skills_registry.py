"""Deterministic discovery and selection of STACY skills.

This module deliberately contains no dynamic code execution. A skill is
metadata until the orchestrator explicitly maps it to a trusted executor.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_ROOT = ROOT / "skills"
_ALLOWED_RISKS = {"low", "medium", "high"}


def _parse_manifest(path: Path) -> dict:
    data = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("\"'")
        if key in {"name", "description", "risk"}:
            data[key] = value
    return data


def discover() -> list[dict]:
    """Return valid skill metadata in stable name order."""
    if not SKILLS_ROOT.exists():
        return []
    skills = []
    for directory in sorted(SKILLS_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        manifest = directory / "SKILL.md"
        if not manifest.is_file():
            continue
        try:
            data = _parse_manifest(manifest)
        except OSError:
            continue
        name = data.get("name", directory.name).strip()
        risk = data.get("risk", "low").lower().strip()
        if not name or risk not in _ALLOWED_RISKS:
            continue
        skills.append({
            "name": name,
            "description": data.get("description", "").strip(),
            "risk": risk,
            "path": str(manifest.relative_to(ROOT)),
        })
    return skills


def select(query: str, *, limit: int = 5) -> list[dict]:
    """Select skills by deterministic token overlap; never executes them."""
    if limit <= 0:
        return []
    tokens = set(re.findall(r"[a-z0-9áéíóúâêôãõç]+", (query or "").lower()))
    scored = []
    for skill in discover():
        text = f"{skill['name']} {skill['description']}".lower()
        score = sum(1 for token in tokens if len(token) >= 3 and token in text)
        if score:
            scored.append((score, skill["name"], skill))
    scored.sort(key=lambda item: (-item[0], item[1].lower()))
    return [item[2] for item in scored[:limit]]


def diagnostics() -> dict:
    skills = discover()
    return {
        "version": "skills-registry-1.0.0",
        "root": str(SKILLS_ROOT),
        "count": len(skills),
        "skills": skills,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(diagnostics(), ensure_ascii=False, indent=2))
