import os
import tempfile
import unittest

import autonomy
import conversation
import orchestrator
import tasks


class TestMP16UsoReal(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.arquivo_original = tasks.ARQUIVO
        tasks.ARQUIVO = os.path.join(self.tempdir.name, "tasks.json")

    def tearDown(self):
        tasks.ARQUIVO = self.arquivo_original
        self.tempdir.cleanup()

    def _orquestrador(self):
        return orchestrator.StacyOrchestrator(
            api_key="",
            memoria={},
            entidades={"entidades": []},
        )

    def test_fluxo_real_tarefa_criar_listar_concluir(self):
        stacy = self._orquestrador()

        criada = stacy.processar("crie uma tarefa estudar direito")
        self.assertEqual(criada["tipo"], "tarefa_criada")
        self.assertEqual(criada["tarefa"]["titulo"], "estudar direito")

        listada = stacy.processar("quais são minhas tarefas")
        self.assertEqual(listada["tipo"], "tarefas")
        self.assertEqual(len(listada["tarefas"]), 1)

        concluida = stacy.processar("conclua a tarefa estudar direito")
        self.assertEqual(concluida["tipo"], "tarefa_concluida")
        self.assertEqual(concluida["tarefa"]["status"], "concluida")

        self.assertEqual(tasks.listar(status="pendente"), [])

    def test_encadeamento_data_e_hora_da_ultima_tarefa(self):
        stacy = self._orquestrador()

        criada = stacy.processar("crie uma tarefa estudar direito")
        self.assertEqual(criada["tipo"], "tarefa_criada")

        atualizada = stacy.processar("e amanhã às 19:30")
        self.assertEqual(atualizada["tipo"], "tarefa_atualizada")
        self.assertEqual(atualizada["tarefa"]["data"], criada["tarefa"]["data"] if criada["tarefa"]["data"] else atualizada["tarefa"]["data"])
        self.assertEqual(atualizada["tarefa"]["hora"], "19:30")

    def test_contexto_temporario_nao_vira_memoria(self):
        estado = conversation.ConversationState()
        estado.registrar_entidade("P-A1")
        self.assertEqual(estado.obter_ultima_entidade(), "P-A1")
        estado.limpar_entidade()
        self.assertIsNone(estado.obter_ultima_entidade())

    def test_rotas_de_uso_real_mantem_prioridade(self):
        self.assertEqual(
            orchestrator.classificar_rota("quais são minhas tarefas"),
            orchestrator.ROTA_INTERNA,
        )
        self.assertEqual(
            orchestrator.classificar_rota("pesquise as notícias de hoje"),
            orchestrator.ROTA_PESQUISA_EXTERNA,
        )
        self.assertEqual(
            orchestrator.classificar_rota("me ajude a estudar direito"),
            orchestrator.ROTA_IA_LOCAL,
        )

    def test_acao_originada_por_ia_nao_e_executada_sem_confirmacao(self):
        intencao = {
            "tipo": "tarefa",
            "acao": "criar",
            "titulo": "tarefa criada pela IA",
            "origem": autonomy.ORIGEM_IA,
        }
        resultado = autonomy.avaliar_execucao(intencao)
        self.assertFalse(resultado["executar"])
        self.assertEqual(resultado["status"], autonomy.STATUS_CONFIRMAR)


if __name__ == "__main__":
    unittest.main()
