"""Controlled agent modes for STACY orchestration."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentMode:
    name: str
    purpose: str
    autonomous: bool
    requires_confirmation: bool


MODES = {
    "controlled": AgentMode(
        "controlled",
        "ações determinísticas e previsíveis",
        False,
        True,
    ),
    "smart": AgentMode(
        "smart",
        "planejamento assistido para tarefas de baixo risco",
        False,
        False,
    ),
    "agent": AgentMode(
        "agent",
        "planejamento multi-etapas com ferramentas autorizadas",
        True,
        True,
    ),
}


def resolve(intent_type: str | None, *, action: bool = False, risk: str = "low") -> AgentMode:
    """Choose a mode conservatively; privileged/high-risk work stays controlled."""
    if action or str(risk).lower() == "high":
        return MODES["controlled"]
    if str(intent_type).lower() in {"tarefa", "acao", "planejamento", "complexa"}:
        return MODES["agent"]
    return MODES["smart"]


def diagnostics() -> dict:
    return {
        "version": "agent-modes-1.0.0",
        "modes": [
            {
                "name": mode.name,
                "purpose": mode.purpose,
                "autonomous": mode.autonomous,
                "requires_confirmation": mode.requires_confirmation,
            }
            for mode in MODES.values()
        ],
    }
