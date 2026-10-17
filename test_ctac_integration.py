import unittest

from orchestrator import StacyOrchestrator


class MepoIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.orquestrador = StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []},
        )

    def test_consulta_mepos_e_interna(self):
        resultado = self.orquestrador.processar("quais são meus MEPOs")
        self.assertEqual(resultado["tipo"], "mepos")
        self.assertEqual(resultado["rota"], "interno")
        self.assertIn("MP-09", resultado["resposta"])
        self.assertEqual(len(resultado["mepos"]), 12)

    def test_orchestrator_has_no_ctac_dependency(self):
        import inspect
        source = inspect.getsource(StacyOrchestrator)
        self.assertNotIn("ctac", source.lower())


if __name__ == "__main__":
    unittest.main()
