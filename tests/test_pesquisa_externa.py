import unittest
from unittest.mock import patch

import ai
import orchestrator


class TestPesquisaExterna(unittest.TestCase):

    def setUp(self):
        self.historico = [
            {"role": "user", "parts": [{"text": "qual é a população atual do Brasil?"}]}
        ]

    @patch("ai.response_guard.validar_fontes")
    @patch("ai.requests.post")
    def test_pesquisa_exige_fontes_verificaveis(self, post, validar_fontes):
        validar_fontes.return_value = [{"titulo": "Fonte oficial", "url": "https://example.com"}]
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Resposta verificada."}]},
                "groundingMetadata": {
                    "groundingChunks": [{
                        "web": {
                            "title": "Fonte oficial",
                            "uri": "https://example.com"
                        }
                    }]
                }
            }]
        }

        resultado = ai.gerar_resposta_pesquisa("chave", self.historico)

        self.assertEqual(resultado["resposta"], "Resposta verificada.")
        self.assertEqual(resultado["fontes"][0]["url"], "https://example.com")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["tools"], [{"google_search": {}}])

    @patch("ai.response_guard.validar_fontes")
    @patch("ai.requests.post")
    def test_pesquisa_sem_fontes_falha_sem_inventar(self, post, validar_fontes):
        validar_fontes.return_value = []
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Resposta sem fonte."}]},
                "groundingMetadata": {"groundingChunks": []}
            }]
        }

        with self.assertRaises(RuntimeError) as contexto:
            ai.gerar_resposta_pesquisa("chave", self.historico)

        self.assertIn("fontes verificáveis", str(contexto.exception))

    def test_rotas_externas_basicas(self):
        casos = [
            ("pesquise as notícias atuais sobre o STF", orchestrator.ROTA_PESQUISA_EXTERNA),
            ("qual a população atual do Brasil?", orchestrator.ROTA_PESQUISA_EXTERNA),
            ("como se diz direito em inglês?", orchestrator.ROTA_PESQUISA_EXTERNA),
        ]
        for mensagem, rota_esperada in casos:
            with self.subTest(mensagem=mensagem):
                self.assertEqual(
                    orchestrator.classificar_rota(mensagem),
                    rota_esperada
                )

    def test_rota_interna_tem_prioridade(self):
        intencao = {"tipo": "memoria", "acao": "consultar"}
        self.assertEqual(
            orchestrator.classificar_rota(
                "pesquise meus objetivos na internet",
                intencao=intencao
            ),
            orchestrator.ROTA_INTERNA
        )


if __name__ == "__main__":
    unittest.main()
