import time


class ConversationState:

    def __init__(self, limite=12):
        self.limite = limite

        self.ultima_mensagem = None
        self.ultima_resposta = None
        self.ultima_entidade_id = None
        self.ultima_acao = None
        self.ultima_intencao = None
        self.ultima_rota = None
        self.ultima_consulta = None
        self.ultima_tarefa = None
        self.intencao_pendente = None
        self.ultima_atualizacao = None

        self.historico = []

    def registrar_mensagem(self, mensagem):

        self.ultima_mensagem = mensagem
        self.ultima_atualizacao = time.time()

        self.historico.append({
            "tipo": "usuario",
            "conteudo": mensagem,
            "timestamp": self.ultima_atualizacao,
            "rota": None
        })

        self._limitar_historico()

    def registrar_resposta(self, resposta):

        self.ultima_resposta = resposta
        self.ultima_atualizacao = time.time()

        self.historico.append({
            "tipo": "stacy",
            "conteudo": resposta,
            "timestamp": self.ultima_atualizacao,
            "rota": None
        })

        self._limitar_historico()

    def registrar_entidade(self, entidade_id):

        self.ultima_entidade_id = entidade_id
        self.ultima_atualizacao = time.time()

    def limpar_entidade(self):
        """Remove apenas o referente temporário da conversa."""
        self.ultima_entidade_id = None
        self.ultima_atualizacao = time.time()

    def registrar_acao(self, acao):

        self.ultima_acao = acao
        self.ultima_atualizacao = time.time()

    def registrar_rota(self, rota, consulta=None):
        self.ultima_rota = rota
        if consulta:
            self.ultima_consulta = consulta
        self.ultima_atualizacao = time.time()

        # A rota pertence ao turno inteiro. Marcamos a última mensagem do
        # usuário e a resposta correspondente para que cada consumidor possa
        # filtrar seu próprio contexto sem depender de outro componente.
        indice_usuario = None
        for indice in range(len(self.historico) - 1, -1, -1):
            if self.historico[indice].get("tipo") == "usuario":
                indice_usuario = indice
                break

        if indice_usuario is None:
            return

        self.historico[indice_usuario]["rota"] = rota

        indice_resposta = indice_usuario + 1
        if (
            indice_resposta < len(self.historico)
            and self.historico[indice_resposta].get("tipo") == "stacy"
        ):
            self.historico[indice_resposta]["rota"] = rota

    def registrar_tarefa(self, tarefa):
        self.ultima_tarefa = tarefa
        self.ultima_atualizacao = time.time()

    def obter_ultima_tarefa(self):
        return self.ultima_tarefa

    def registrar_intencao(self, intencao):

        self.ultima_intencao = intencao
        self.ultima_atualizacao = time.time()

    def registrar_intencao_pendente(self, intencao):
        self.intencao_pendente = intencao

    def obter_intencao_pendente(self):
        return self.intencao_pendente

    def limpar_intencao_pendente(self):
        self.intencao_pendente = None

    def obter_historico(self):

        return list(self.historico)

    def ultimas_mensagens(self, quantidade=6):

        return self.historico[-quantidade:]

    def _limitar_historico(self):

        if len(self.historico) > self.limite:
            self.historico = self.historico[-self.limite:]

    def obter_ultima_mensagem(self):
        return self.ultima_mensagem

    def obter_ultima_resposta(self):
        return self.ultima_resposta

    def obter_ultima_entidade(self):
        return self.ultima_entidade_id

    def obter_ultima_acao(self):
        return self.ultima_acao

    def obter_ultima_intencao(self):
        return self.ultima_intencao

    def obter_contexto_atual(self):
        return {
            "ultima_mensagem": self.ultima_mensagem,
            "ultima_resposta": self.ultima_resposta,
            "ultima_entidade_id": self.ultima_entidade_id,
            "ultima_acao": self.ultima_acao,
            "ultima_intencao": self.ultima_intencao,
            "ultima_rota": self.ultima_rota,
            "ultima_consulta": self.ultima_consulta,
            "ultima_tarefa": self.ultima_tarefa
        }

    def limpar(self):

        self.ultima_mensagem = None
        self.ultima_resposta = None
        self.ultima_entidade_id = None
        self.ultima_acao = None
        self.ultima_intencao = None
        self.ultima_rota = None
        self.ultima_consulta = None
        self.ultima_tarefa = None
        self.intencao_pendente = None
        self.ultima_atualizacao = None
        self.historico = []

    def resumo(self):

        return {
            "ultima_mensagem": self.ultima_mensagem,
            "ultima_resposta": self.ultima_resposta,
            "ultima_entidade_id": self.ultima_entidade_id,
            "ultima_acao": self.ultima_acao,
            "ultima_intencao": self.ultima_intencao,
            "ultima_rota": self.ultima_rota,
            "ultima_consulta": self.ultima_consulta,
            "ultima_tarefa": self.ultima_tarefa,
            "historico": self.ultimas_mensagens()
        }
