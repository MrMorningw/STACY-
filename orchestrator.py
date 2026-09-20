import json
import unicodedata
import context
import entity_store
import memory
import intent
import command
import ai
import entity_resolver
import action
import conversation
import tasks
import knowledge




ROTA_INTERNA = "interno"
ROTA_CONHECIMENTO = "conhecimento_core"
ROTA_IA_LOCAL = "ia_local"
ROTA_PESQUISA_EXTERNA = "pesquisa_externa"


def _normalizar_rota(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)

    # Tolerância a erro de digitação comum sem alterar o restante da frase.
    texto = texto.replace("quantaa ", "quantas ")
    texto = texto.replace("quantoo ", "quanto ")

    caracteres = []
    for caractere in texto:
        categoria = unicodedata.category(caractere)

        if categoria == "Mn":
            continue

        if categoria.startswith("P"):
            caracteres.append(" ")
        else:
            caracteres.append(caractere)

    return " ".join("".join(caracteres).split())


def _contem_termo(texto, termo):
    """Verifica termo/frase sem casar dentro de outra palavra."""
    texto = f" {texto.strip()} "
    termo = f" {termo.strip()} "
    return termo in texto


def classificar_rota(mensagem, intencao=None, comando=None, conhecimento=False):
    """Classifica a mensagem em exatamente uma rota."""
    texto = _normalizar_rota(mensagem)

    # 1) INTERNO: dados e operações da própria STACY nunca saem para IA/Web.
    if comando in {"memoria", "buscar", "memorize", "esquecer"}:
        return ROTA_INTERNA

    if isinstance(intencao, dict) and intencao.get("tipo") in {"memoria", "tarefa"}:
        return ROTA_INTERNA

    marcadores_internos = (
        "meus projetos", "meus objetivos", "minhas preferencias",
        "minhas tarefas", "minhas informacoes", "o que voce guardou",
        "o que voce sabe sobre mim", "minha memoria", "dados sobre mim",
        "informacoes sobre mim", "me diga meus projetos",
        "me diga meus objetivos", "qual e meu projeto",
        "qual e o meu projeto", "qual e meu objetivo",
        "qual e o meu objetivo", "quais sao meus projetos",
        "quais sao os meus projetos", "quais sao meus objetivos",
        "quais sao os meus objetivos"
    )
    if any(_contem_termo(texto, marcador) for marcador in marcadores_internos):
        return ROTA_INTERNA

    # 2) PESQUISA EXPLÍCITA: pedido direto do usuário sempre significa Web.
    gatilhos_externos = (
        "pesquise", "pesquisar", "pesquisa na internet",
        "procure", "busque", "pesquisa no google",
        "procure no google", "na internet", "no google"
    )
    if any(_contem_termo(texto, gatilho) for gatilho in gatilhos_externos):
        return ROTA_PESQUISA_EXTERNA

    # Pedido explícito de fontes também exige consulta externa, mas
    # somente em construções que indiquem essa intenção; "fontes" isolada
    # pode aparecer em perguntas conceituais.
    gatilhos_fontes = (
        "me de fontes", "me dê fontes", "com fontes",
        "cite fontes", "fontes sobre", "fontes para"
    )
    if any(_contem_termo(texto, gatilho) for gatilho in gatilhos_fontes):
        return ROTA_PESQUISA_EXTERNA

    # 3) PESQUISA IMPLÍCITA: atualidade ou fatos externos verificáveis.
    termos_temporais = (
        "hoje", "agora", "atual", "atualmente", "ultimo", "ultima",
        "ultimos", "ultimas", "recentemente", "noticia", "noticias"
    )
    if any(_contem_termo(texto, termo) for termo in termos_temporais):
        return ROTA_PESQUISA_EXTERNA

    padroes_factuais = (
        "quem e ", "quem foi ", "quem sao ", "quando foi ",
        "quando aconteceu ", "onde fica ", "quanto tempo vive",
        "quanto tempo vivem", "quantos anos vive", "qual a idade de",
        "qual o tamanho de", "qual a populacao de",
        "qual e a populacao de", "tem quantas luas",
        "possui quantas luas"
    )
    if any(padrao in texto for padrao in padroes_factuais):
        return ROTA_PESQUISA_EXTERNA

    # CORE: um fato já verificado tem prioridade sobre qualquer
    # padrão implícito de pesquisa. A pesquisa explícita já foi tratada
    # acima e continua tendo prioridade absoluta.
    if conhecimento:
        return ROTA_CONHECIMENTO

    # 4) PESQUISA IMPLÍCITA: perguntas quantitativas factuais que não
    # possuem resposta verificada no CORE.
    padroes_quantitativos = (
        "quanto tempo ",
        "quantos ",
        "quantas ",
    )
    verbos_quantitativos = (
        " vive", " vivem", " tem", " têm", " existem",
        " sao", " são", " ha", " há"
    )
    if any(padrao in texto for padrao in padroes_quantitativos):
        if any(verbo in texto for verbo in verbos_quantitativos):
            return ROTA_PESQUISA_EXTERNA

    # 6) IA LOCAL: conversa, estudo e raciocínio sem necessidade externa.
    return ROTA_IA_LOCAL


