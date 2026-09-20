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

    def test_objectives_query_does_not_collide_with_projects(self):
        resultado = intent.interpretar("quais sao os meus objetivos ?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "objetivos")

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

    def test_followup_tasks_query_uses_core(self):
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
                "e as minhas tarefas ?"
            )
        finally:
            orchestrator.tasks.listar = original_listar

        self.assertEqual(resultado["tipo"], "tarefas")
        self.assertIn("estudar direito", resultado["resposta"])

    def test_typo_tolerance_keeps_structured_task_query(self):
        resultado = intent.interpretar(
            "quais sao minhas tafefas?"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "listar")

    def test_typo_tolerance_keeps_structured_project_query(self):
        resultado = intent.interpretar(
            "quais saos meus projtos?"
        )
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "projetos")

    def test_natural_followup_projects_and_objectives(self):
        projetos = intent.interpretar("e os meus projetos?")
        objetivos = intent.interpretar("e meus objetivos?")
        self.assertEqual(projetos["categoria"], "projetos")
        self.assertEqual(objetivos["categoria"], "objetivos")

    def test_memory_recall_command_uses_core(self):
        resultado = intent.interpretar("o que você guardou de mim?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["acao"], "mostrar")

    def test_external_factual_query_is_marked_for_web(self):
        self.assertTrue(
            self.orquestrador._deve_pesquisar_web(
                "quanto tempo vivem os patos?"
            )
        )
        self.assertTrue(
            self.orquestrador._deve_pesquisar_web(
                "pesquise a população atual do Brasil"
            )
        )

    def test_web_routing_does_not_use_question_mark_alone(self):
        self.assertFalse(
            self.orquestrador._deve_pesquisar_web(
                "você está aí?"
            )
        )

    def test_web_research_failure_returns_clean_result(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("429 quota")
            )
            resultado = self.orquestrador.processar(
                "quanto tempo vivem os patos?"
            )
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa_indisponivel")
        self.assertIn("Não vou inventar", resultado["resposta"])

    def test_verified_knowledge_stays_in_core(self):
        resultado = self.orquestrador.processar("quantas luas tem venus?")
        self.assertEqual(resultado["tipo"], "conhecimento_verificado")
        self.assertIn("não possui luas naturais", resultado["resposta"])

    def test_factual_followup_uses_conversation_context(self):
        original_ai = self.orquestrador._usar_ai
        try:
            self.orquestrador._usar_ai = lambda mensagem: {
                "tipo": "ai",
                "resposta": "Resposta inicial.",
                "origem": "teste"
            }

            self.orquestrador.processar(
                "qual fruta é verde e começa com a?"
            )
        finally:
            self.orquestrador._usar_ai = original_ai

        resultado = self.orquestrador.processar(
            "tem um caroço no meio"
        )
        self.assertEqual(resultado["tipo"], "conhecimento_verificado")
        self.assertIn("abacate", resultado["resposta"].lower())

    def test_exit_with_punctuation_is_command(self):
        resultado = self.orquestrador.processar("sair?")
        self.assertEqual(resultado["tipo"], "sair")

    def test_intent_accepts_common_saos_typo(self):
        resultado = intent.interpretar("quais saos meus projetos?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "projetos")


if __name__ == "__main__":
    unittest.main()
