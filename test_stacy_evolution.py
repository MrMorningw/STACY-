"""Regression tests for the STACY evolution layer."""
from __future__ import annotations

import agent_modes
import skills_registry
import verification_gate


def test_skill_discovery_is_deterministic():
    skills = skills_registry.discover()
    names = [skill["name"] for skill in skills]
    assert names == sorted(names, key=str.lower)
    assert {"research", "verification", "memory", "android", "automation", "engineering"}.issubset(names)


def test_skill_selection_never_executes_code():
    selected = skills_registry.select("pesquisa e verificação")
    assert selected
    assert all("path" in skill for skill in selected)


def test_verification_rejects_empty_response():
    report = verification_gate.verify_result({"tipo": "resposta", "resposta": ""})
    assert not report.ok
    assert report.status == "failed"
    assert "resposta vazia" in report.issues


def test_verification_accepts_valid_result():
    report = verification_gate.verify_result({
        "tipo": "resposta",
        "resposta": "ok",
        "fontes": [{"url": "https://example.com"}],
    })
    assert report.ok
    assert report.status == "verified"


def test_verification_converts_operation_exception_to_failure():
    def broken_operation():
        raise RuntimeError("boom")

    result, report = verification_gate.run_with_verification(broken_operation)
    assert result is None
    assert not report.ok
    assert report.status == "exception"


def test_high_risk_actions_are_controlled():
    mode = agent_modes.resolve("tarefa", action=True, risk="high")
    assert mode.name == "controlled"
    assert mode.requires_confirmation
