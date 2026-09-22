import time


class ConversationState:

    ESTADOS_OPERACIONAIS = {"ocioso", "conversando", "aguardando_confirmacao", "concluido", "erro"}

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
        self.estado_operacional = "ocioso"
        self.operacao_atual = None

        self.historico = []

    def registrar_mensagem(self, mensagem):

        self.ultima_mensagem = mensagem
        self.ultima_atualizacao = time.time()
        if self.estado_operacional == "ocioso":
            self.estado_operacional = "conversando"

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

        if self.estado_operacional != "aguardando_confirmacao":
            self.estado_operacional = "concluido"

        self._limitar_historico()

    def registrar_entidade(self, entidade_id):

        self.ultima_entidade_id = entidade_id
        self.ultima_atualizacao = time.time()

    def limpar_entidade(self):
        """Remove apenas o referente temporário da conversa."""
        self.ultima_entidade_id = None
        self.ultima_atualizacao = time.time()

    def registrar_acao(self, acao, aguardando_confirmacao=False):

        self.ultima_acao = dict(acao) if isinstance(acao, dict) else acao
        self.operacao_atual = dict(acao) if isinstance(acao, dict) else acao
        self.ultima_atualizacao = time.time()

        if aguardando_confirmacao:
            self.estado_operacional = "aguardando_confirmacao"
        elif self.estado_operacional != "erro":
            self.estado_operacional = "concluido"

    def registrar_acao_pendente(self, acao):
        self.registrar_acao(acao, aguardando_confirmacao=True)

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
        self.intencao_pendente = dict(intencao) if isinstance(intencao, dict) else intencao
        self.operacao_atual = dict(intencao) if isinstance(intencao, dict) else intencao
        self.estado_operacional = "conversando"
        self.ultima_atualizacao = time.time()

    def obter_intencao_pendente(self):
        return self.intencao_pendente

    def limpar_intencao_pendente(self):
        self.intencao_pendente = None
        if self.estado_operacional == "conversando":
            self.operacao_atual = None
            self.estado_operacional = "ocioso"
        self.ultima_atualizacao = time.time()

    def definir_estado_operacional(self, estado):
        if estado not in self.ESTADOS_OPERACIONAIS:
            raise ValueError(f"Estado operacional inválido: {estado}")
        self.estado_operacional = estado
        self.ultima_atualizacao = time.time()

    def obter_estado_operacional(self):
        return self.estado_operacional

    def definir_operacao_atual(self, operacao):
        if operacao is not None and not isinstance(operacao, dict):
            raise TypeError("A operação atual deve ser um dicionário ou None.")
        self.operacao_atual = dict(operacao) if isinstance(operacao, dict) else None
        self.ultima_atualizacao = time.time()

    def obter_operacao_atual(self):
        return dict(self.operacao_atual) if isinstance(self.operacao_atual, dict) else self.operacao_atual

    def registrar_erro(self, erro=None):
        self.estado_operacional = "erro"
        self.operacao_atual = {"erro": str(erro)} if erro is not None else None
        self.ultima_atualizacao = time.time()

    def limpar_operacao(self):
        self.operacao_atual = None
        self.ultima_acao = None
        self.intencao_pendente = None
        self.estado_operacional = "ocioso"
        self.ultima_atualizacao = time.time()

    def obter_contexto_operacional(self):
        return {
            "estado": self.estado_operacional,
            "operacao_atual": self.obter_operacao_atual(),
            "ultima_entidade_id": self.ultima_entidade_id,
            "ultima_acao": dict(self.ultima_acao) if isinstance(self.ultima_acao, dict) else self.ultima_acao,
            "ultima_intencao": dict(self.ultima_intencao) if isinstance(self.ultima_intencao, dict) else self.ultima_intencao,
            "intencao_pendente": dict(self.intencao_pendente) if isinstance(self.intencao_pendente, dict) else self.intencao_pendente,
            "ultima_mensagem": self.ultima_mensagem,
            "ultima_resposta": self.ultima_resposta,
            "ultima_atualizacao": self.ultima_atualizacao
        }

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
            "ultima_tarefa": self.ultima_tarefa,
            "estado_operacional": self.estado_operacional,
            "operacao_atual": self.obter_operacao_atual()
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
        self.estado_operacional = "ocioso"
        self.operacao_atual = None
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
