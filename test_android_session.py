import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from android_session import load_api_key, exclusive_session_lock, persist_session, restore_session
from conversation import ConversationState


class FakeOrchestrator:
    def __init__(self):
        self.historico = []
        self.acao_pendente = None
        self.ultima_decisao = None
        self.entidade_contextual = None
        self.conversa = ConversationState()


class AndroidSessionTests(unittest.TestCase):
    def test_pending_action_and_conversation_survive_process_restart(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"STACY_STATE_DIR": directory}, clear=False
        ):
            with exclusive_session_lock():
                first = FakeOrchestrator()
                first.acao_pendente = {"tipo": "remover_tarefa", "tarefa_id": "task-123"}
                first.conversa.registrar_mensagem("remova a tarefa")
                first.conversa.registrar_intencao_pendente({"tipo": "tarefa"})
                persist_session(first)

                restored = FakeOrchestrator()
                self.assertIsNone(restore_session(restored))
                self.assertEqual(restored.acao_pendente, first.acao_pendente)
                self.assertEqual(
                    restored.conversa.ultima_mensagem,
                    "remova a tarefa",
                )
                self.assertEqual(
                    restored.conversa.obter_intencao_pendente(),
                    {"tipo": "tarefa"},
                )

    def test_corrupt_state_is_quarantined_and_not_reused(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"STACY_STATE_DIR": directory}, clear=False
        ):
            path = Path(directory, "session.json")
            path.write_text(
                json.dumps({"schema_version": 999, "acao_pendente": {"tipo": "remover"}}),
                encoding="utf-8",
            )
            orchestrator = FakeOrchestrator()
            warning = restore_session(orchestrator)
            self.assertIn("inválido", warning)
            self.assertIsNone(orchestrator.acao_pendente)
            self.assertFalse(path.exists())
            self.assertTrue(list(Path(directory).glob("session.corrupt.*.json")))

    def test_invalid_private_key_config_does_not_break_local_core(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"STACY_STATE_DIR": directory}, clear=False
        ):
            os.environ.pop("GEMINI_API_KEY", None)
            Path(directory, "secrets.json").write_text("{not-json", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertIsNone(load_api_key())
            self.assertIn("recursos locais continuarão disponíveis", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
