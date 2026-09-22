import unittest

import ctac
import mepo
import autonomy
import orchestration


class FinalStabilityTest(unittest.TestCase):

    def test_ctac_final_trajectory(self):
        registros = mepo.listar()
        self.assertEqual(len(registros), 12)
        self.assertTrue(mepo.validar_sequencia(registros))
        self.assertTrue(all(item["status"] == "fechado" for item in registros[:11]))
        self.assertEqual(registros[11]["status"], "planejado")
        self.assertTrue(ctac.validar_coerencia()["coerente"])

    def test_orchestration_and_autonomy_boundaries(self):
        self.assertEqual(
            orchestration.resolver_rota(
                "interno",
                {"needs_memory": False, "needs_action": False, "needs_web": True},
            ),
            "interno",
        )
        self.assertFalse(
            autonomy.avaliar_execucao({
                "tipo": "tarefa",
                "origem": autonomy.ORIGEM_IA,
            })["executar"]
        )

    def test_python_modules_import(self):
        import stacy
        import orchestrator
        import ai
        import context
        import conversation
        import tasks
        import entity
        import entity_store
        import action
        import intent
        self.assertTrue(all((m is not None) for m in (
            stacy, orchestrator, ai, context, conversation, tasks,
            entity, entity_store, action, intent,
        )))


if __name__ == "__main__":
    unittest.main()
