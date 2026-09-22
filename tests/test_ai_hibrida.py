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

        self.assertIn("não responderam corretamente", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
