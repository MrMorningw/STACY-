import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import android_core
from conversation import ConversationState
from android_session import load_api_key


class AndroidCoreEntryPointTests(unittest.TestCase):
    def _run(self, message, state_dir, result=None, raised=None):
        fake_memory = types.SimpleNamespace(carregar_memoria=lambda: {"usuario": {}})
        fake_entities = types.SimpleNamespace(carregar_entidades=lambda: {"entidades": []})

        class FakeOrchestrator:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.historico = []
                self.acao_pendente = None
                self.ultima_decisao = None
                self.entidade_contextual = None
                self.conversa = ConversationState()

            def processar(self, text):
                if raised is not None:
                    raise raised
                self.historico.append({"role": "user", "parts": [{"text": text}]})
                self.conversa.registrar_mensagem(text)
                print("diagnóstico interno que não pode contaminar stdout")
                return result if result is not None else {
                    "tipo": "local",
                    "resposta": f"Recebido: {text}",
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
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {"STACY_STATE_DIR": state_dir}):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = android_core.main([message])
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_success_writes_one_json_line_to_stdout(self):
        with tempfile.TemporaryDirectory() as state_dir:
            exit_code, stdout, stderr = self._run("oi", state_dir)
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(stdout.splitlines()), 1)
            self.assertEqual(json.loads(stdout), {
                "tipo": "local",
                "resposta": "Recebido: oi",
            })
            self.assertIn("diagnóstico interno", stderr)
            state = json.loads((Path(state_dir) / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(state["historico"][0]["parts"][0]["text"], "oi")

    def test_session_history_survives_separate_process_calls(self):
        with tempfile.TemporaryDirectory() as state_dir:
            self._run("primeira", state_dir)
            self._run("segunda", state_dir)
            state = json.loads((Path(state_dir) / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [item["parts"][0]["text"] for item in state["historico"]],
                ["primeira", "segunda"],
            )
            self.assertEqual(
                [item["conteudo"] for item in state["conversa"]["historico"]],
                ["primeira", "segunda"],
            )

    def test_core_exception_returns_safe_json_error(self):
        with tempfile.TemporaryDirectory() as state_dir:
            exit_code, stdout, stderr = self._run(
                "oi", state_dir, raised=RuntimeError("detalhe interno privado")
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["tipo"], "erro")
            self.assertIn("interrompida com segurança", payload["resposta"])
            self.assertNotIn("detalhe interno privado", stdout)
            self.assertIn("detalhe interno privado", stderr)

    def test_api_key_environment_takes_precedence_over_private_file(self):
        with tempfile.TemporaryDirectory() as state_dir:
            Path(state_dir, "secrets.json").write_text(
                json.dumps({"GEMINI_API_KEY": "file-key"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {"STACY_STATE_DIR": state_dir, "GEMINI_API_KEY": "env-key"}):
                self.assertEqual(load_api_key(), "env-key")

    def test_api_key_can_be_loaded_from_private_file(self):
        with tempfile.TemporaryDirectory() as state_dir:
            Path(state_dir, "secrets.json").write_text(
                json.dumps({"GEMINI_API_KEY": "local-key"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {"STACY_STATE_DIR": state_dir}, clear=False):
                os.environ.pop("GEMINI_API_KEY", None)
                self.assertEqual(load_api_key(), "local-key")

    def test_empty_input_returns_json_error(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = android_core.main(["  "])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["tipo"], "erro")


if __name__ == "__main__":
    unittest.main()
