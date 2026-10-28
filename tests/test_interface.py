import unittest
from unittest.mock import patch

import interface


class TestConsoleInterface(unittest.TestCase):
    def test_interface_is_text_only_and_has_no_android_capabilities(self):
        status = interface.ConsoleInterface().status()
        self.assertFalse(status.voz_entrada)
        self.assertFalse(status.voz_saida)
        self.assertFalse(status.notificacoes)
        self.assertFalse(status.alguma_capacidade_android)

    def test_voice_request_fails_explicitly_without_launching_a_process(self):
        ui = interface.ConsoleInterface()
        with patch("subprocess.run") as runner:
            with self.assertRaisesRegex(RuntimeError, "modo texto"):
                ui.ouvir()
            runner.assert_not_called()

    def test_speech_and_notifications_are_not_external_side_effects(self):
        ui = interface.ConsoleInterface()
        with patch("subprocess.run") as runner:
            self.assertFalse(ui.falar("Olá, senhor."))
            self.assertFalse(ui.notificar("STACY", "Tarefa concluída."))
            runner.assert_not_called()

    def test_default_mode_is_always_text(self):
        with patch.dict("os.environ", {"STACY_INTERFACE": "voz"}, clear=True):
            self.assertEqual(interface.modo_interface_padrao(), "texto")
        with patch.dict("os.environ", {"STACY_INTERFACE": "invalido"}, clear=True):
            self.assertEqual(interface.modo_interface_padrao(), "texto")


if __name__ == "__main__":
    unittest.main()
