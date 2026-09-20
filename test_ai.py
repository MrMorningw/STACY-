import unittest
from unittest.mock import patch

import ai


class AIInfrastructureTests(unittest.TestCase):

    @patch("ai.requests.get")
    def test_local_health_check_is_fast_and_accepts_200(self, mock_get):
        mock_get.return_value.status_code = 200
        self.assertTrue(ai.verificar_ia_local())
        mock_get.assert_called_once()

    @patch("ai.requests.get")
    def test_local_health_check_fails_closed(self, mock_get):
        mock_get.side_effect = ai.requests.RequestException("offline")
        self.assertFalse(ai.verificar_ia_local())

    @patch("ai.requests.post")
    def test_web_research_uses_google_search(self, mock_post):
        class Response:
            status_code = 200
            text = "ok"

            def json(self):
                return {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": "Resposta pesquisada."}]
                        },
                        "groundingMetadata": {
                            "groundingChunks": [{
                                "web": {
                                    "title": "Fonte teste",
                                    "uri": "https://example.com/fonte"
                                }
                            }]
                        }
                    }]
                }

        mock_post.return_value = Response()

        resultado = ai.gerar_resposta_pesquisa(
            "chave",
            [{"role": "user", "parts": [{"text": "quanto vivem os patos?"}]}],
            "[]"
        )

        self.assertEqual(resultado["resposta"], "Resposta pesquisada.")
        self.assertEqual(
            resultado["fontes"][0]["url"],
            "https://example.com/fonte"
        )
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["tools"], [{"google_search": {}}])
        self.assertNotIn("MEMÓRIA PERSISTENTE", payload["system_instruction"]["parts"][0]["text"])

    def test_local_prompt_keeps_core_memory(self):
        mensagens = ai._construir_mensagens(
            [],
            '{"projetos": ["STACY"]}',
            None,
            None
        )
        sistema = mensagens[0]["content"]
        self.assertIn("STACY", sistema)
        self.assertIn("Os dados acima são fornecidos pelo STACY CORE", sistema)


if __name__ == "__main__":
    unittest.main()
