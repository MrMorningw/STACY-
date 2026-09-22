import unittest

import conversation
import orchestrator


class OperationalContextTests(unittest.TestCase):

    def setUp(self):
        self.contexto = conversation.ConversationState()


    def test_orchestrator_confirmation_keeps_action_pending(self):
        estado = orchestrator.StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []}
        )
        acao = {
            "tipo": "atualizar_atributo",
            "entidade_id": "P-A1",
            "campo": "objetivos",
            "valor": "Direito"
        }
        estado._registrar_resultado_conversa({
            "tipo": "acao_candidata",
            "resposta": "Deseja confirmar?",
            "acao": acao
        })
        self.assertEqual(
            estado.conversa.obter_estado_operacional(),
            "aguardando_confirmacao"
        )
        self.assertEqual(
            estado.conversa.obter_operacao_atual(),
            acao
        )

    def test_orchestrator_completed_action_closes_operation(self):
        estado = orchestrator.StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []}
        )
        acao = {
            "tipo": "atualizar_atributo",
            "entidade_id": "P-A1",
            "campo": "objetivos",
            "valor": "Direito"
        }
        estado._registrar_resultado_conversa({
            "tipo": "acao_executada",
            "resposta": "Pronto, senhor.",
            "acao": acao
        })
        self.assertEqual(
            estado.conversa.obter_estado_operacional(),
            "concluido"
        )
        self.assertEqual(
            estado.conversa.obter_operacao_atual(),
            acao
        )

    def test_orchestrator_error_marks_operational_state_as_error(self):
        estado = orchestrator.StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []}
        )
        estado._registrar_resultado_conversa({
            "tipo": "erro_acao",
            "resposta": "Não consegui executar.",
            "erro": "falha de teste"
        })
        self.assertEqual(
            estado.conversa.obter_estado_operacional(),
            "erro"
        )
        self.assertIn(
            "falha de teste",
            estado.conversa.obter_operacao_atual()["erro"]
        )


    def test_new_message_clears_stale_confirmation_before_local_reply(self):
        estado = orchestrator.StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []}
        )
        estado.acao_pendente = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        estado.conversa.registrar_acao_pendente(
            estado.acao_pendente
        )

        resultado = estado.processar("oi")

        self.assertEqual(resultado["tipo"], "local")
        self.assertIsNone(estado.acao_pendente)
        self.assertEqual(
            estado.conversa.obter_estado_operacional(),
            "concluido"
        )

    def test_initial_state_is_idle(self):
        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "ocioso"
        )
        self.assertIsNone(
            self.contexto.obter_operacao_atual()
        )

    def test_user_message_enters_conversation_state(self):
        self.contexto.registrar_mensagem("oi stacy")
        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "conversando"
        )
        self.assertEqual(
            self.contexto.obter_ultima_mensagem(),
            "oi stacy"
        )

    def test_response_closes_normal_operation(self):
        self.contexto.registrar_mensagem("oi stacy")
        self.contexto.registrar_resposta("Olá, senhor.")
        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "concluido"
        )

    def test_action_creates_pending_operational_context(self):
        acao = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        self.contexto.registrar_acao_pendente(acao)

        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "aguardando_confirmacao"
        )
        self.assertEqual(
            self.contexto.obter_operacao_atual(),
            acao
        )

    def test_executed_action_does_not_wait_for_confirmation(self):
        acao = {
            "tipo": "atualizar_atributo",
            "entidade_id": "P-A1",
            "campo": "objetivos",
            "valor": "Direito"
        }

        self.contexto.registrar_acao(acao)

        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "concluido"
        )
        self.assertEqual(
            self.contexto.obter_operacao_atual(),
            acao
        )

    def test_response_before_action_does_not_hide_pending_state(self):
        acao = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        self.contexto.registrar_resposta("Confirma a remoção?")
        self.contexto.registrar_acao_pendente(acao)

        estado = self.contexto.obter_contexto_operacional()

        self.assertEqual(
            estado["estado"],
            "aguardando_confirmacao"
        )
        self.assertEqual(
            estado["operacao_atual"],
            acao
        )

    def test_operational_context_is_not_persistent_entity_context(self):
        self.contexto.registrar_entidade("P-A1")
        self.contexto.registrar_acao({
            "tipo": "atualizar_atributo",
            "entidade_id": "P-A1",
            "campo": "objetivos",
            "valor": "Direito"
        })

        operacional = self.contexto.obter_contexto_operacional()

        self.assertEqual(
            operacional["ultima_entidade_id"],
            "P-A1"
        )
        self.assertEqual(
            operacional["operacao_atual"]["entidade_id"],
            "P-A1"
        )

    def test_clear_operation_removes_temporary_state(self):
        self.contexto.registrar_acao_pendente({
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        })
        self.contexto.registrar_intencao_pendente({
            "tipo": "tarefa",
            "acao": "remover"
        })

        self.contexto.limpar_operacao()

        self.assertEqual(
            self.contexto.obter_estado_operacional(),
            "ocioso"
        )
        self.assertIsNone(
            self.contexto.obter_operacao_atual()
        )
        self.assertIsNone(
            self.contexto.obter_intencao_pendente()
        )
        self.assertIsNone(
            self.contexto.obter_ultima_acao()
        )

    def test_invalid_operational_state_fails_closed(self):
        with self.assertRaises(ValueError):
            self.contexto.definir_estado_operacional("estado_inexistente")

    def test_operational_context_is_snapshot_not_internal_reference(self):
        acao = {
            "tipo": "remover_tarefa",
            "tarefa_id": "T-1"
        }
        self.contexto.registrar_acao(acao)

        snapshot = self.contexto.obter_contexto_operacional()
        snapshot["operacao_atual"]["tarefa_id"] = "T-999"

        self.assertEqual(
            self.contexto.obter_operacao_atual()["tarefa_id"],
            "T-1"
        )


if __name__ == "__main__":
    unittest.main()
