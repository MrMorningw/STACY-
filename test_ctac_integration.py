import unittest

from orchestrator import StacyOrchestrator


class CtacIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.orquestrador = StacyOrchestrator(
            api_key=None,
            memoria={},
            entidades={"entidades": []},
        )

    def test_consulta_ctac_e_interna(self):
        resultado = self.orquestrador.processar("status do CTAC")
        self.assertEqual(resultado["tipo"], "ctac")
        self.assertEqual(resultado["rota"], "interno")
        self.assertTrue(resultado["estado_ctac"]["coerente"])

    def test_consulta_mepos_e_interna(self):
        resultado = self.orquestrador.processar("quais são meus MEPOs")
        self.assertEqual(resultado["tipo"], "mepos")
        self.assertEqual(resultado["rota"], "interno")
        self.assertIn("MP-09", resultado["resposta"])
        self.assertEqual(len(resultado["mepos"]), 12)


if __name__ == "__main__":
    unittest.main()
