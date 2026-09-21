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

    def test_route_internal_memory_is_never_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "pesquise meus projetos",
                intencao={"tipo": "memoria", "acao": "consultar"},
            ),
            orchestrator.ROTA_INTERNA
        )

    def test_route_internal_tasks_is_never_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "pesquise minhas tarefas",
                intencao={"tipo": "tarefa", "acao": "listar"},
            ),
            orchestrator.ROTA_INTERNA
        )

    def test_explicit_research_has_priority_over_core_knowledge(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "pesquise quantas luas tem venus",
                conhecimento=True,
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_core_knowledge_is_separate_from_external_research(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "quantas luas tem venus?",
                conhecimento=True,
            ),
            orchestrator.ROTA_CONHECIMENTO
        )

    def test_unknown_quantitative_fact_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "quanto tempo vivem os patos?",
                conhecimento=False,
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_ai_response_is_added_once_to_history(self):
        original_health = orchestrator.ai.verificar_ia_local
        original_local = orchestrator.ai.gerar_resposta_local
        try:
            orchestrator.ai.verificar_ia_local = lambda: True
            orchestrator.ai.gerar_resposta_local = (
                lambda *args, **kwargs: "Resposta de teste."
            )
            resultado = orchestrator.StacyOrchestrator._usar_ai(self.orquestrador, "primeira pergunta")
        finally:
            orchestrator.ai.verificar_ia_local = original_health
            orchestrator.ai.gerar_resposta_local = original_local

        self.assertEqual(resultado["tipo"], "ai")
        modelos = [
            item for item in self.orquestrador.historico
            if item.get("role") == "model"
        ]
        self.assertEqual(len(modelos), 1)
        self.assertEqual(
            modelos[0]["parts"][0]["text"],
            "Resposta de teste."
        )

    def test_route_source_word_alone_stays_local(self):
        self.assertEqual(
            orchestrator.classificar_rota("quais fontes bibliográficas devo estudar?"),
            orchestrator.ROTA_IA_LOCAL
        )

    def test_route_explicit_source_request_is_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("me dê fontes sobre responsabilidade civil"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_explicit_external_research(self):
        self.assertEqual(
            orchestrator.classificar_rota("pesquise a população atual do Brasil"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_current_information_is_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual a notícia atual sobre o Brasil?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_quantitative_lifespan_question_is_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("quanto tempo patos vivem?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_quantitative_count_question_is_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("quantos mares o planeta Terra tem?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_conversational_prefix_does_not_break_memory_query(self):
        resultado = intent.interpretar(
            "otimo. wuais sao meus projetos?"
        )
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "projetos")

    def test_conversational_prefix_with_comma_is_tolerated(self):
        resultado = intent.interpretar(
            "certo, quais sao meus objetivos?"
        )
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "objetivos")

    def test_factual_verb_typo_is_normalized_for_routing(self):
        self.assertEqual(
            orchestrator._normalizar_rota(
                "quantos presidentes o brasil possuie?"
            ),
            "quantos presidentes o brasil possui"
        )

    def test_unknown_count_with_past_tense_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "quantos presidentes o brasil ja teve?"
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_specific_translation_request_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "como se diz eu te amo em latim?"
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_typo_in_routing_vocabulary_is_normalized_generally(self):
        self.assertEqual(
            orchestrator._normalizar_rota("quantaa"),
            "quantas"
        )

    def test_capital_fact_question_is_external_without_core_answer(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "qual a capital de Portugal?",
                conhecimento=False,
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_small_typo_in_local_phrase_uses_local_response(self):
        resultado = self.orquestrador.processar("como voce esya?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("operando normalmente", resultado["resposta"])


    def test_price_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("quanto custa um notebook?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_value_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual o valor de uma ação hoje?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_date_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual a data de fundação da ONU?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_route_normal_conversation_is_local_ai(self):
        self.assertEqual(
            orchestrator.classificar_rota("você está aí?"),
            orchestrator.ROTA_IA_LOCAL
        )

    def test_route_internal_project_question_overrides_question_word(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual é meu projeto?"),
            orchestrator.ROTA_INTERNA
        )

    def test_self_identity_is_local(self):
        resultado = self.orquestrador.processar("quem é você?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("STACY", resultado["resposta"])

    def test_route_question_words_alone_stay_local(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual a diferença entre responsabilidade objetiva e subjetiva?"),
            orchestrator.ROTA_IA_LOCAL
        )

    def test_confirmation_accepts_punctuation(self):
        self.orquestrador.acao_pendente = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        original_remover = orchestrator.tasks.remover
        try:
            orchestrator.tasks.remover = lambda tarefa_id: {
                "id": tarefa_id,
                "titulo": "teste"
            }
            resultado = self.orquestrador.processar("Sim!")
        finally:
            orchestrator.tasks.remover = original_remover

        self.assertEqual(resultado["tipo"], "tarefa_removida")
        self.assertIsNone(self.orquestrador.acao_pendente)

    def test_unrelated_message_clears_stale_pending_action(self):
        self.orquestrador.acao_pendente = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        self.orquestrador._usar_ai = lambda mensagem: {
            "tipo": "ai",
            "resposta": "Resposta local de teste.",
            "origem": "teste"
        }
        resultado = self.orquestrador.processar("Explique responsabilidade civil.")
        self.assertEqual(resultado["tipo"], "ai")
        self.assertIsNone(self.orquestrador.acao_pendente)

    def test_internal_intent_overrides_explicit_research_word(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "pesquise meus objetivos",
                intencao={"tipo": "memoria", "acao": "consultar", "categoria": "objetivos"}
            ),
            orchestrator.ROTA_INTERNA
        )

    def test_verified_knowledge_stays_in_core(self):
        resultado = self.orquestrador.processar("quantas luas tem venus?")
        self.assertEqual(resultado["tipo"], "conhecimento_verificado")
        self.assertIn("não possui luas naturais", resultado["resposta"])

    def test_explicit_research_bypasses_core_knowledge(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: {
                "resposta": "Resultado pesquisado.",
                "fontes": [{"titulo": "Fonte teste", "url": "https://example.com/fonte"}]
            }
            resultado = self.orquestrador.processar("pesquise quantas luas tem venus")
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa")
        self.assertEqual(resultado["resposta"], "Resultado pesquisado.")

    def test_duck_lifespan_uses_external_research(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: {
                "resposta": "Resposta pesquisada sobre a expectativa de vida dos patos.",
                "fontes": [{"titulo": "Fonte teste", "url": "https://example.com/patos"}]
            }
            resultado = self.orquestrador.processar("quanto tempo vivem os patos?")
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa")
        self.assertIn("expectativa de vida", resultado["resposta"])

    def test_web_research_failure_returns_clean_result(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("429 quota"))
            resultado = self.orquestrador.processar("pesquise a população atual do Brasil")
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa_indisponivel")
        self.assertIn("Não vou inventar", resultado["resposta"])

    def test_memory_recall_is_human_readable(self):
        resultado = self.orquestrador.processar("o que você guardou de mim?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("STACY", resultado["resposta"])
        self.assertIn("aprender ingles", resultado["resposta"])

    def test_duplicate_memory_does_not_fall_into_ai(self):
        resultado = self.orquestrador.processar(
            "memorize projetos.STACY"
        )
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("já estava registrado", resultado["resposta"])

    def test_missing_memory_removal_does_not_fall_into_ai(self):
        resultado = self.orquestrador.processar(
            "esquecer projetos.NAO_EXISTE"
        )
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("Nenhuma informação foi alterada", resultado["resposta"])

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
