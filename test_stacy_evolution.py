"""Regression tests for the STACY evolution layer."""
from __future__ import annotations

import unittest

import agent_modes
import skills_registry
import verification_gate


class StacyEvolutionTests(unittest.TestCase):
    def test_skill_discovery_is_deterministic(self):
        skills = skills_registry.discover()
        names = [skill["name"] for skill in skills]
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertTrue({"research", "verification", "memory", "android", "automation", "engineering"}.issubset(names))

    def test_skill_selection_never_executes_code(self):
        selected = skills_registry.select("pesquisa e verificação")
        self.assertTrue(selected)
        self.assertTrue(all("path" in skill for skill in selected))

    def test_verification_rejects_empty_response(self):
        report = verification_gate.verify_result({"tipo": "resposta", "resposta": ""})
        self.assertFalse(report.ok)
        self.assertEqual(report.status, "failed")
        self.assertIn("resposta vazia", report.issues)

    def test_verification_accepts_valid_result(self):
        report = verification_gate.verify_result({
            "tipo": "resposta",
            "resposta": "ok",
            "fontes": [{"url": "https://example.com"}],
        })
        self.assertTrue(report.ok)
        self.assertEqual(report.status, "verified")

    def test_verification_converts_operation_exception_to_failure(self):
        def broken_operation():
            raise RuntimeError("boom")

        result, report = verification_gate.run_with_verification(broken_operation)
        self.assertIsNone(result)
        self.assertFalse(report.ok)
        self.assertEqual(report.status, "exception")

    def test_high_risk_actions_are_controlled(self):
        mode = agent_modes.resolve("tarefa", action=True, risk="high")
        self.assertEqual(mode.name, "controlled")
        self.assertTrue(mode.requires_confirmation)


if __name__ == "__main__":
    unittest.main()
