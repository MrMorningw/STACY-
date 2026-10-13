import contextlib
import io
import json
import sys
import types
import unittest
from unittest.mock import patch

import android_core


class AndroidCoreEntryPointTests(unittest.TestCase):
    def _run(self, message, result=None, raised=None):
        fake_memory = types.SimpleNamespace(carregar_memoria=lambda: {"usuario": {}})
        fake_entities = types.SimpleNamespace(carregar_entidades=lambda: {"entidades": []})

        class FakeOrchestrator:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def processar(self, text):
                if raised is not None:
                    raise raised
                print("diagnóstico interno que não pode contaminar stdout")
                return result if result is not None else {
                    "tipo": "local",
                    "resposta": "Núcleo operacional",
                }

        fake_orchestrator = types.ModuleType("orchestrator")
        fake_orchestrator.StacyOrchestrator = FakeOrchestrator
        stdout = io.StringIO()
        stderr = io.StringIO()
        modules = {
            "memory": fake_memory,
            "entity_store": fake_entities,
            "orchestrator": fake_orchestrator,
        }
        with patch.dict(sys.modules, modules):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = android_core.main([message])
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_success_writes_one_json_line_to_stdout(self):
        exit_code, stdout, stderr = self._run("oi")
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(json.loads(stdout), {
            "tipo": "local",
            "resposta": "Núcleo operacional",
        })
        self.assertIn("diagnóstico interno", stderr)

    def test_core_exception_returns_json_error(self):
        exit_code, stdout, _ = self._run("oi", raised=RuntimeError("falha simulada"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["tipo"], "erro")
        self.assertIn("falha simulada", json.loads(stdout)["resposta"])

    def test_empty_input_returns_json_error(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = android_core.main(["  "])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["tipo"], "erro")


if __name__ == "__main__":
    unittest.main()
