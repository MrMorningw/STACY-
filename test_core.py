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

    def test_projects_query_uses_core(self):
        resultado = self.orquestrador.processar("quais sao os meus projetos ?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("STACY", resultado["resposta"])
        self.assertNotIn("CSD", resultado["resposta"])

    def test_objectives_query_uses_core(self):
        resultado = self.orquestrador.processar("quais sao os meus objetivos ?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("aprender ingles", resultado["resposta"])

    def test_tasks_query_with_punctuation_is_structured(self):
        original_listar = orchestrator.tasks.listar
        try:
            orchestrator.tasks.listar = lambda data=None: [
                {
                    "id": "T-1",
                    "titulo": "estudar direito",
                    "data": None,
                    "hora": None,
                    "status": "pendente"
                }
            ]
            resultado = self.orquestrador.processar(
                "quais sao as minhas tarefas ?"
            )
        finally:
            orchestrator.tasks.listar = original_listar

        self.assertEqual(resultado["tipo"], "tarefas")
        self.assertIn("estudar direito", resultado["resposta"])

    def test_exit_with_punctuation_is_command(self):
        resultado = self.orquestrador.processar("sair?")
        self.assertEqual(resultado["tipo"], "sair")

    def test_intent_accepts_common_saos_typo(self):
        resultado = intent.interpretar("quais saos meus projetos?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "projetos")


if __name__ == "__main__":
    unittest.main()
