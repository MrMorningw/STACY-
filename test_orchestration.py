import unittest

import orchestration


class OrchestrationTests(unittest.TestCase):

    def test_internal_route_is_sovereign(self):
        decisao = {
            "needs_memory": False,
            "needs_action": False,
            "needs_web": True,
        }
        self.assertEqual(
            orchestration.resolver_rota("interno", decisao),
            "interno",
        )

    def test_memory_overrides_external_route(self):
        decisao = {
            "needs_memory": True,
            "needs_action": False,
            "needs_web": True,
        }
        self.assertEqual(
            orchestration.resolver_rota("pesquisa_externa", decisao),
            "interno",
        )

    def test_action_overrides_external_route(self):
        decisao = {
            "needs_memory": False,
            "needs_action": True,
            "needs_web": True,
        }
        self.assertEqual(
            orchestration.resolver_rota("ia_local", decisao),
            "interno",
        )

    def test_web_overrides_local_route_when_no_internal_need_exists(self):
        decisao = {
            "needs_memory": False,
            "needs_action": False,
            "needs_web": True,
        }
        self.assertEqual(
            orchestration.resolver_rota("ia_local", decisao),
            "pesquisa_externa",
        )

    def test_existing_route_is_preserved_without_new_requirement(self):
        decisao = {
            "needs_memory": False,
            "needs_action": False,
            "needs_web": False,
        }
        self.assertEqual(
            orchestration.resolver_rota("conhecimento_core", decisao),
            "conhecimento_core",
        )

    def test_invalid_decision_does_not_change_route(self):
        self.assertEqual(
            orchestration.resolver_rota("ia_local", None),
            "ia_local",
        )

    def test_decision_shape_is_validated(self):
        self.assertTrue(
            orchestration.validar_decisao({
                "needs_memory": False,
                "needs_action": False,
                "needs_web": False,
            })
        )
        self.assertFalse(orchestration.validar_decisao({}))
        self.assertFalse(orchestration.validar_decisao({
            "needs_memory": "yes",
            "needs_action": False,
            "needs_web": False,
        }))


if __name__ == "__main__":
    unittest.main()