def _normalizar_confirmacao(texto):
    texto = _normalizar_rota(texto)
    return texto.rstrip("?!.,;: ")


class StacyOrchestrator:

    def __init__(
        self,
        api_key,
        memoria,
        entidades
    ):
        self.api_key = api_key
        self.memoria = memoria
        self.entidades = entidades
        self.historico = []
        self.acao_pendente = None
        self.conversa = conversation.ConversationState()

        self.entidade_contextual = (
            entity_store.obter_contexto_persistente(
                self.entidades
            )
        )

    def processar(self, mensagem):

        resultado = self._processar_interno(mensagem)

        return self._registrar_resultado_conversa(
            resultado
        )

    def _processar_interno(self, mensagem):

        mensagem_normalizada = unicodedata.normalize(
            "NFD",
            mensagem.strip().lower().rstrip("?!.,;: ")
        )
        mensagem_normalizada = "".join(
            caractere
            for caractere in mensagem_normalizada
            if unicodedata.category(caractere) != "Mn"
        )

        respostas_locais = {
            "oi stacy": "Olá, senhor. Estou pronta.",
            "ola stacy": "Olá, senhor. Estou pronta.",
            "olá stacy": "Olá, senhor. Estou pronta.",
            "como voce esta": "Estou operando normalmente, senhor. Pronta para continuar.",
            "como você está": "Estou operando normalmente, senhor. Pronta para continuar.",
            "teste": "Teste recebido, senhor. STACY está operacional.",
            "testar": "Teste recebido, senhor. STACY está operacional.",
            "teste stacy": "Teste recebido, senhor. STACY está operacional.",
            "oi": "Olá, senhor. Estou pronta.",
            "olá": "Olá, senhor. Estou pronta.",
            "ola": "Olá, senhor. Estou pronta.",
            "bom dia": "Bom dia, senhor. STACY está pronta.",
            "boa tarde": "Boa tarde, senhor. STACY está pronta.",
            "boa noite": "Boa noite, senhor. STACY está pronta.",
            "quem e voce": "Sou a STACY, sua assistente pessoal. Opero com um núcleo local e, quando necessário, uso recursos externos autorizados.",
            "o que voce e": "Sou a STACY, sua assistente pessoal.",
            "o que voce faz": "Posso ajudar com organização, tarefas, memória, estudos e conversação."
        }

        mensagem = mensagem.strip()

        if not mensagem:
            return {
                "tipo": "vazio"
            }

        # Toda mensagem recebida entra no estado conversacional, inclusive
        # saudações e respostas locais. Isso evita uma quebra silenciosa de
        # contexto depois de uma interação curta.
        self.conversa.registrar_mensagem(mensagem)

        if mensagem_normalizada in respostas_locais:
            return {
                "tipo": "local",
                "resposta": respostas_locais[mensagem_normalizada]
            }

        if not mensagem:
            return {
                "tipo": "vazio"
            }

        if self.acao_pendente is not None:

            confirmacao = _normalizar_confirmacao(mensagem)

            if confirmacao in {
                "sim", "s", "pode", "confirmo", "confirmado"
            }:

                acao = self.acao_pendente

                if acao.get("tipo") == "remover_tarefa":
                    resultado = tasks.remover(
                        acao["tarefa_id"]
                    )

                    self.acao_pendente = None

                    if resultado is None:
                        return {
                            "tipo": "erro_tarefa",
                            "resposta": (
                                "Não consegui remover "
                                "a tarefa, senhor."
                            )
                        }

                    return {
                        "tipo": "tarefa_removida",
                        "resposta": (
                            f"Removida, senhor: "
                            f"'{resultado['titulo']}'."
                        ),
                        "tarefa": resultado
                    }

                campos_colecao = [
                    "objetivos",
                    "projetos",
                    "preferencias"
                ]

                if acao.get("campo") in campos_colecao:

                    resultado = action.executar_adicao_em_colecao(
                        self.entidades,
                        acao.get("entidade_id"),
                        acao.get("campo"),
                        acao.get("valor")
                    )

                else:

                    resultado = action.executar(
                        acao,
                        self.entidades
                    )

                self.acao_pendente = None

                if resultado["status"] == "executada":

                    entidade = entity_store.obter_por_id(
                        self.entidades,
                        resultado["entidade_id"]
                    )

                    return {
                        "tipo": "acao_executada",
                        "resposta": (
                            f"Pronto, senhor. "
                            f"Atualizei '{resultado['campo']}' "
                            f"de {entidade['nome']} "
                            f"com '{resultado['valor']}'."
                        ),
                        "resultado": resultado
                    }

                if resultado["status"] == "ja_existente":

                    entidade = entity_store.obter_por_id(
                        self.entidades,
                        resultado["entidade_id"]
                    )

                    return {
                        "tipo": "acao_ja_existente",
                        "resposta": (
                            f"Senhor, '{resultado['valor']}' "
                            f"já estava registrado em "
                            f"'{resultado['campo']}' "
                            f"de {entidade['nome']}."
                        ),
                        "resultado": resultado
                    }

                return {
                    "tipo": "erro_acao",
                    "resposta": (
                        "Não consegui executar "
                        "a alteração, senhor."
                    ),
                    "resultado": resultado
                }

            if confirmacao in {
                "nao", "n", "cancele", "cancelar"
            }:

                self.acao_pendente = None

                return {
                    "tipo": "acao_cancelada",
                    "resposta": (
                        "Entendido, senhor. "
                        "A alteração foi cancelada."
                    )
                }

            # Uma mensagem diferente de confirmação não deve deixar uma ação
            # antiga armada para um futuro "sim". A consulta atual continua
            # normalmente, mas a confirmação anterior é descartada.
            self.acao_pendente = None

        # O roteador decide a origem antes de qualquer IA.
        # A classificação interna é prioritária para impedir que dados pessoais
        # ou tarefas sejam enviados à pesquisa externa por engano.
        comando = command.identificar_comando(mensagem)
        intencao = intent.interpretar(mensagem)

        rota_previa = classificar_rota(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=False
        )

        resposta_conhecimento = None
        if rota_previa != ROTA_INTERNA:
            texto_rota = _normalizar_rota(mensagem)
            gatilhos_externos = (
                "pesquise", "pesquisar", "pesquisa na internet",
                "procure", "busque", "pesquisa no google",
                "procure no google", "na internet", "no google"
            )
            gatilhos_fontes = (
                "me de fontes", "me dê fontes", "com fontes",
                "cite fontes", "fontes sobre", "fontes para"
            )
            pesquisa_explicita = (
                any(_contem_termo(texto_rota, gatilho)
                    for gatilho in gatilhos_externos)
                or any(_contem_termo(texto_rota, gatilho)
                       for gatilho in gatilhos_fontes)
            )

            if not pesquisa_explicita:
                resposta_conhecimento = knowledge.consultar(mensagem)
                if resposta_conhecimento is None:
                    resposta_conhecimento = knowledge.consultar_contextual(
                        mensagem,
                        self.conversa.ultimas_mensagens(6)
                    )

        rota = classificar_rota(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=resposta_conhecimento is not None
        )

        if rota == ROTA_CONHECIMENTO:
            return {
                "tipo": "conhecimento_verificado",
                "resposta": resposta_conhecimento,
                "origem": "core",
                "rota": rota
            }

        if rota == ROTA_PESQUISA_EXTERNA:
            return self._pesquisar_web(mensagem)

        # Rotas internas continuam pelo CORE abaixo, onde memória, tarefas,
        # entidades e ações são executadas sem passar por modelos.

        entidade_detectada = entity_resolver.resolver(
            mensagem,
            self.entidades,
            self.entidade_contextual
        )

        if (
            entidade_detectada is not None
            and entidade_detectada.get("status") == "encontrada"
        ):

            entidade = entidade_detectada.get("entidade")

            if entidade is not None:

                self._atualizar_contexto(
                    entidade
                )

                self.conversa.registrar_entidade(
                    entidade["id"]
                )

        # Consultas simples de memória devem ser resolvidas pelo CORE
        # antes de contexto/IA, evitando que o modelo invente dados.
        if (
            isinstance(intencao, dict)
            and intencao.get("tipo") == "memoria"
            and intencao.get("acao") == "consultar"
        ):
            resultado_memoria = self._processar_intencao(intencao)
            if resultado_memoria is not None:
                return resultado_memoria

        resultado_tarefa = self._processar_tarefa(
            intencao
        )

        if resultado_tarefa is not None:
            return resultado_tarefa

        entidade_atual = None

        if self.entidade_contextual is not None:

            entidade_atual = entity_store.obter_por_id(
                self.entidades,
                self.entidade_contextual["id"]
            )

        if entidade_atual is not None:

            acao_candidata = action.detectar_atualizacao(
                mensagem,
                entidade_atual
            )

            if acao_candidata is not None:

                acao = action.interpretar_atualizacao(
                    acao_candidata
                )

                if acao is not None:

                    self.acao_pendente = acao

                    self.conversa.registrar_acao(
                        acao
                    )

                    return {
                        "tipo": "acao_candidata",
                        "resposta": (
                            f"Entendi, senhor. "
                            f"Posso atualizar "
                            f"'{acao['campo']}' "
                            f"de {entidade_atual['nome']} "
                            f"com '{acao['valor']}'. "
                            f"Deseja confirmar?"
                        ),
                        "acao": acao,
                        "entidade": entidade_atual
                    }

        contexto = context.interpretar_contexto(
            mensagem,
            entity_store,
            self.entidades
        )

        if contexto is not None:

            self._atualizar_contexto(
                contexto["entidade"]
            )

            self.conversa.registrar_entidade(
                contexto["entidade"]["id"]
            )

            resultado = context.resolver_consulta(
                contexto
            )

            if resultado is not None:

                resposta = self._formatar_contexto(
                    contexto,
                    resultado
                )

                if resposta is not None:

                    return {
                        "tipo": "local",
                        "resposta": resposta,
                        "contexto": contexto,
                        "resultado": resultado
                    }

        if comando is not None:

            if comando == "sair":

                return {
                    "tipo": "sair"
                }

        if intencao is not None:

            self.conversa.registrar_intencao(
                intencao
            )

            resultado_intencao = self._processar_intencao(
                intencao
            )

            if resultado_intencao is not None:

                return resultado_intencao

        # Se chegou aqui, a rota definida é IA local. A pesquisa externa
        # nunca é acionada implicitamente depois desta decisão.
        if rota == ROTA_INTERNA:
            return {
                "tipo": "local",
                "resposta": (
                    "Entendi que o senhor está falando de dados internos da STACY, "
                    "mas não consegui identificar a operação solicitada. "
                    "Nenhuma pesquisa externa ou IA foi acionada."
                ),
                "rota": rota
            }

        return self._usar_ai(mensagem)

    def _registrar_resultado_conversa(self, resultado):
        if not isinstance(resultado, dict):
            return resultado

        resposta = resultado.get("resposta")

        if resposta is not None:
            self.conversa.registrar_resposta(resposta)

        if resultado.get("entidade") is not None:
            entidade = resultado.get("entidade")
            entidade_id = entidade.get("id")

            if entidade_id is not None:
                self.conversa.registrar_entidade(
                    entidade_id
                )

        if resultado.get("acao") is not None:
            self.conversa.registrar_acao(
                resultado.get("acao")
            )

        if resultado.get("intencao") is not None:
            self.conversa.registrar_intencao(
                resultado.get("intencao")
            )

        return resultado

    def _atualizar_contexto(
        self,
        entidade
    ):

        identificador = entidade.get(
            "id"
        )

        if not identificador:

            return

        contexto = (
            entity_store.definir_contexto_persistente(
                self.entidades,
                identificador
            )
        )

        if contexto is not None:

            self.entidade_contextual = contexto

    def _formatar_contexto(
        self,
        contexto,
        resultado
    ):

        status = resultado.get(
            "status"
        )

        entidade = contexto.get(
            "entidade",
            {}
        )

        nome = entidade.get(
            "nome",
            "essa entidade"
        )

        if status == "encontrada":

            atributo = resultado.get(
                "atributo"
            )

            valor = resultado.get(
                "valor"
            )

            if atributo == "nome":

                return (
                    f"O nome é {valor}, senhor."
                )

            if atributo == "objetivo_principal":

                return (
                    f"O objetivo do {nome} "
                    f"é {valor}, senhor."
                )

            return (
                f"O valor de {atributo} "
                f"para {nome} é {valor}, senhor."
            )

        if status == "nao_encontrado":

            atributo = resultado.get(
                "atributo"
            )

            return (
                f"Não encontrei o atributo "
                f"'{atributo}' registrado "
                f"para {nome}, senhor."
            )

        if status == "entidade_completa":

            linhas = [
                f"Tenho estas informações "
                f"sobre {nome}, senhor.",
                f"• ID: {resultado.get('entidade_id')}",
                f"• Categoria: {resultado.get('categoria')}"
            ]

            atributos = resultado.get(
                "atributos",
                {}
            )

            for chave, valor in atributos.items():

                linhas.append(
                    f"• {chave}: {valor}"
                )

            return "\\n".join(linhas)

        return None

    def _processar_intencao(
        self,
        intencao
    ):

        if intencao.get("tipo") != "memoria":

            return None

        acao = intencao.get(
            "acao"
        )

        categoria = intencao.get(
            "categoria"
        )

        valor = intencao.get(
            "valor"
        )

        if acao == "memorizar":

            if not categoria or not valor:
                return None

            sucesso = memory.registrar_memoria(
                categoria,
                valor,
                self.memoria
            )

            if sucesso:

                return {
                    "tipo": "local",
                    "resposta": (
                        f"Guardado, senhor. Registrei '{valor}' "
                        f"em '{categoria}'."
                    ),
                    "memoria": {
                        "categoria": categoria,
                        "valor": valor
                    }
                }

            return {
                "tipo": "local",
                "resposta": (
                    f"Senhor, '{valor}' já estava registrado "
                    f"em '{categoria}' ou o formato informado é inválido."
                )
            }

        if acao == "esquecer":

            if not categoria or not valor:
                return None

            sucesso = memory.esquecer_memoria(
                categoria,
                valor,
                self.memoria
            )

            if sucesso:

                return {
                    "tipo": "local",
                    "resposta": (
                        f"Informação '{valor}' removida "
                        "da memória, senhor."
                    )
                }

            return {
                "tipo": "local",
                "resposta": (
                    f"Não encontrei '{valor}' em '{categoria}', "
                    "senhor. Nenhuma informação foi alterada."
                )
            }

        if acao == "mostrar":

            return {
                "tipo": "local",
                "resposta": memory.mostrar_memoria(
                    self.memoria
                )
            }

        if acao == "consultar":

            if not categoria:
                return None

            dados = memory.buscar_memoria(
                categoria,
                self.memoria
            )

            if not dados:

                return {
                    "tipo": "local",
                    "resposta": (
                        f"Não há registros em "
                        f"'{categoria}', senhor."
                    )
                }

            if categoria == "usuario":

                linhas = [
                    f"{chave}: {valor}"
                    for chave, valor in dados.items()
                ]

                resposta = (
                    "Estas são as informações do senhor "
                    "que estão na memória:\n"
                    + "\n".join(
                        f"• {linha}"
                        for linha in linhas
                    )
                )

            else:

                resposta = (
                    f"Seus {categoria}, senhor:\n"
                    + "\n".join(
                        f"• {item}"
                        for item in dados
                    )
                )

            return {
                "tipo": "local",
                "resposta": resposta,
                "categoria": categoria,
                "dados": dados
            }

        if acao == "buscar":

            valor_busca = (
                intencao.get("valor")
                or intencao.get("conteudo")
            )

            if not valor_busca:
                return None

            resultados = memory.buscar_por_texto(
                self.memoria,
                valor_busca
            )

            if not resultados:

                return {
                    "tipo": "local",
                    "resposta": (
                        f"Não encontrei '{valor_busca}' "
                        f"na memória, senhor."
                    )
                }

            linhas = []

            for resultado in resultados:

                categoria_resultado = resultado.get(
                    "categoria"
                )

                memoria_item = resultado.get(
                    "memoria"
                )

                valor_resultado = (
                    memory.obter_valor_memoria(
                        memoria_item
                    )
                )

                linhas.append(
                    f"• {categoria_resultado}: "
                    f"{valor_resultado}"
                )

            return {
                "tipo": "local",
                "resposta": (
                    "Encontrei estas informações "
                    "na memória, senhor:\n"
                    + "\n".join(linhas)
                ),
                "resultados": resultados
            }

        return None

    def _processar_tarefa(self, intencao):

        if not isinstance(intencao, dict):
            return None

        if intencao.get("tipo") != "tarefa":
            return None

        acao = intencao.get("acao")

        if acao == "criar":

            titulo = intencao.get("titulo")
            data = intencao.get("data")
            hora = intencao.get("hora")

            if not titulo:
                return None

            tarefa = tasks.criar(
                titulo,
                data,
                hora
            )

            if tarefa is None:
                return {
                    "tipo": "erro_tarefa",
                    "resposta": (
                        "Não consegui criar essa tarefa, senhor."
                    )
                }

            return {
                "tipo": "tarefa_criada",
                "resposta": (
                    f"Tarefa criada, senhor: "
                    f"'{tarefa['titulo']}'."
                ),
                "tarefa": tarefa
            }

        if acao == "listar":

            data = intencao.get("data")

            tarefas = tasks.listar(
                data=data
            )

            if not tarefas:

                if data:
                    return {
                        "tipo": "tarefas",
                        "resposta": (
                            f"O senhor não possui "
                            f"tarefas pendentes para {data}."
                        ),
                        "tarefas": []
                    }

                return {
                    "tipo": "tarefas",
                    "resposta": (
                        "O senhor não possui "
                        "tarefas pendentes."
                    ),
                    "tarefas": []
                }

            linhas = [
                "Estas são suas tarefas pendentes, senhor:"
            ]

            for tarefa in tarefas:

                linha = (
                    f"• {tarefa['titulo']}"
                )

                if tarefa.get("data"):
                    linha += (
                        f" — {tarefa['data']}"
                    )

                if tarefa.get("hora"):
                    linha += (
                        f" às {tarefa['hora']}"
                    )

                linhas.append(linha)

            return {
                "tipo": "tarefas",
                "resposta": "\n".join(linhas),
                "tarefas": tarefas
            }

        if acao in ["concluir", "remover"]:

            termo = intencao.get("termo")

            if not termo:
                return None

            if acao == "concluir":
                encontrados = tasks.buscar(
                    termo,
                    status="pendente"
                )
            else:
                encontrados = tasks.buscar(
                    termo
                )

            if not encontrados:

                return {
                    "tipo": "tarefa_nao_encontrada",
                    "resposta": (
                        f"Não encontrei uma tarefa "
                        f"correspondente a '{termo}', senhor."
                    )
                }

            if len(encontrados) > 1:

                return {
                    "tipo": "tarefa_ambigua",
                    "resposta": (
                        "Encontrei mais de uma tarefa "
                        "correspondente. Poderia especificar "
                        "qual delas deseja?"
                    ),
                    "tarefas": encontrados
                }

            tarefa = encontrados[0]

            if acao == "concluir":

                resultado = tasks.concluir(
                    tarefa["id"]
                )

                return {
                    "tipo": "tarefa_concluida",
                    "resposta": (
                        f"Concluída, senhor: "
                        f"'{resultado['titulo']}'."
                    ),
                    "tarefa": resultado
                }

            self.acao_pendente = {
                "tipo": "remover_tarefa",
                "tarefa_id": tarefa["id"],
                "tarefa": tarefa
            }

            return {
                "tipo": "confirmacao",
                "resposta": (
                    f"Senhor, confirma a remoção da tarefa "
                    f"'{tarefa['titulo']}'? "
                    f"Esta ação não poderá ser desfeita."
                ),
                "tarefa": tarefa
            }

        return None

    def _pesquisar_web(self, mensagem):
        self.historico.append({
            "role": "user",
            "parts": [{"text": mensagem}]
        })

        # Pesquisa externa recebe somente a consulta atual.
        # Memória persistente e conversa pessoal não são enviadas ao provedor.
        historico_pesquisa = [
            {
                "role": "user",
                "parts": [{"text": mensagem}]
            }
        ]

        try:
            resultado = ai.gerar_resposta_pesquisa(
                self.api_key,
                historico_pesquisa
            )
        except Exception as erro:
            # Pesquisa externa não cai na IA local: isso preserva a regra
            # de não inventar fatos quando a fonte externa está indisponível.
            return {
                "tipo": "pesquisa_indisponivel",
                "resposta": (
                    "Não consegui consultar fontes externas agora, senhor. "
                    "Não vou inventar uma resposta."
                ),
                "origem": "gemini_google",
                "erro": str(erro)
            }

        resposta = resultado["resposta"]
        fontes = resultado.get("fontes", [])

        self.historico.append({
            "role": "model",
            "parts": [{"text": resposta}]
        })

        return {
            "tipo": "pesquisa",
            "resposta": resposta,
            "origem": "gemini_google",
            "fontes": fontes
        }

    def _usar_ai(
        self,
        mensagem
    ):

        self.historico.append({
            "role": "user",
            "parts": [
                {
                    "text": mensagem
                }
            ]
        })

        contexto_memoria = json.dumps(
            self.memoria,
            ensure_ascii=False,
            indent=2
        )

        contexto_entidade = None

        if self.entidade_contextual is not None:

            entidade = entity_store.obter_por_id(
                self.entidades,
                self.entidade_contextual["id"]
            )

            if entidade is not None:

                contexto_entidade = json.dumps(
                    entidade,
                    ensure_ascii=False,
                    indent=2
                )

        contexto_conversa = json.dumps(
            self.conversa.ultimas_mensagens(6),
            ensure_ascii=False,
            indent=2
        )

        erros = []

        try:
            if not ai.verificar_ia_local():
                raise RuntimeError(
                    "servidor local não está acessível"
                )

            resposta = ai.gerar_resposta_local(
                self.historico,
                contexto_memoria,
                contexto_entidade,
                contexto_conversa
            )

            origem = "local"

        except Exception as erro_local:

            erros.append(f"IA local: {erro_local}")

            print(
                "[STACY] IA local indisponível; "
                "tentando Gemini como fallback..."
            )

            try:
                resposta = ai.gerar_resposta(
                    self.api_key,
                    self.historico,
                    contexto_memoria,
                    contexto_entidade,
                    contexto_conversa
                )

                origem = "gemini"

            except Exception as erro_gemini:

                erros.append(f"Gemini: {erro_gemini}")

                raise RuntimeError(
                    "Não consegui obter uma resposta da IA agora, senhor. "
                    "A IA local está indisponível e o Gemini não respondeu dentro do tempo esperado."
                ) from erro_gemini

        self.historico.append({
            "role": "model",
            "parts": [
                {
                    "text": resposta
                }
            ]
        })

        return {
            "tipo": "ai",
            "resposta": resposta,
            "origem": origem
        }