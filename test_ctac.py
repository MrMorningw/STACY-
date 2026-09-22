import unittest

import ctac


class CtacTest(unittest.TestCase):

    def test_estado_aponta_proxima_mp12(self):
        estado = ctac.estado()
        self.assertEqual(estado["mepo_atual"], "MP-12")
        self.assertEqual(estado["status_mepo_atual"], "planejado")
        self.assertEqual(estado["mepos_fechados"], 11)

    def test_coerencia_da_trajetoria(self):
        resultado = ctac.validar_coerencia()
        self.assertTrue(resultado["coerente"])
        self.assertEqual(resultado["erros"], [])

    def test_formatacao(self):
        self.assertIn("MP-12", ctac.formatar_estado())
        self.assertIn("MP-01", ctac.formatar_mepos())


if __name__ == "__main__":
    unittest.main()
