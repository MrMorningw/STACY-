import unittest

import intent
import orchestrator
import cortex


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

    def test_last_question_is_resolved_from_conversation_history(self):
        self.orquestrador.processar("Qual é a capital do Brasil?")
        self.orquestrador.processar("Qual foi a última pergunta que eu fiz?")
        resultado = self.orquestrador.processar("Qual foi a última pergunta que eu fiz?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("Qual foi a última pergunta que eu fiz?", resultado["resposta"])

    def test_first_question_is_resolved_from_conversation_history(self):
        self.orquestrador.processar("Qual é a capital do Brasil?")
        self.orquestrador.processar("Qual é a cor de uma abóbora?")
        resultado = self.orquestrador.processar(
            "Qual foi a primeira pergunta nesta conversa?"
        )
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("Qual é a capital do Brasil?", resultado["resposta"])

    def test_generic_color_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota("qual a cor de uma abobora?"),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_generic_difference_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "qual a diferenca entre responsabilidade civil objetiva e subjetiva?"
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

    def test_requirement_age_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "quantos anos precisa ter para entrar no STF do Brasil?"
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_classification_criteria_question_goes_external(self):
        self.assertEqual(
            orchestrator.classificar_rota(
                "quais os criterios para um corpo celeste ser considerado uma estrela?"
            ),
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_web_research_preserves_context_for_followup(self):
        chamadas = []

        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            def pesquisa_mock(api_key, historico):
                chamadas.append(historico)
                return {
                    "resposta": "Resultado pesquisado.",
                    "fontes": [
                        {
                            "titulo": "Fonte de teste",
                            "url": "https://example.com/fonte"
                        }
                    ]
                }

            orchestrator.ai.gerar_resposta_pesquisa = pesquisa_mock

            self.orquestrador.processar(
                "quais os criterios para um corpo celeste ser considerado uma estrela?"
            )
            resultado = self.orquestrador.processar(
                "e quais os criterios para sua classificacao?"
            )
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa")
        self.assertTrue(chamadas)
        textos = [
            parte["text"]
            for mensagem in chamadas[-1]
            for parte in mensagem.get("parts", [])
            if isinstance(parte, dict) and "text" in parte
        ]
        self.assertIn(
            "quais os criterios para um corpo celeste ser considerado uma estrela?",
            textos
        )
        self.assertEqual(
            textos[-1],
            "e quais os criterios para sua classificacao?"
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
            orchestrator.classificar_rota("qual?"),
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

    def test_common_factual_questions_go_external(self):
        casos = [
            "qual o aumentativo de abobora?",
            "qual o nome da estatua da liberdade?",
            "me diga uma ave que comece com a letra T",
        ]

        for mensagem in casos:
            with self.subTest(mensagem=mensagem):
                self.assertEqual(
                    orchestrator.classificar_rota(mensagem),
                    orchestrator.ROTA_PESQUISA_EXTERNA
                )


    def test_cortex_structures_task_request(self):
        decisao = cortex.analisar(
            "crie uma tarefa estudar direito amanhã",
            intencao={"tipo": "tarefa", "acao": "criar", "titulo": "estudar direito"},
        )
        self.assertEqual(decisao["modo"], cortex.MODO_ACAO)
        self.assertTrue(decisao["needs_action"])
        self.assertEqual(decisao["ferramenta"], "tasks")
        self.assertEqual(decisao["confidence"], 1.0)

    def test_cortex_structures_memory_request(self):
        decisao = cortex.analisar(
            "quais sao meus objetivos",
            intencao={"tipo": "memoria", "acao": "consultar", "categoria": "objetivos"},
        )
        self.assertEqual(decisao["modo"], cortex.MODO_MEMORIA)
        self.assertTrue(decisao["needs_memory"])
        self.assertFalse(decisao["needs_web"])

    def test_cortex_structures_explicit_research(self):
        decisao = cortex.analisar("pesquise a populacao atual do Brasil")
        self.assertEqual(decisao["modo"], cortex.MODO_PESQUISA)
        self.assertTrue(decisao["needs_web"])
        self.assertEqual(decisao["ferramenta"], "web")

    def test_cortex_does_not_use_local_ai_as_factual_authority(self):
        decisao = cortex.analisar("qual a cor de uma abobora?")
        self.assertEqual(decisao["modo"], cortex.MODO_PESQUISA)
        self.assertTrue(decisao["needs_web"])

    def test_cortex_keeps_open_conversation_local(self):
        decisao = cortex.analisar("me ajuda a organizar meus estudos")
        self.assertEqual(decisao["modo"], cortex.MODO_CONVERSA)
        self.assertFalse(decisao["needs_web"])
        self.assertFalse(decisao["needs_action"])

    def test_orchestrator_exposes_structured_cortex_decision(self):
        resultado = self.orquestrador.processar("qual a cor de uma abobora?")
        self.assertEqual(
            self.orquestrador.ultima_decisao["modo"],
            cortex.MODO_PESQUISA
        )
        self.assertTrue(self.orquestrador.ultima_decisao["needs_web"])


class TestContextContinuity(unittest.TestCase):

    def setUp(self):
        memoria = {
            "usuario": {"nome": "Danley"},
            "projetos": [],
            "objetivos": [],
            "preferencias": []
        }
        entidades = {"entidades": []}
        self.orquestrador = orchestrator.StacyOrchestrator(
            "teste",
            memoria,
            entidades
        )

    def test_conversation_state_keeps_structured_continuity(self):
        self.orquestrador.conversa.registrar_rota(
            orchestrator.ROTA_PESQUISA_EXTERNA,
            "capital do Brasil"
        )
        self.assertEqual(
            self.orquestrador.conversa.ultima_consulta,
            "capital do Brasil"
        )
        self.assertEqual(
            self.orquestrador.conversa.ultima_rota,
            orchestrator.ROTA_PESQUISA_EXTERNA
        )

    def test_task_time_followup_updates_last_task(self):
        original_criar = orchestrator.tasks.criar
        original_atualizar = orchestrator.tasks.atualizar
        try:
            tarefa = {
                "id": "T-1",
                "titulo": "estudar responsabilidade civil",
                "data": "2026-09-22",
                "hora": None,
                "status": "pendente"
            }
            orchestrator.tasks.criar = lambda *args, **kwargs: tarefa.copy()
            atualizado = tarefa.copy()
            atualizado["hora"] = "19:00"
            orchestrator.tasks.atualizar = lambda *args, **kwargs: atualizado

            resultado = self.orquestrador.processar(
                "crie uma tarefa estudar responsabilidade civil amanhã"
            )
            self.assertEqual(resultado["tipo"], "tarefa_criada")

            resultado = self.orquestrador.processar("e coloque para 19h")
            self.assertEqual(resultado["tipo"], "tarefa_atualizada")
            self.assertEqual(resultado["tarefa"]["hora"], "19:00")
        finally:
            orchestrator.tasks.criar = original_criar
            orchestrator.tasks.atualizar = original_atualizar

    def test_research_followup_includes_previous_subject(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        consultas = []
        try:
            def pesquisa_mock(api_key, historico):
                consultas.append(historico)
                return {
                    "resposta": "Resultado pesquisado.",
                    "fontes": []
                }

            orchestrator.ai.gerar_resposta_pesquisa = pesquisa_mock
            self.orquestrador.processar(
                "pesquise sobre responsabilidade objetiva"
            )
            resultado = self.orquestrador.processar(
                "e na responsabilidade do empregador?"
            )
            self.assertEqual(resultado["tipo"], "pesquisa")
            textos = [
                p["text"]
                for m in consultas[-1]
                for p in m.get("parts", [])
                if isinstance(p, dict) and "text" in p
            ]
            self.assertTrue(
                any("responsabilidade objetiva" in t.lower() for t in textos)
            )
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

    def test_local_ai_does_not_receive_external_research_turns(self):
        original_pesquisa = orchestrator.ai.gerar_resposta_pesquisa
        original_health = orchestrator.ai.verificar_ia_local
        original_local = orchestrator.ai.gerar_resposta_local
        capturado = []

        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: {
                "resposta": "Resposta externa sobre responsabilidade objetiva.",
                "fontes": []
            }
            orchestrator.ai.verificar_ia_local = lambda: True

            def local_mock(historico, *args, **kwargs):
                capturado.append(historico)
                return "Resposta local."

            orchestrator.ai.gerar_resposta_local = local_mock

            self.orquestrador.processar(
                "pesquise sobre responsabilidade objetiva"
            )
            resultado = self.orquestrador.processar(
                "me ajude a organizar meus estudos"
            )

            self.assertEqual(resultado["tipo"], "ai")
            textos = [
                parte["text"]
                for mensagem in capturado[-1]
                for parte in mensagem.get("parts", [])
                if isinstance(parte, dict) and "text" in parte
            ]
            self.assertFalse(
                any("responsabilidade objetiva" in texto.lower() for texto in textos)
            )
            self.assertIn("organizar meus estudos", textos[-1].lower())
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original_pesquisa
            orchestrator.ai.verificar_ia_local = original_health
            orchestrator.ai.gerar_resposta_local = original_local

    def test_research_adapter_preserves_history_for_external_followup(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        consultas = []

        try:
            def pesquisa_mock(api_key, historico):
                consultas.append(historico)
                return {
                    "resposta": "Resultado pesquisado.",
                    "fontes": []
                }

            orchestrator.ai.gerar_resposta_pesquisa = pesquisa_mock
            self.orquestrador.processar(
                "pesquise sobre responsabilidade objetiva"
            )
            self.orquestrador.processar(
                "e na responsabilidade do empregador?"
            )

            textos = [
                parte["text"]
                for mensagem in consultas[-1]
                for parte in mensagem.get("parts", [])
                if isinstance(parte, dict) and "text" in parte
            ]
            self.assertIn("pesquise sobre responsabilidade objetiva", textos)
            self.assertIn("e na responsabilidade do empregador?", textos)
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

    def test_ambiguous_task_target_asks_instead_of_guessing(self):
        original = orchestrator.tasks.buscar
        try:
            orchestrator.tasks.buscar = lambda *args, **kwargs: [
                {"id": "1", "titulo": "estudar direito"},
                {"id": "2", "titulo": "estudar direito tributário"}
            ]
            resultado = self.orquestrador.processar(
                "conclua a tarefa estudar direito"
            )
            self.assertEqual(resultado["tipo"], "tarefa_ambigua")
            self.assertIn("mais de uma tarefa", resultado["resposta"])
        finally:
            orchestrator.tasks.buscar = original

    def test_stacy_identity_is_not_user_memory(self):
        resultado = self.orquestrador.processar("qual o seu nomee?")
        self.assertEqual(resultado["tipo"], "local")
        self.assertIn("STACY", resultado["resposta"])
        self.assertNotIn("Danley", resultado["resposta"])

    def test_generic_color_question_does_not_fall_into_memory(self):
        original = orchestrator.ai.gerar_resposta_pesquisa
        try:
            orchestrator.ai.gerar_resposta_pesquisa = lambda *args, **kwargs: {
                "resposta": "O céu normalmente aparece azul durante o dia.",
                "fontes": []
            }
            resultado = self.orquestrador.processar("qual a cor do céu?")
        finally:
            orchestrator.ai.gerar_resposta_pesquisa = original

        self.assertEqual(resultado["tipo"], "pesquisa")
        self.assertNotIn("Danley", resultado["resposta"])

    def test_task_list_tolerates_small_spelling_errors(self):
        resultado = intent.interpretar("e aa minhas tafefas?")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "listar")

    def test_conversational_prefix_is_removed_before_routing(self):
        resultado = intent.interpretar("que bom. quais sao minhas tarefas?")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "listar")

    def test_task_creation_extracts_hour_written_as_horas(self):
        resultado = intent.interpretar(
            "crie uma tarefa estudar direito amanhã 18 horas"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "criar")
        self.assertEqual(resultado["titulo"], "estudar direito")
        self.assertEqual(resultado["hora"], "18:00")

    def test_task_typo_and_hour_are_normalized_together(self):
        resultado = intent.interpretar(
            "crie uma tarafe para estudaf amanha 18 horas direto penal"
        )
        self.assertEqual(resultado["titulo"], "estudar direito penal")
        self.assertEqual(resultado["hora"], "18:00")

    def test_conversational_prefix_does_not_break_task_list(self):
        resultado = intent.interpretar("que bom. quais sao minhas tarefas?")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "listar")

    def test_conversational_prefix_does_not_break_task_creation(self):
        resultado = intent.interpretar(
            "otimo. crie uma tarefa estudar responsabilidade civil amanhã às 18h"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "criar")
        self.assertEqual(resultado["titulo"], "estudar responsabilidade civil")
        self.assertEqual(resultado["hora"], "18:00")

    def test_task_creation_tolerates_command_typos(self):
        resultado = intent.interpretar(
            "crie uma tarafe para estudaf amanha 18 horas direto penal"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "criar")
        self.assertEqual(resultado["titulo"], "estudar direito penal")
        self.assertEqual(resultado["hora"], "18:00")

    def test_goals_alias_is_internal_objectives_query(self):
        resultado = intent.interpretar("e minhas metas?")
        self.assertEqual(resultado["tipo"], "memoria")
        self.assertEqual(resultado["categoria"], "objetivos")

    def test_ambiguous_task_reference_does_not_become_literal_title(self):
        resultado = intent.interpretar("crie essa tarefa stacy")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "referencia")

    def test_ambiguous_task_reference_uses_last_task_context(self):
        self.orquestrador.conversa.registrar_tarefa({
            "id": "T-1",
            "titulo": "estudar direito",
            "status": "pendente"
        })
        resultado = self.orquestrador.processar("crie essa tarefa stacy")
        self.assertEqual(resultado["tipo"], "clarificacao")
        self.assertIn("estudar direito", resultado["resposta"])
        self.assertNotIn("tarefa para Stacy", resultado["resposta"])



class TestTaskConversationCorrections(unittest.TestCase):

    def test_task_creation_corrects_cokega_and_removes_temporal_connector(self):
        resultado = intent.interpretar(
            "crie uma tarefa para ir visitar meu cokega as 16 horas de amanha"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "criar")
        self.assertEqual(resultado["titulo"], "ir visitar meu colega")
        self.assertEqual(resultado["hora"], "16:00")
        self.assertIsNotNone(resultado["data"])

    def test_user_name_is_not_classified_as_stacy_identity(self):
        for mensagem in ("qual meu nome?", "e o meu nome?"):
            with self.subTest(mensagem=mensagem):
                resultado = intent.interpretar(mensagem)
                self.assertEqual(resultado["tipo"], "memoria")
                self.assertEqual(resultado["categoria"], "usuario")

    def test_delete_last_task_is_internal_reference(self):
        resultado = intent.interpretar("exclua a ultima tarefa criada")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "remover")
        self.assertEqual(resultado["referencia"], "ultima")

    def test_delete_her_is_internal_reference(self):
        resultado = intent.interpretar("exclua ela")
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "remover")
        self.assertEqual(resultado["referencia"], "ultima")

    def test_correct_last_task_title_by_replacement(self):
        resultado = intent.interpretar(
            "arrume o nome de cokega para colega da tarefa criada"
        )
        self.assertEqual(resultado["tipo"], "tarefa")
        self.assertEqual(resultado["acao"], "corrigir_titulo")
        self.assertEqual(resultado["referencia"], "ultima")
        self.assertEqual(resultado["antigo"], "cokega")
        self.assertEqual(resultado["novo"], "colega")

    def test_delete_last_task_asks_confirmation_instead_of_web(self):
        self.orquestrador.conversa.registrar_tarefa({
            "id": "T-1",
            "titulo": "ir visitar meu colega",
            "status": "pendente"
        })
        resultado = self.orquestrador.processar(
            "exclua a ultima tarefa criada"
        )
        self.assertEqual(resultado["tipo"], "confirmacao")
        self.assertIn("ir visitar meu colega", resultado["resposta"])
        self.assertEqual(resultado["rota"], orchestrator.ROTA_INTERNA)

    def test_correct_last_task_title_executes_locally(self):
        original = orchestrator.tasks.atualizar
        try:
            self.orquestrador.conversa.registrar_tarefa({
                "id": "T-1",
                "titulo": "ir visitar meu cokega",
                "status": "pendente"
            })
            atualizado = {
                "id": "T-1",
                "titulo": "ir visitar meu colega",
                "status": "pendente"
            }
            orchestrator.tasks.atualizar = lambda *args, **kwargs: atualizado
            resultado = self.orquestrador.processar(
                "arrume o nome de cokega para colega da tarefa criada"
            )
        finally:
            orchestrator.tasks.atualizar = original

        self.assertEqual(resultado["tipo"], "tarefa_atualizada")
        self.assertIn("ir visitar meu colega", resultado["resposta"])



if __name__ == "__main__":
    unittest.main()
