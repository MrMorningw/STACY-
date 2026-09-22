import time


class ConversationState:

    ESTADOS_OPERACIONAIS = {
        "ocioso",
        "conversando",
        "aguardando_confirmacao",
        "concluido",
        "erro"
    }

    def __init__(self, limite=12):
        self.limite = limite

        self.ultima_mensagem = None
        self.ultima_resposta = None
        self.ultima_entidade_id = None
        self.ultima_acao = None
        self.ultima_intencao = None
        self.intencao_pendente = None
        self.ultima_atualizacao = None

        # Contexto operacional: estado temporário da execução atual.
        # Não é memória persistente e não deve ser confundido com
        # contexto de entidade persistente.
        self.estado_operacional = "ocioso"
        self.operacao_atual = None
        self.historico = []

    def registrar_mensagem(self, mensagem):

        self.ultima_mensagem = mensagem
        self.ultima_atualizacao = time.time()

        self.historico.append({
            "tipo": "usuario",
            "conteudo": mensagem,
            "timestamp": self.ultima_atualizacao
        })

        if self.estado_operacional == "ocioso":
            self.estado_operacional = "conversando"

        self._limitar_historico()

    def registrar_resposta(self, resposta):

        self.ultima_resposta = resposta
        self.ultima_atualizacao = time.time()

        self.historico.append({
            "tipo": "stacy",
            "conteudo": resposta,
            "timestamp": self.ultima_atualizacao
        })

        # Uma resposta encerra a operação corrente, exceto quando uma ação
        # foi registrada como pendente logo depois dela.
        if self.estado_operacional != "aguardando_confirmacao":
            self.estado_operacional = "concluido"

        self._limitar_historico()

    def registrar_entidade(self, entidade_id):

        self.ultima_entidade_id = entidade_id
        self.ultima_atualizacao = time.time()

    def registrar_acao(self, acao):

        self.ultima_acao = acao
        self.ultima_atualizacao = time.time()

        if isinstance(acao, dict):
            self.operacao_atual = dict(acao)
            self.estado_operacional = "aguardando_confirmacao"
        else:
            self.operacao_atual = None

    def registrar_intencao(self, intencao):

        self.ultima_intencao = intencao
        self.ultima_atualizacao = time.time()

    def registrar_intencao_pendente(self, intencao):
        self.intencao_pendente = intencao
        self.operacao_atual = (
            dict(intencao)
            if isinstance(intencao, dict)
            else intencao
        )
        self.estado_operacional = "conversando"

    def obter_intencao_pendente(self):
        return self.intencao_pendente

    def limpar_intencao_pendente(self):
        self.intencao_pendente = None

    def definir_estado_operacional(self, estado):
        if estado not in self.ESTADOS_OPERACIONAIS:
            raise ValueError(
                f"Estado operacional inválido: {estado}"
            )

        self.estado_operacional = estado
        self.ultima_atualizacao = time.time()

    def obter_estado_operacional(self):
        return self.estado_operacional

    def definir_operacao_atual(self, operacao):
        if operacao is not None and not isinstance(operacao, dict):
            raise TypeError(
                "A operação atual deve ser um dicionário ou None."
            )

        self.operacao_atual = (
            dict(operacao)
            if isinstance(operacao, dict)
            else None
        )
        self.ultima_atualizacao = time.time()

    def obter_operacao_atual(self):
        if isinstance(self.operacao_atual, dict):
            return dict(self.operacao_atual)
        return self.operacao_atual

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
            "ultima_acao": (
                dict(self.ultima_acao)
                if isinstance(self.ultima_acao, dict)
                else self.ultima_acao
            ),
            "ultima_intencao": (
                dict(self.ultima_intencao)
                if isinstance(self.ultima_intencao, dict)
                else self.ultima_intencao
            ),
            "intencao_pendente": (
                dict(self.intencao_pendente)
                if isinstance(self.intencao_pendente, dict)
                else self.intencao_pendente
            ),
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
            "ultima_intencao": self.ultima_intencao
        }

    def limpar(self):

        self.ultima_mensagem = None
        self.ultima_resposta = None
        self.ultima_entidade_id = None
        self.ultima_acao = None
        self.ultima_intencao = None
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
            "estado_operacional": self.estado_operacional,
            "operacao_atual": self.obter_operacao_atual(),
            "historico": self.ultimas_mensagens()
        }
