import unittest
from unittest.mock import patch

import interface


class TestAndroidInterface(unittest.TestCase):

    def test_status_sem_termux_api(self):
        with patch.object(interface.shutil, "which", return_value=None):
            status = interface.AndroidInterface().status()

        self.assertFalse(status.voz_entrada)
        self.assertFalse(status.voz_saida)
        self.assertFalse(status.notificacoes)
        self.assertFalse(status.alguma_capacidade_android)

    def test_entrada_por_voz_executa_comando_e_retorna_texto(self):
        processo = interface.subprocess.CompletedProcess(
            ["termux-speech-to-text"], 0, "crie uma tarefa estudar direito\n", ""
        )
        runner = unittest.mock.Mock(return_value=processo)

        with patch.object(interface.shutil, "which", return_value="/usr/bin/termux-speech-to-text"):
            texto = interface.AndroidInterface(runner=runner).ouvir()

        self.assertEqual(texto, "crie uma tarefa estudar direito")
        runner.assert_called_once()
        self.assertEqual(runner.call_args.args[0], ["termux-speech-to-text"])

    def test_entrada_por_voz_indisponivel_nao_quebra_o_core(self):
        with patch.object(interface.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError):
                interface.AndroidInterface().ouvir()

    def test_saida_por_voz_e_notificacao_sao_adaptadores_opcionais(self):
        processo = interface.subprocess.CompletedProcess([], 0, "", "")
        runner = unittest.mock.Mock(return_value=processo)

        def disponivel(nome):
            return f"/usr/bin/{nome}"

        with patch.object(interface.shutil, "which", side_effect=disponivel):
            ui = interface.AndroidInterface(runner=runner)
            self.assertTrue(ui.falar("Olá, senhor."))
            self.assertTrue(ui.notificar("STACY", "Tarefa concluída."))

        self.assertEqual(runner.call_count, 2)
        self.assertEqual(
            runner.call_args_list[0].args[0],
            ["termux-tts-speak", "Olá, senhor."],
        )
        self.assertEqual(
            runner.call_args_list[1].args[0],
            ["termux-notification", "--title", "STACY", "--content", "Tarefa concluída."],
        )

    def test_modo_interface_padrao_e_controlado(self):
        with patch.dict(interface.os.environ, {}, clear=True):
            self.assertEqual(interface.modo_interface_padrao(), "texto")
        with patch.dict(interface.os.environ, {"STACY_INTERFACE": "voz"}, clear=True):
            self.assertEqual(interface.modo_interface_padrao(), "voz")
        with patch.dict(interface.os.environ, {"STACY_INTERFACE": "invalido"}, clear=True):
            self.assertEqual(interface.modo_interface_padrao(), "texto")


if __name__ == "__main__":
    unittest.main()
