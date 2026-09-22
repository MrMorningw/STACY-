import unittest

import mepo


class MepoTest(unittest.TestCase):

    def test_catalogo_tem_12_mepos_em_sequencia(self):
        registros = mepo.listar()
        self.assertEqual(len(registros), 12)
        self.assertTrue(mepo.validar_sequencia(registros))

    def test_mp01_a_mp11_estao_fechados_e_mp12_aguarda_inicio(self):
        registros = mepo.listar()
        self.assertTrue(all(item["status"] == "fechado" for item in registros[:11]))
        self.assertEqual(registros[11]["status"], "planejado")
        self.assertEqual(mepo.proximo_aberto()["id"], "MP-12")

    def test_transicoes_sao_controladas(self):
        self.assertTrue(mepo.validar_transicao("planejado", "em_execucao"))
        self.assertTrue(mepo.validar_transicao("em_execucao", "validado"))
        self.assertTrue(mepo.validar_transicao("validado", "fechado"))
        self.assertFalse(mepo.validar_transicao("fechado", "em_execucao"))
        self.assertFalse(mepo.validar_transicao("planejado", "fechado"))

    def test_identificador_invalido(self):
        self.assertIsNone(mepo.obter("MP-99"))
        self.assertIsNone(mepo.numero("abc"))


if __name__ == "__main__":
    unittest.main()
