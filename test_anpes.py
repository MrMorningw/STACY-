import unittest

import anpes
import orchestrator


def plano(etapas=None):
    return {
        "versao": anpes.VERSAO_PLANO,
        "titulo": "Diagnóstico do núcleo",
        "etapas": etapas if etapas is not None else [
            {
                "id": "estado",
                "ferramenta": "diagnostico.status",
                "argumentos": {},
            }
        ],
    }


class AnpesTests(unittest.TestCase):
    def test_read_only_plan_is_ready_but_not_executed(self):
        resultado = anpes.avaliar_plano(plano())
        self.assertEqual(resultado["status"], "pronto")
        self.assertFalse(resultado["executar"])

    def test_unknown_tool_is_rejected(self):
        resultado = anpes.validar_plano(plano([{
            "id": "shell",
            "ferramenta": "terminal.executar_shell",
            "argumentos": {"comando": "echo unsafe"},
        }]))
        self.assertEqual(resultado["status"], "invalido")
        self.assertEqual(resultado["motivo"], "ferramenta_nao_autorizada")

    def test_plan_step_limit_is_enforced(self):
        steps = [
            {"id": f"step-{i}", "ferramenta": "diagnostico.status", "argumentos": {}}
            for i in range(anpes.MAX_ETAPAS + 1)
        ]
        resultado = anpes.validar_plano(plano(steps))
        self.assertEqual(resultado["motivo"], "limite_de_etapas_excedido")

    def test_duplicate_step_ids_are_rejected(self):
        step = {"id": "same", "ferramenta": "diagnostico.status", "argumentos": {}}
        resultado = anpes.validar_plano(plano([step, step]))
        self.assertEqual(resultado["motivo"], "id_de_etapa_duplicado")

    def test_medium_risk_requires_explicit_approval(self):
        result = anpes.avaliar_plano(plano([{
            "id": "open",
            "ferramenta": "android.abrir_app",
            "argumentos": {"app": "calculadora"},
        }]))
        self.assertEqual(result["status"], "aguardando_confirmacao")
        self.assertEqual(result["etapas_que_exigem_confirmacao"], ["open"])

    def test_unconnected_executor_is_reported(self):
        result = anpes.executar_plano(plano(), executores={})
        self.assertEqual(result["status"], "indisponivel")
        self.assertEqual(result["motivo"], "executor_nao_conectado")

    def test_simulation_never_calls_executor(self):
        calls = []
        result = anpes.executar_plano(
            plano(),
            executores={"diagnostico.status": lambda args: calls.append(args)},
        )
        self.assertEqual(result["status"], "simulacao")
        self.assertEqual(calls, [])

    def test_execution_requires_approval_for_medium_risk(self):
        calls = []
        plan = plano([{
            "id": "open",
            "ferramenta": "android.abrir_app",
            "argumentos": {"app": "calculadora"},
        }])
        result = anpes.executar_plano(
            plan,
            executores={"android.abrir_app": lambda args: calls.append(args) or {"ok": True}},
            simulacao=False,
        )
        self.assertEqual(result["status"], "aguardando_confirmacao")
        self.assertEqual(calls, [])

    def test_approved_execution_returns_handler_result(self):
        calls = []
        plan = plano([{
            "id": "open",
            "ferramenta": "android.abrir_app",
            "argumentos": {"app": "calculadora"},
        }])
        result = anpes.executar_plano(
            plan,
            executores={"android.abrir_app": lambda args: calls.append(args) or {"ok": True}},
            etapas_aprovadas={"open"},
            simulacao=False,
        )
        self.assertEqual(result["status"], "concluido")
        self.assertEqual(result["resultados"][0]["resultado"], {"ok": True})
        self.assertEqual(len(calls), 1)

    def test_executor_exception_is_sanitized_and_stops_plan(self):
        events = []
        result = anpes.executar_plano(
            plano(),
            executores={"diagnostico.status": lambda args: (_ for _ in ()).throw(RuntimeError("secret path"))},
            simulacao=False,
            auditoria=events.append,
        )
        self.assertEqual(result["status"], "falhou")
        self.assertNotIn("secret path", str(result))
        self.assertEqual(result["resultados"][0]["motivo"], "falha_interna_do_executor")
        self.assertEqual(events[-1]["estado"], "falhou")

    def test_orchestrator_exposes_deterministic_anpes_status(self):
        core = orchestrator.StacyOrchestrator.__new__(orchestrator.StacyOrchestrator)
        result = core._processar_anpes("status do ANPES")
        self.assertEqual(result["tipo"], "anpes_status")
        self.assertEqual(result["rota"], orchestrator.ROTA_INTERNA)
        self.assertEqual(result["anpes"]["politica_autonomia"], "integrada_ao_core")

    def test_orchestrator_does_not_capture_unrelated_messages_as_status(self):
        core = orchestrator.StacyOrchestrator.__new__(orchestrator.StacyOrchestrator)
        self.assertIsNone(core._processar_anpes("qual é a previsão do tempo"))

    def test_status_reports_actual_integration_limits(self):
        status = anpes.estado()
        self.assertEqual(status["politica_autonomia"], "integrada_ao_core")
        self.assertTrue(status["simulacao_padrao"])
        self.assertEqual(status["execucao_por_ferramentas"], "requer_executores_registrados")
        self.assertFalse(status["auto_modificacao"])
        self.assertFalse(status["apk_autossuficiente"])

    def test_core_intention_keeps_existing_authorized_contract(self):
        result = anpes.avaliar_intencao({
            "tipo": "tarefa",
            "acao": "criar",
            "origem": anpes.ORIGEM_CORE,
        })
        self.assertEqual(result["status"], anpes.STATUS_AUTORIZADA)
        self.assertTrue(result["executar"])

    def test_ai_intention_is_blocked_until_explicit_command(self):
        result = anpes.avaliar_intencao({
            "tipo": "memoria",
            "acao": "memorizar",
            "origem": anpes.ORIGEM_IA,
        })
        self.assertEqual(result["status"], anpes.STATUS_CONFIRMAR)
        self.assertFalse(result["executar"])

    def test_unknown_intention_origin_is_rejected(self):
        result = anpes.avaliar_intencao({
            "tipo": "tarefa",
            "origem": "unknown",
        })
        self.assertEqual(result["status"], anpes.STATUS_INVALIDA)
        self.assertFalse(result["executar"])

    def test_invalid_mode_is_rejected(self):
        result = anpes.avaliar_plano(plano(), modo="autonomia_total")
        self.assertEqual(result["status"], "invalido")
        self.assertEqual(result["motivo"], "modo_de_autonomia_invalido")

    def test_non_string_tool_identifier_is_rejected_without_crashing(self):
        result = anpes.validar_plano(plano([{
            "id": "bad-tool",
            "ferramenta": [],
            "argumentos": {},
        }]))
        self.assertEqual(result["status"], "invalido")
        self.assertEqual(result["motivo"], "ferramenta_nao_autorizada")

    def test_invalid_plan_is_rejected(self):
        self.assertEqual(anpes.validar_plano(None)["status"], "invalido")


if __name__ == "__main__":
    unittest.main()
