import unittest
import ctac
class CtacTest(unittest.TestCase):
    def test_trajetoria_completa(self):
        estado=ctac.estado(); self.assertIsNone(estado["mepo_atual"]); self.assertEqual(estado["status_mepo_atual"],None); self.assertEqual(estado["mepos_fechados"],12); self.assertTrue(ctac.validar_coerencia()["coerente"])
    def test_formatacao(self):
        self.assertIn("CTAC",ctac.formatar_estado()); self.assertIn("MP-12",ctac.formatar_mepos())
if __name__=="__main__": unittest.main()
