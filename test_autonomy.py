import unittest

import autonomy


class AutonomyTests(unittest.TestCase):

    def test_core_action_is_authorized(self):
        resultado = autonomy.avaliar_execucao({
            "tipo": "tarefa",
            "acao": "criar",
            "origem": autonomy.ORIGEM_CORE,
        })
        self.assertEqual(resultado["status"], autonomy.STATUS_AUTORIZADA)
        self.assertTrue(resultado["executar"])

    def test_ai_action_requires_confirmation(self):
        resultado = autonomy.avaliar_execucao({
            "tipo": "tarefa",
            "acao": "criar",
            "origem": autonomy.ORIGEM_IA,
        })
        self.assertEqual(resultado["status"], autonomy.STATUS_CONFIRMAR)
        self.assertFalse(resultado["executar"])

    def test_ai_memory_action_requires_confirmation(self):
        resultado = autonomy.avaliar_execucao({
            "tipo": "memoria",
            "acao": "memorizar",
            "origem": autonomy.ORIGEM_IA,
        })
        self.assertEqual(resultado["status"], autonomy.STATUS_CONFIRMAR)
        self.assertFalse(resultado["executar"])

    def test_unknown_origin_is_rejected(self):
        resultado = autonomy.avaliar_execucao({
            "tipo": "tarefa",
            "acao": "criar",
            "origem": "desconhecida",
        })
        self.assertEqual(resultado["status"], autonomy.STATUS_INVALIDA)
        self.assertFalse(resultado["executar"])

    def test_invalid_intention_is_rejected(self):
        resultado = autonomy.avaliar_execucao(None)
        self.assertEqual(resultado["status"], autonomy.STATUS_INVALIDA)
        self.assertFalse(resultado["executar"])

    def test_non_executable_type_is_rejected(self):
        resultado = autonomy.avaliar_execucao({
            "tipo": "conversa",
            "origem": autonomy.ORIGEM_CORE,
        })
        self.assertEqual(resultado["status"], autonomy.STATUS_INVALIDA)
        self.assertFalse(resultado["executar"])


if __name__ == "__main__":
    unittest.main()
