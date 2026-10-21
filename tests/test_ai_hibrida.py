import unittest
from unittest.mock import patch

import ai


class TestIAHibrida(unittest.TestCase):

    def setUp(self):
        self.historico = [
            {"role": "user", "parts": [{"text": "olá"}]}
        ]

    @patch("ai.gerar_resposta")
    @patch("ai.gerar_resposta_local")
    @patch("ai.verificar_ia_local")
    def test_prefere_ia_local(self, verificar, local, gemini):
        verificar.return_value = True
        local.return_value = "Resposta local."

        resultado = ai.gerar_resposta_hibrida(
            "chave",
            self.historico,
            "{}"
        )

        self.assertEqual(resultado["origem"], "local")
        self.assertFalse(resultado["fallback"])
        self.assertEqual(resultado["resposta"], "Resposta local.")
        gemini.assert_not_called()

    @patch("ai.gerar_resposta")
    @patch("ai.gerar_resposta_local")
    @patch("ai.verificar_ia_local")
    def test_faz_fallback_para_gemini(self, verificar, local, gemini):
        verificar.return_value = False
        gemini.return_value = "Resposta Gemini."

        resultado = ai.gerar_resposta_hibrida(
            "chave",
            self.historico,
            "{}"
        )

        self.assertEqual(resultado["origem"], "gemini")
        self.assertTrue(resultado["fallback"])
        self.assertEqual(resultado["resposta"], "Resposta Gemini.")
        local.assert_not_called()

    @patch("ai.gerar_resposta")
    @patch("ai.gerar_resposta_local")
    @patch("ai.verificar_ia_local")
    def test_falha_total_nao_inventa_resposta(self, verificar, local, gemini):
        verificar.return_value = False
        gemini.side_effect = RuntimeError("Gemini indisponível")

        with self.assertRaises(RuntimeError) as contexto:
            ai.gerar_resposta_hibrida(
                "chave",
                self.historico,
                "{}"
            )

        self.assertIn("Falha nos provedores de IA", str(contexto.exception))
        self.assertIn("servidor local não está acessível", str(contexto.exception))
        self.assertIn("Gemini indisponível", str(contexto.exception))


    @patch("ai.gerar_resposta")
    @patch("ai.gerar_resposta_local")
    @patch("ai.verificar_ia_local")
    def test_explains_missing_gemini_key_without_revealing_secrets(self, verificar, local, gemini):
        verificar.return_value = False
        gemini.side_effect = RuntimeError(
            "Chave da Gemini não configurada. No Termux, configure "
            "~/.stacy/secrets.json com GEMINI_API_KEY; não envie a chave no chat."
        )

        with self.assertRaises(RuntimeError) as contexto:
            ai.gerar_resposta_hibrida(None, self.historico, "{}")

        message = str(contexto.exception)
        self.assertIn("GEMINI_API_KEY", message)
        self.assertIn("servidor local não está acessível", message)
        self.assertNotIn("AIza", message)


if __name__ == "__main__":
    unittest.main()
