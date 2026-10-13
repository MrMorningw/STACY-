import json
import re
import unicodedata
from difflib import SequenceMatcher
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
import cortex
import ctac
import mepo
import orchestration
import autonomy




ROTA_INTERNA = "interno"
ROTA_CONHECIMENTO = "conhecimento_core"
ROTA_IA_LOCAL = "ia_local"
ROTA_PESQUISA_EXTERNA = "pesquisa_externa"


def _normalizar_rota(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)

    caracteres = []
    for caractere in texto:
        categoria = unicodedata.category(caractere)

        if categoria == "Mn":
            continue

        if categoria.startswith("P"):
            caracteres.append(" ")
        else:
            caracteres.append(caractere)

    texto = " ".join("".join(caracteres).split())

    # Corrige apenas palavras do vocabulário de roteamento. Isso dá
    # tolerância a erros de digitação sem transformar perguntas concretas
    # em respostas pré-programadas.
    vocabulario = (
        "quanto", "quantos", "quantas", "qual",
        "quem", "quando", "onde", "capital", "populacao",
        "idade", "tamanho", "temperatura", "distancia",
        "massa", "velocidade", "vive", "vivem", "teve", "tinham",
        "existem", "tem", "possui", "possuem", "sao", "ha",
        "quais", "criterios", "classificacao", "requisitos",
        "condicoes", "considerado", "precisa", "deve", "devem"
    )
    tokens = []
    for token in texto.split():
        melhor = token
        melhor_similaridade = 0.0
        for candidato in vocabulario:
            if len(token) < 4 or len(candidato) < 4:
                continue
            similaridade = SequenceMatcher(None, token, candidato).ratio()
            if similaridade > melhor_similaridade:
                melhor_similaridade = similaridade
                melhor = candidato
        if melhor_similaridade >= 0.80:
            tokens.append(melhor)
        else:
            tokens.append(token)

    return " ".join(tokens)


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

    # 3) CONHECIMENTO VERIFICADO: depois de pesquisa explícita e das
    # operações internas, uma resposta já confirmada pelo CORE tem prioridade
    # sobre qualquer rota implícita de pesquisa.
    if conhecimento:
        return ROTA_CONHECIMENTO

    # 4) PESQUISA IMPLÍCITA: atualidade ou fatos externos verificáveis.
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
        "qual e a populacao de", "qual a capital de",
        "qual e a capital de", "qual a capital da",
        "qual e a capital da", "qual a temperatura de",
        "qual e a temperatura de", "qual a distancia de",
        "qual e a distancia de", "qual a massa de",
        "qual e a massa de", "qual a velocidade de",
        "qual e a velocidade de", "qual o preco de",
        "qual e o preco de", "quanto custa", "quanto vale",
        "qual o valor de", "qual e o valor de", "qual a data de",
        "qual e a data de", "em que ano", "qual a altura de",
        "qual e a altura de", "qual a profundidade de",
        "qual e a profundidade de", "tem quantas luas",
        "possui quantas luas"
    )
    if any(padrao in texto for padrao in padroes_factuais):
        return ROTA_PESQUISA_EXTERNA

    # Perguntas sobre critérios/requisitos/classificação pedem fatos e
    # definições verificáveis. Elas devem sair para pesquisa externa quando
    # não forem atendidas pelo CORE, sem depender do assunto específico.
    padroes_traducao = (
        "como se diz ",
        "como se fala ",
        "como falar ",
        "traduza ",
        "traduz ",
        "traducao de ",
        "tradução de "
    )
    if any(padrao in texto for padrao in padroes_traducao):
        return ROTA_PESQUISA_EXTERNA

    padroes_criterios = (
        "criterios para",
        "criterios de",
        "requisitos para",
        "requisitos de",
        "condicoes para",
        "condicoes de",
        "criterios de classificacao",
        "criterios para classificacao",
        "como e classificado",
        "como sao classificados",
        "como se classifica",
        "o que caracteriza"
    )
    if any(padrao in texto for padrao in padroes_criterios):
        return ROTA_PESQUISA_EXTERNA

    # 5) PESQUISA IMPLÍCITA: perguntas quantitativas factuais que não
    # possuem resposta verificada no CORE.
    padroes_quantitativos = (
        "quanto tempo ",
        "quantos anos ",
        "quantos ",
        "quantas ",
        "quanto custa ",
        "quanto vale ",
        "qual o preco de ",
        "qual e o preco de ",
        "qual o valor de ",
        "qual e o valor de ",
    )
    verbos_quantitativos = (
        " vive", " vivem", " teve", " tinham", " tem",
        " possui", "possuem", " existem", " sao", " são",
        " ha", " há", " precisa", " devem", " deve",
        " precisa ter", " tem que", " deve ter"
    )
    if any(padrao in texto for padrao in padroes_quantitativos):
        if any(verbo in texto for verbo in verbos_quantitativos):
            return ROTA_PESQUISA_EXTERNA

    # Traduções exatas devem ser verificadas externamente quando o pedido
    # exige uma língua específica. A IA local permanece para explicações
    # linguísticas e conversas sobre linguagem.
    padroes_traducao = (
        "como se diz ", "como se fala ",
        "como traduzir ", "traduza "
    )
    if any(padrao in texto for padrao in padroes_traducao):
        return ROTA_PESQUISA_EXTERNA

    # Alguns fatos simples são verificáveis externamente, mas não devem
    # impedir uma resposta determinística do CORE quando ela já existir.
    # Ex.: "qual a cor de uma abobora?" pesquisa; "qual a cor de um gato
    # preto?" pode ser respondida pelo conhecimento verificado do CORE.
    # A pesquisa explícita já foi tratada acima; aqui, conhecimento verificado
    # pelo CORE deve vencer somente os padrões implícitos.
    if conhecimento:
        return ROTA_CONHECIMENTO

    padroes_fato_externo_simples = (
        "qual a cor de ",
        "qual e a cor de ",
        "qual a cor do ",
        "qual e a cor do ",
        "qual a diferenca entre ",
        "qual e a diferenca entre ",
        "onde fica ",
        "quando foi ",
        "quem foi ",
    )
    if any(padrao in texto for padrao in padroes_fato_externo_simples):
        return ROTA_PESQUISA_EXTERNA

    # Perguntas conceituais, explicativas e triviais sem um padrão factual
    # específico permanecem na IA local, salvo quando o usuário pedir
    # pesquisa/fonte ou houver marcador de atualidade tratado acima.
    padroes_fato_comum = (
        "qual o nome ",
        "qual e o nome ",
        "qual o aumentativo de ",
        "qual e o aumentativo de ",
        "qual o diminutivo de ",
        "qual e o diminutivo de ",
        "como se chama ",
        "qual o significado de ",
        "qual e o significado de ",
    )
    if any(padrao in texto for padrao in padroes_fato_comum):
        return ROTA_PESQUISA_EXTERNA

    # Pedidos por um exemplo factual também não devem ser respondidos
    # por chute quando o CORE não possui o fato verificado.
    padroes_exemplo_factual = (
        "me diga uma ave ",
        "me diga um animal ",
        "me diga uma fruta ",
        "me diga um pais ",
        "me diga uma cidade ",
        "diga uma ave ",
        "diga um animal ",
        "diga uma fruta ",
        "diga um pais ",
        "diga uma cidade ",
    )
    if any(padrao in texto for padrao in padroes_exemplo_factual):
        return ROTA_PESQUISA_EXTERNA

    # 7) IA LOCAL: conversa, estudo e raciocínio sem necessidade externa.
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
        self.ultima_decisao = None
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


    def _processar_anpes(self, mensagem):
        texto = _normalizar_rota(mensagem)
        consultas = {
            "status do anpes", "estado do anpes", "situacao do anpes",
            "status do nucleo anpes", "estado do nucleo anpes",
            "status do nucleo", "estado do nucleo",
            "o que e anpes", "o que e o anpes", "o que faz o anpes",
        }
        if texto not in consultas:
            return None

        estado = autonomy.anpes_estado()
        resposta = (
            "ANPES está integrado ao gate de autonomia do CORE, senhor. "
            "A validação de planos está disponível, com simulação por padrão "
            "e limite de oito etapas. A execução de planos ainda exige "
            "executores explicitamente registrados; esta consulta não executa "
            "ações. O núcleo não executa shell arbitrário nem se modifica sozinho."
        )
        return {
            "tipo": "anpes_status",
            "resposta": resposta,
            "anpes": estado,
            "rota": ROTA_INTERNA,
        }

    def _processar_ctac_mepo(self, mensagem):
        texto = _normalizar_rota(mensagem)
        consultas_ctac = (
            "ctac", "o que e ctac", "o que e o ctac",
            "status do ctac", "estado do ctac", "situacao do ctac",
            "coerencia da trajetoria"
        )
        consultas_mepo = (
            "mepos", "mepos atuais", "quais mepos", "quais sao os mepos",
            "quais sao meus mepos", "qual meu mepo", "qual e meu mepo",
            "qual o mepo atual", "qual e o mepo atual", "status dos mepos"
        )
        if texto in consultas_ctac or "status do ctac" in texto or "estado do ctac" in texto:
            validacao = ctac.validar_coerencia()
            return {
                "tipo": "ctac", "resposta": ctac.formatar_estado(),
                "estado_ctac": validacao, "rota": ROTA_INTERNA
            }
        if texto in consultas_mepo or "quais sao os mepos" in texto:
            return {
                "tipo": "mepos", "resposta": ctac.formatar_mepos(),
                "mepos": mepo.listar(), "rota": ROTA_INTERNA
            }
        return None

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

        if self.acao_pendente is None and mensagem_normalizada in respostas_locais:
            return {
                "tipo": "local",
                "resposta": respostas_locais[mensagem_normalizada]
            }

        # Tolerância geral para pequenas falhas de digitação em frases locais.
        for frase, resposta in respostas_locais.items():
            if self.acao_pendente is None and len(mensagem_normalizada) >= 6:
                similaridade = SequenceMatcher(
                    None,
                    mensagem_normalizada,
                    frase
                ).ratio()
                if similaridade >= 0.88:
                    return {
                        "tipo": "local",
                        "resposta": resposta
                    }

        if not mensagem:
            return {
                "tipo": "vazio"
            }

        if self.acao_pendente is not None:

            confirmacao = _normalizar_confirmacao(mensagem)

            acao = self.acao_pendente

            if confirmacao in {
                "sim", "s", "pode", "confirmo", "confirmado"
            }:

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
                            ),
                            "acao": acao
                        }

                    return {
                        "tipo": "tarefa_removida",
                        "resposta": (
                            f"Removida, senhor: "
                            f"'{resultado['titulo']}'."
                        ),
                        "tarefa": resultado,
                        "acao": acao
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

                status = resultado.get("status") if isinstance(resultado, dict) else None

                if status == "executada":

                    entidade = entity_store.obter_por_id(
                        self.entidades,
                        resultado.get("entidade_id")
                    )

                    if entidade is None:
                        return {
                            "tipo": "erro_acao",
                            "resposta": (
                                "A ação foi processada, mas a entidade "
                                "não está mais disponível, senhor."
                            ),
                            "resultado": resultado
                        }

                    return {
                        "tipo": "acao_executada",
                        "resposta": (
                            f"Pronto, senhor. "
                            f"Atualizei '{resultado['campo']}' "
                            f"de {entidade['nome']} "
                            f"com '{resultado['valor']}'."
                        ),
                        "resultado": resultado,
                        "acao": acao
                    }

                if status == "ja_existente":

                    entidade = entity_store.obter_por_id(
                        self.entidades,
                        resultado.get("entidade_id")
                    )

                    if entidade is None:
                        return {
                            "tipo": "erro_acao",
                            "resposta": (
                                "A informação já estava registrada, "
                                "mas a entidade não está mais disponível, senhor."
                            ),
                            "resultado": resultado
                        }

                    return {
                        "tipo": "acao_ja_existente",
                        "resposta": (
                            f"Senhor, '{resultado.get('valor')}' "
                            f"já estava registrado em "
                            f"'{resultado.get('campo')}' "
                            f"de {entidade.get('nome', 'essa entidade')}."
                        ),
                        "resultado": resultado,
                        "acao": acao
                    }

                return {
                    "tipo": "erro_acao",
                    "resposta": (
                        "Não consegui executar "
                        "a alteração, senhor."
                    ),
                    "resultado": resultado,
                    "acao": acao
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
                    ),
                    "acao": acao
                }

            # Uma mensagem diferente de confirmação invalida a operação
            # pendente e seu estado operacional temporário.
            self.acao_pendente = None
            self.conversa.limpar_operacao()

            # Reprocessa respostas locais depois de descartar a operação antiga.
            if mensagem_normalizada in respostas_locais:
                return {
                    "tipo": "local",
                    "resposta": respostas_locais[mensagem_normalizada]
                }

            for frase, resposta in respostas_locais.items():
                if len(mensagem_normalizada) >= 6:
                    similaridade = SequenceMatcher(
                        None,
                        mensagem_normalizada,
                        frase
                    ).ratio()
                    if similaridade >= 0.88:
                        return {
                            "tipo": "local",
                            "resposta": resposta
                        }

        # Consultas sobre a própria conversa são determinísticas.
        # Nunca devem depender de conhecimento externo ou de uma IA pequena.
        consulta_conversa = self._resolver_consulta_conversa(mensagem)
        if consulta_conversa is not None:
            return consulta_conversa

        # O roteador decide a origem antes de qualquer IA.
        # A classificação interna é prioritária para impedir que dados pessoais
        # ou tarefas sejam enviados à pesquisa externa por engano.
        #
        # Antes da classificação factual, porém, consultas de entidade que já
        # possuem um referente na conversa devem passar pelo resolvedor local.
        # Ex.: depois de "STACY", "qual o nome dela?" é uma consulta de contexto,
        # não uma nova pesquisa na Web.
        entidade_contextual_conversa = None
        entidade_conversa_id = self.conversa.obter_ultima_entidade()

        if entidade_conversa_id:
            entidade_contextual_conversa = entity_store.obter_por_id(
                self.entidades,
                entidade_conversa_id
            )

        if entidade_contextual_conversa is not None:
            contexto_previo = context.interpretar_contexto(
                mensagem,
                entity_store,
                self.entidades,
                contexto_atual=entidade_contextual_conversa
            )

            if contexto_previo is not None:
                resultado_previo = context.resolver_consulta(
                    contexto_previo
                )

                if (
                    resultado_previo is not None
                    and resultado_previo.get("status") == "encontrada"
                ):
                    resposta_previa = self._formatar_contexto(
                        contexto_previo,
                        resultado_previo
                    )

                    if resposta_previa is not None:
                        self._atualizar_contexto(
                            contexto_previo["entidade"]
                        )
                        return {
                            "tipo": "local",
                            "resposta": resposta_previa,
                            "contexto": contexto_previo,
                            "resultado": resultado_previo
                        }

        # Uma mensagem sem referente, nome da entidade ou marcador de
        # continuidade encerra o contexto conversacional temporário. A memória
        # persistente permanece intacta.
        if not self._deve_preservar_entidade_conversacional(mensagem):
            self.conversa.limpar_entidade()

        comando = command.identificar_comando(mensagem)
        intencao = intent.interpretar(mensagem)

        # A identidade da STACY pertence ao próprio sistema, não à memória
        # do usuário nem à pesquisa externa.
        if (
            isinstance(intencao, dict)
            and intencao.get("tipo") == "identidade"
            and intencao.get("alvo") == "stacy"
        ):
            return {
                "tipo": "local",
                "resposta": (
                    "Sou a STACY, senhor. Sua assistente pessoal."
                ),
                "rota": ROTA_INTERNA
            }

        # Memória estruturada é responsabilidade exclusiva do CORE.
        # Execute consultas de memória imediatamente após a interpretação,
        # antes do Cortex poder classificá-las como perguntas factuais.
        if (
            isinstance(intencao, dict)
            and intencao.get("tipo") == "memoria"
        ):
            resultado_memoria = self._processar_intencao(intencao)
            if resultado_memoria is not None:
                return resultado_memoria

        # Continuidade operacional: se a mensagem fornece apenas data/hora,
        # aplica a alteração à última tarefa criada, sem exigir que o usuário
        # repita o título.
        continuacao_tarefa = self._resolver_continuacao_tarefa(mensagem)
        if continuacao_tarefa is not None:
            intencao = continuacao_tarefa

        # Intenções de tarefa já reconhecidas pelo parser são operações
        # determinísticas. Execute-as imediatamente, antes de Cortex, IA,
        # conhecimento ou resolução contextual poderem alterar a leitura.
        resultado_tarefa = self._processar_tarefa(intencao)
        if resultado_tarefa is not None:
            return resultado_tarefa

        # O estado do ANPES é diagnóstico determinístico e não deve passar por IA/Web.
        resultado_anpes = self._processar_anpes(mensagem)
        if resultado_anpes is not None:
            return resultado_anpes

        # CTAC/MEPO é contexto interno da trajetória: não passa por IA/Web.
        resultado_ctac = self._processar_ctac_mepo(mensagem)
        if resultado_ctac is not None:
            return resultado_ctac

        # Somente depois de comandos/tarefas determinísticos, tratamos uma
        # referência sem referente ativo como conversa para esclarecimento.
        # Assim, "crie essa tarefa" continua sendo processado pelo CORE,
        # enquanto "qual o nome dela?" após mudança de assunto não ressuscita
        # pesquisa externa anterior.
        texto_referencia = f" {_normalizar_rota(mensagem)} "
        pronomes_sem_referente = (
            "ele", "ela", "dele", "dela", "eles", "elas",
            "deles", "delas", "esse", "essa", "isso",
            "aquele", "aquela", "aquilo"
        )
        tem_pronome_sem_entidade = (
            not self.conversa.obter_ultima_entidade()
            and any(
                _contem_termo(texto_referencia, pronome)
                for pronome in pronomes_sem_referente
            )
        )

        if tem_pronome_sem_entidade:
            return self._usar_ai(mensagem)

        # O modelo local faz a interpretação semântica quando o CORE
        # ainda não identificou uma operação. O Cortex continua sendo apenas
        # coordenador/validador; a IA não recebe autoridade para executar.
        decisao_ia = None
        # Não acione o modelo local quando o roteador determinístico já sabe
        # que a mensagem é interna ou exige pesquisa externa. Isso evita
        # chamadas desnecessárias e, principalmente, evita esperar o timeout
        # do llama-server em testes e em consultas que já têm rota definida.
        rota_inicial = classificar_rota(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=False
        )
        palavras_roteamento = (
            "crie", "criar", "adicione", "adicionar", "anote", "anotar",
            "lembre", "lembrar", "guarde", "guardar", "memorize", "memorizar",
            "esqueça", "esqueca", "apague", "apagar", "remova", "remover",
            "delete", "exclua", "excluir", "conclua", "concluir",
            "atualize", "atualizar", "corrija", "corrigir", "arrume", "arrumar",
            "altere", "alterar", "mude", "mudar", "troque", "trocar",
            "coloque", "colocar", "registre", "registrar", "faça", "faca"
        )
        texto_roteamento = _normalizar_rota(mensagem)
        precisa_roteador_local = any(
            texto_roteamento.startswith(palavra + " ")
            or texto_roteamento == palavra
            for palavra in palavras_roteamento
        ) or any(
            _contem_termo(texto_roteamento, referencia)
            for referencia in (
                "essa tarefa", "esta tarefa", "ultima tarefa",
                "última tarefa", "exclua ela", "apague ela", "remova ela"
            )
        )

        if (
            intencao is None
            and comando is None
            and rota_inicial == ROTA_IA_LOCAL
            and precisa_roteador_local
        ):
            contexto_router = json.dumps(
                self.conversa.ultimas_mensagens(4),
                ensure_ascii=False
            )
            try:
                decisao_ia = ai.analisar_rota_local(
                    mensagem,
                    contexto_router
                )
            except Exception:
                # Falha do intérprete não derruba a STACY. O Cortex
                # determinístico continua como fallback.
                decisao_ia = None

        decisao = cortex.analisar(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=False,
            decisao_ia=decisao_ia
        )
        if (
            isinstance(decisao, dict)
            and decisao.get("modo") == "clarify"
        ):
            return {
                "tipo": "clarificacao",
                "resposta": (
                    "Preciso de um pouco mais de informação para entender "
                    "o que o senhor deseja fazer."
                ),
                "rota": ROTA_IA_LOCAL
            }

        # Converte somente decisões estruturadas do intérprete em intenções
        # executáveis. O modelo nunca executa diretamente.
        if (
            isinstance(decisao, dict)
            and decisao.get("ferramenta") in {"tasks", "memory"}
        ):
            argumentos_ia = decisao.get("argumentos", {})
            if isinstance(argumentos_ia, dict):
                if decisao.get("ferramenta") == "tasks":
                    dados_tarefa = {
                        chave: valor
                        for chave, valor in argumentos_ia.items()
                        if chave in {"acao", "titulo", "data", "hora", "termo", "tarefa_id"}
                        and valor not in (None, "")
                    }
                    if dados_tarefa.get("acao"):
                        intencao = {
                            "tipo": "tarefa",
                            "origem": autonomy.ORIGEM_IA,
                            **dados_tarefa
                        }
                elif decisao.get("ferramenta") == "memory":
                    dados_memoria = {
                        chave: valor
                        for chave, valor in argumentos_ia.items()
                        if chave in {"acao", "categoria", "valor", "conteudo"}
                        and valor not in (None, "")
                    }
                    if dados_memoria.get("acao"):
                        intencao = {
                            "tipo": "memoria",
                            "origem": autonomy.ORIGEM_IA,
                            **dados_memoria
                        }

        self.ultima_decisao = cortex.analisar(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=False
        )

        rota_previa = classificar_rota(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=False
        )

        consulta_contextual = self._resolver_continuacao_pesquisa(mensagem)
        if consulta_contextual is not None:
            # Uma continuação de pesquisa mantém a intenção externa mesmo
            # quando a frase atual, isoladamente, parece conversacional.
            rota_previa = ROTA_PESQUISA_EXTERNA

        # A decisão de rota passa pelo núcleo de orquestração, que aplica
        # prioridades únicas e impede que capacidades concorrentes assumam
        # controle da mesma mensagem.
        rota_previa = orchestration.resolver_rota(
            rota_previa,
            decisao
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

        # Continuação de uma pesquisa anterior é uma decisão de contexto:
        # a mensagem curta pode não conter, sozinha, nenhum gatilho factual.
        if consulta_contextual is not None:
            rota = ROTA_PESQUISA_EXTERNA

        # Atualiza a decisão com o resultado do CORE.
        self.ultima_decisao = cortex.analisar(
            mensagem,
            intencao=intencao,
            comando=comando,
            conhecimento=resposta_conhecimento is not None,
            decisao_ia=decisao_ia
        )

        if rota == ROTA_CONHECIMENTO:
            return {
                "tipo": "conhecimento_verificado",
                "resposta": resposta_conhecimento,
                "origem": "core",
                "rota": rota,
                "consulta": mensagem
            }

        if rota == ROTA_PESQUISA_EXTERNA:
            # O histórico já carrega a consulta anterior; a ferramenta deve
            # receber a mensagem atual intacta para preservar a continuidade
            # sem reescrever a fala do usuário.
            return self._pesquisar_web(mensagem)

        # Rotas internas continuam pelo CORE abaixo, onde memória, tarefas,
        # entidades e ações são executadas sem passar por modelos.

        entidade_contextual_conversa = None
        entidade_conversa_id = self.conversa.obter_ultima_entidade()

        if entidade_conversa_id:
            entidade_contextual_conversa = entity_store.obter_por_id(
                self.entidades,
                entidade_conversa_id
            )

        entidade_detectada = entity_resolver.resolver(
            mensagem,
            self.entidades,
            entidade_contextual_conversa,
            usar_contexto_persistente=(
                entidade_contextual_conversa is None
                and entity_resolver.detectar_referencia(mensagem) is None
            )
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
            self.entidades,
            contexto_atual=entidade_contextual_conversa
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

            autorizacao = autonomy.avaliar_execucao(
                intencao
            )
            if (
                intencao.get("origem") == autonomy.ORIGEM_IA
                and not autorizacao.get("executar")
            ):
                return {
                    "tipo": "confirmacao_autonomia",
                    "resposta": (
                        "Identifiquei uma ação pela IA local, senhor, "
                        "mas não vou executá-la automaticamente. "
                        "Se desejar a execução, repita o pedido de forma "
                        "explícita como comando da STACY."
                    ),
                    "intencao": intencao,
                    "autonomia": autorizacao,
                    "rota": ROTA_INTERNA
                }

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

    def _resolver_continuacao_tarefa(self, mensagem):
        """Converte uma continuação de data/hora em atualização da última tarefa."""
        tarefa = self.conversa.obter_ultima_tarefa()
        if not isinstance(tarefa, dict):
            return None

        texto = mensagem.strip()
        normalizado = _normalizar_rota(texto)
        if normalizado.startswith("e "):
            normalizado = normalizado[2:].strip()
            texto = texto.strip()[2:].strip()

        restante, data, hora = intent.extrair_data_hora_tarefa(texto)

        # A mensagem precisa representar uma alteração, não uma nova tarefa.
        restante_normalizado = _normalizar_rota(restante)
        restante_normalizado = restante_normalizado.replace("  ", " ").strip()
        if not data and not hora:
            return None

        if restante_normalizado not in {
            "", "coloque", "colocar", "mude", "mudar",
            "altere", "alterar", "passe", "passar",
            "coloque para", "mude para", "mudar para",
            "altere para", "alterar para", "passe para", "passar para",
            "a tarefa", "a tarefa para"
        }:
            return None

        return {
            "tipo": "tarefa",
            "acao": "atualizar",
            "tarefa_id": tarefa.get("id"),
            "data": data,
            "hora": hora
        }

    def _deve_preservar_entidade_conversacional(self, mensagem):
        """Indica se a mensagem ainda pode depender do referente atual."""
        entidade_id = self.conversa.obter_ultima_entidade()
        if not entidade_id:
            return False

        texto = _normalizar_rota(mensagem)

        if entity_resolver.detectar_referencia(mensagem) is not None:
            return True

        entidade = entity_store.obter_por_id(
            self.entidades,
            entidade_id
        )
        if isinstance(entidade, dict):
            nome = _normalizar_rota(entidade.get("nome", ""))
            if nome and _contem_termo(texto, nome):
                return True

        if (
            texto.startswith("e ")
            or texto.startswith("mas ")
            or texto.startswith("nesse ")
            or texto.startswith("neste ")
            or texto.startswith("nesta ")
            or texto.startswith("sobre ")
            or texto.startswith("no caso ")
            or texto.startswith("na ")
            or texto.startswith("no ")
        ):
            return True

        # O contexto semântico genérico não decide a continuidade.
        # Consultas factuais sobre outro assunto podem parecer relacionadas
        # ao referente atual e isso manteria uma entidade obsoleta viva.
        # Referência explícita, nome da entidade e marcadores de continuidade
        # já cobrem as formas válidas de continuidade.
        return False

    def _resolver_continuacao_pesquisa(self, mensagem):
        """Liga perguntas curtas ao assunto da última pesquisa sem adivinhar fatos."""
        anterior = self.conversa.ultima_consulta
        if not anterior or self.conversa.ultima_rota not in {
            ROTA_PESQUISA_EXTERNA,
            ROTA_CONHECIMENTO
        }:
            return None

        texto = _normalizar_rota(mensagem)

        # Uma referência pronominal sem entidade conversacional ativa não
        # deve ressuscitar uma pesquisa de outro assunto. Nesse caso, deixe
        # a mensagem seguir para a IA local, que poderá pedir esclarecimento.
        # Pronomes sem referente ativo nunca podem herdar a última
        # pesquisa externa. Isso inclui construções como "qual o nome dela?".
        pronomes_sem_referente = (
            " ele", " ela", " dele", " dela", " eles", " elas",
            " deles", " delas", " esse", " essa", " isso", " aquele",
            " aquela", " aquilo"
        )
        mensagem_normalizada = f" {_normalizar_rota(mensagem)} "
        tem_referencia = (
            entity_resolver.detectar_referencia(mensagem) is not None
            or any(
                _contem_termo(mensagem_normalizada.strip(), pronome.strip())
                for pronome in pronomes_sem_referente
            )
        )
        if tem_referencia and not self.conversa.obter_ultima_entidade():
            return None

        if not texto or len(texto.split()) > 14:
            return None

        inicio_continuacao = (
            texto.startswith("e ")
            or texto.startswith("mas ")
            or texto.startswith("nesse ")
            or texto.startswith("neste ")
            or texto.startswith("nesta ")
            or texto.startswith("sobre ")
            or texto.startswith("no caso ")
            or texto.startswith("na ")
            or texto.startswith("no ")
        )
        referencia = any(
            _contem_termo(texto, termo)
            for termo in ("isso", "ele", "ela", "dele", "dela", "sua", "seu")
        )

        if not (inicio_continuacao or referencia):
            return None

        assunto = anterior.split(" | complemento:", 1)[0].strip()
        return f"{assunto} | complemento: {mensagem.strip()}"

    def _resolver_consulta_conversa(self, mensagem):
        """Resolve perguntas sobre o histórico sem usar IA ou Web."""
        texto = _normalizar_rota(mensagem)
        ultimo = (
            "qual foi a ultima coisa que eu perguntei",
            "qual foi a ultima pergunta que eu fiz",
            "qual foi minha ultima pergunta",
            "qual foi a minha ultima pergunta",
            "o que eu perguntei por ultimo",
            "o que eu perguntei antes"
        )
        primeiro = (
            "qual foi a primeira coisa que eu perguntei",
            "qual foi a primeira pergunta que eu fiz",
            "qual foi minha primeira pergunta",
            "qual foi a minha primeira pergunta",
            "qual foi a primeira pergunta nesta conversa",
            "qual foi a primeira pergunta nessa conversa"
        )
        modo = None
        if any(_contem_termo(texto, frase) for frase in ultimo):
            modo = "ultima"
        elif any(_contem_termo(texto, frase) for frase in primeiro):
            modo = "primeira"
        if modo is None:
            return None
        historico = self.conversa.obter_historico()
        usuarios = [
            item.get("conteudo", "").strip()
            for item in historico[:-1]
            if item.get("tipo") == "usuario"
            and item.get("conteudo", "").strip()
        ]
        if not usuarios:
            return {
                "tipo": "local",
                "resposta": "Ainda não tenho outra pergunta registrada nesta conversa.",
                "rota": ROTA_INTERNA
            }
        pergunta = usuarios[-1] if modo == "ultima" else usuarios[0]
        rotulo = "última" if modo == "ultima" else "primeira"
        return {
            "tipo": "local",
            "resposta": f"A {rotulo} pergunta registrada foi: {pergunta}",
            "rota": ROTA_INTERNA
        }

    def _registrar_resultado_conversa(self, resultado):
        if not isinstance(resultado, dict):
            return resultado

        resposta = resultado.get("resposta")

        if resposta is not None:
            self.conversa.registrar_resposta(resposta)

        rota = resultado.get("rota")
        if rota is None:
            tipo = resultado.get("tipo")
            if tipo in {"pesquisa", "pesquisa_fallback", "pesquisa_indisponivel"}:
                rota = ROTA_PESQUISA_EXTERNA
            elif tipo in {
                "local", "tarefa_ultima", "tarefa_criada", "tarefa_atualizada",
                "tarefas", "tarefa_concluida", "tarefa_nao_encontrada",
                "tarefa_ambigua", "confirmacao", "tarefa_removida",
                "erro_tarefa", "acao_executada", "acao_candidata",
                "acao_ja_existente", "acao_cancelada", "erro_acao"
            }:
                rota = ROTA_INTERNA
            elif tipo == "conhecimento_verificado":
                rota = ROTA_CONHECIMENTO
            else:
                rota = ROTA_IA_LOCAL

        consulta = resultado.get("consulta")
        if consulta is not None:
            self.conversa.registrar_rota(rota, consulta)
        else:
            self.conversa.registrar_rota(rota)

        tarefa = resultado.get("tarefa")
        if isinstance(tarefa, dict):
            self.conversa.registrar_tarefa(tarefa)

        if resultado.get("entidade") is not None:
            entidade = resultado.get("entidade")
            entidade_id = entidade.get("id")

            if entidade_id is not None:
                self.conversa.registrar_entidade(
                    entidade_id
                )
        elif rota in {
            ROTA_PESQUISA_EXTERNA,
            ROTA_CONHECIMENTO
        }:
            # Uma nova pergunta factual sem entidade explícita encerra o
            # referente conversacional anterior. Isso impede que um pronome
            # posterior reutilize uma entidade de outro assunto.
            self.conversa.limpar_entidade()

        acao = resultado.get("acao")
        if acao is not None:
            if resultado.get("tipo") == "acao_candidata":
                self.conversa.registrar_acao_pendente(acao)
            else:
                self.conversa.registrar_acao(acao)

        if resultado.get("intencao") is not None:
            self.conversa.registrar_intencao(
                resultado.get("intencao")
            )

        if resultado.get("tipo") in {
            "erro_acao",
            "erro_tarefa",
            "pesquisa_indisponivel"
        }:
            self.conversa.registrar_erro(
                resultado.get("erro") or resultado.get("tipo")
            )

        return resultado

    def _atualizar_contexto(
        self,
        entidade
    ):

        # Contexto conversacional é temporário. Não gravamos automaticamente
        # a entidade atual em entities.json, porque isso transformaria um
        # referente de uma conversa em memória persistente.
        if not isinstance(entidade, dict):
            return

        identificador = entidade.get("id")
        if not identificador:
            return

        self.entidade_contextual = {
            "id": entidade.get("id"),
            "uuid": entidade.get("uuid"),
            "categoria": entidade.get("categoria"),
            "nome": entidade.get("nome")
        }

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

            if categoria == "usuario" and intencao.get("chave"):
                valor_memoria = f"{intencao['chave']}={valor}"
            else:
                valor_memoria = valor

            sucesso = memory.registrar_memoria(
                categoria,
                valor_memoria,
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

        if acao == "ultima":
            tarefa = self.conversa.obter_ultima_tarefa()
            if isinstance(tarefa, dict) and tarefa.get("titulo"):
                resposta = f"A última tarefa criada é '{tarefa['titulo']}'."
                if tarefa.get("data"):
                    resposta += f" Data: {tarefa['data']}."
                if tarefa.get("hora"):
                    resposta += f" Horário: {tarefa['hora']}."
                return {
                    "tipo": "tarefa_ultima",
                    "resposta": resposta,
                    "tarefa": tarefa,
                    "rota": ROTA_INTERNA
                }
            return {
                "tipo": "tarefa_nao_encontrada",
                "resposta": "Não encontrei nenhuma tarefa criada recentemente, senhor.",
                "rota": ROTA_INTERNA
            }

        if acao == "referencia":
            tarefa = self.conversa.obter_ultima_tarefa()
            if isinstance(tarefa, dict) and tarefa.get("titulo"):
                return {
                    "tipo": "clarificacao",
                    "resposta": (
                        f"Senhor, a última tarefa registrada é "
                        f"'{tarefa['titulo']}'. Deseja recriá-la?"
                    ),
                    "tarefa": tarefa,
                    "rota": ROTA_INTERNA
                }
            return {
                "tipo": "clarificacao",
                "resposta": (
                    "Qual tarefa o senhor deseja criar? "
                    "Não vou adivinhar o que significa 'essa tarefa'."
                ),
                "rota": ROTA_INTERNA
            }

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

        if acao == "atualizar":
            tarefa_id = intencao.get("tarefa_id")
            data = intencao.get("data")
            hora = intencao.get("hora")

            if not tarefa_id or (data is None and hora is None):
                return None

            tarefa = tasks.atualizar(
                tarefa_id,
                data=data,
                hora=hora
            )

            if tarefa is None:
                return {
                    "tipo": "erro_tarefa",
                    "resposta": "Não consegui atualizar a tarefa, senhor."
                }

            return {
                "tipo": "tarefa_atualizada",
                "resposta": f"Atualizada, senhor: '{tarefa['titulo']}'.",
                "tarefa": tarefa
            }

        if acao == "corrigir_titulo":
            tarefa = self.conversa.obter_ultima_tarefa()
            if not isinstance(tarefa, dict) or not tarefa.get("id"):
                return {
                    "tipo": "tarefa_nao_encontrada",
                    "resposta": "Não encontrei uma tarefa criada recentemente, senhor."
                }

            antigo = intencao.get("antigo")
            novo = (intencao.get("novo") or "").strip()
            titulo_atual = tarefa.get("titulo", "")

            if not novo:
                return None

            if antigo:
                titulo_novo = re.sub(
                    r"(?<!\w)" + re.escape(antigo) + r"(?!\w)",
                    novo,
                    titulo_atual,
                    count=1,
                    flags=re.IGNORECASE
                )
            else:
                titulo_novo = novo

            if titulo_novo == titulo_atual:
                return {
                    "tipo": "tarefa_atualizada",
                    "resposta": f"O título já está como '{titulo_atual}', senhor.",
                    "tarefa": tarefa
                }

            atualizado = tasks.atualizar(
                tarefa["id"],
                titulo=titulo_novo
            )

            if atualizado is None:
                return {
                    "tipo": "erro_tarefa",
                    "resposta": "Não consegui atualizar o nome da tarefa, senhor."
                }

            return {
                "tipo": "tarefa_atualizada",
                "resposta": f"Nome da tarefa atualizado, senhor: '{atualizado['titulo']}'.",
                "tarefa": atualizado
            }

        if acao in ["concluir", "remover"]:

            termo = intencao.get("termo")

            if acao == "remover" and intencao.get("referencia") == "ultima":
                tarefa = self.conversa.obter_ultima_tarefa()
                if not isinstance(tarefa, dict) or not tarefa.get("id"):
                    return {
                        "tipo": "tarefa_nao_encontrada",
                        "resposta": "Não encontrei uma tarefa criada recentemente, senhor."
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
                        f"'{tarefa['titulo']}'? Esta ação não poderá ser desfeita."
                    ),
                    "tarefa": tarefa,
                    "rota": ROTA_INTERNA
                }

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

        # A pesquisa externa recebe a consulta atual e, quando necessário,
        # uma mensagem anterior do usuário para resolver referências como
        # "sua classificação", "ele" ou "isso". Memória persistente não é
        # enviada ao provedor.
        historico_conversa = self.conversa.ultimas_mensagens(4)
        historico_pesquisa = []

        for item in historico_conversa:
            if not isinstance(item, dict):
                continue

            conteudo = item.get("conteudo", "").strip()
            tipo = item.get("tipo")

            if not conteudo or tipo not in {"usuario", "stacy"}:
                continue

            role = "model" if tipo == "stacy" else "user"
            historico_pesquisa.append({
                "role": role,
                "parts": [{"text": conteudo}]
            })

        # A mensagem atual já está registrada no ConversationState e deve
        # permanecer explicitamente como a última consulta.
        if (
            not historico_pesquisa
            or historico_pesquisa[-1].get("role") != "user"
            or historico_pesquisa[-1]["parts"][0].get("text") != mensagem
        ):
            historico_pesquisa.append({
                "role": "user",
                "parts": [{"text": mensagem}]
            })

        try:
            resultado = ai.gerar_resposta_pesquisa(
                self.api_key,
                historico_pesquisa
            )
        except Exception as erro_pesquisa:
            # Pesquisa externa exige verificação externa. Não substitua uma
            # pesquisa malsucedida por uma resposta comum do Gemini, pois isso
            # confundiria conhecimento não verificado com informação pesquisada.
            return {
                "tipo": "pesquisa_indisponivel",
                "rota": ROTA_PESQUISA_EXTERNA,
                "consulta": mensagem,
                "resposta": (
                    "Não consegui consultar fontes externas agora, senhor. "
                    "A pesquisa não foi verificada; não vou apresentar "
                    "uma resposta factual como se tivesse sido confirmada."
                ),
                "origem": "gemini_google",
                "fontes": [],
                "erro": str(erro_pesquisa)
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
            "rota": ROTA_PESQUISA_EXTERNA,
            "consulta": mensagem,
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

        # Não envie consultas externas anteriores para o modelo local.
        # Modelos pequenos podem copiar o assunto anterior e responder a ele
        # em vez da mensagem atual. A pesquisa externa já mantém seu próprio
        # contexto no caminho _pesquisar_web.
        contexto_local = []
        for item in self.conversa.ultimas_mensagens(6):
            if not isinstance(item, dict):
                continue

            conteudo = item.get("conteudo", "").strip()
            tipo = item.get("tipo")
            rota_item = item.get("rota")

            if not conteudo:
                continue

            # Turnos de pesquisa externa pertencem exclusivamente ao
            # subsistema Web/Gemini. Nunca os reutilize como memória de prompt
            # da IA local, inclusive as respostas da STACY a esses turnos.
            if rota_item == ROTA_PESQUISA_EXTERNA:
                continue

            contexto_local.append(item)

        contexto_conversa = json.dumps(
            contexto_local[-6:],
            ensure_ascii=False,
            indent=2
        )

        # Converta apenas os turnos não externos para o histórico da IA local.
        # O Gemini continua recebendo o histórico completo da sessão.
        historico_local = []
        for item in contexto_local:
            tipo = item.get("tipo")
            conteudo = item.get("conteudo", "").strip()
            if not conteudo or tipo not in {"usuario", "stacy"}:
                continue
            historico_local.append({
                "role": "user" if tipo == "usuario" else "model",
                "parts": [{"text": conteudo}]
            })

        # Garanta que a consulta atual seja o último turno do histórico local.
        if not historico_local or historico_local[-1]["parts"][0]["text"] != mensagem:
            historico_local.append({
                "role": "user",
                "parts": [{"text": mensagem}]
            })

        try:
            resultado_hibrido = ai.gerar_resposta_hibrida(
                self.api_key,
                historico_local,
                contexto_memoria,
                contexto_entidade,
                contexto_conversa,
                historico_gemini=self.historico
            )
            resposta = resultado_hibrido["resposta"]
            origem = resultado_hibrido["origem"]

            if resultado_hibrido.get("fallback"):
                print(
                    "[STACY] IA local indisponível; "
                    "Gemini assumiu como fallback."
                )

        except Exception as erro_hibrido:
            raise RuntimeError(
                "Não consegui obter uma resposta da IA agora, senhor. "
                "A IA local e o Gemini não responderam corretamente."
            ) from erro_hibrido

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