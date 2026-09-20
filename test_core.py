import unittest

import intent
import orchestrator


class CoreRoutingTests(unittest.TestCase):

    def setUp(self):
        self.memoria = {
            "usuario": {"nome": "Danley"},
            "preferencias": [],
            "projetos": [{"id": "P-A1", "valor": "STACY"}],
            "objetivos": [{"id": "O-A1", "valor": "aprender ingles"}],
            "informacoes": []
        }
        self.entidades = {"entidades": []}
        self.orquestrador = orchestrator.StacyOrchestrator(
            api_key=None,
            memoria=self.memoria,
            entidades=self.entidades
        )

        def ai_nao_deve_ser_chamada(_):
            self.fail("Uma consulta estruturada caiu na IA.")

        self.orquestrador._usar_ai = ai_nao_deve_ser_chamada

    def test_greeting_with_punctuation_is_local(self):
        resultado = self.orquestrador.processar("como voce esta?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("operando normalmente", resultado["resposta"])

    def test_local_greeting_is_registered_in_conversation(self):
        self.orquestrador.processar("oi stacy")
        self.assertEqual(
            self.orquestrador.conversa.obter_ultima_mensagem(),
            "oi stacy"
        )

    def test_greeting_accent_is_local(self):
        resultado = self.orquestrador.processar("Olá STACY?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("pronta", resultado["resposta"])

    def test_projects_query_uses_core(self):
        resultado = self.orquestrador.processar("quais sao os meus projetos ?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("STACY", resultado["resposta"])
        self.assertNotIn("CSD", resultado["resposta"])

    def test_objectives_query_uses_core(self):
        resultado = self.orquestrador.processar("quais sao os meus objetivos ?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("aprender ingles", resultado["resposta"])

    def test_objectives_query_does_not_collide_with_projects(self):
        resultado = intent.interpretar("quais sao os meus objetivos ?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "objetivos")

    def test_tasks_query_with_punctuation_is_structured(self):
        original_listar = orchestrator.tasks.listar