"""Cortex determinístico de entendimento da STACY.

Responsabilidade: transformar a mensagem em uma decisão estruturada antes
da execução. O Cortex não gera respostas e não é uma autoridade factual.
"""

import re
import unicodedata


MODO_CONVERSA = "chat"
MODO_RESPOSTA = "answer"
MODO_PESQUISA = "research"
MODO_ACAO = "action"
MODO_MEMORIA = "memory"
MODO_CLARIFICAR = "clarify"


def normalizar(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[!?.,;:]+", " ", texto)
    return " ".join(texto.split())


def _tem(texto, termo):
    return f" {termo} " in f" {texto} "


def analisar(mensagem, intencao=None, comando=None, conhecimento=False):
    """Produz uma decisão estruturada e conservadora."""
    texto = normalizar(mensagem)

    if not texto:
        return {
            "modo": MODO_CLARIFICAR,
            "objetivo": None,
            "ferramenta": None,
            "argumentos": {},
            "needs_web": False,
            "needs_memory": False,
            "needs_action": False,
            "confidence": 1.0,
            "motivo": "mensagem_vazia",
        }

    tipo = intencao.get("tipo") if isinstance(intencao, dict) else None
    acao = intencao.get("acao") if isinstance(intencao, dict) else None

    if comando in {"memoria", "buscar", "memorize", "esquecer"}:
        return {
            "modo": MODO_MEMORIA,
            "objetivo": acao or comando,
            "ferramenta": "memory",
            "argumentos": intencao or {},
            "needs_web": False,
            "needs_memory": True,
            "needs_action": False,
            "confidence": 1.0,
            "motivo": "comando_memoria",
        }

    if tipo == "memoria":
        return {
            "modo": MODO_MEMORIA,
            "objetivo": acao or "consultar",
            "ferramenta": "memory",
            "argumentos": intencao,
            "needs_web": False,
            "needs_memory": True,
            "needs_action": False,
            "confidence": 1.0,
            "motivo": "intencao_memoria",
        }

    if tipo == "tarefa":
        return {
            "modo": MODO_ACAO,
            "objetivo": acao or "tarefa",
            "ferramenta": "tasks",
            "argumentos": intencao,
            "needs_web": False,
            "needs_memory": False,
            "needs_action": True,
            "confidence": 1.0,
            "motivo": "intencao_tarefa",
        }

    pesquisa_explicita = (
        _tem(texto, "pesquise")
        or _tem(texto, "pesquisar")
        or _tem(texto, "procure")
        or _tem(texto, "busque")
        or _tem(texto, "na internet")
        or _tem(texto, "no google")
        or _tem(texto, "pesquisa na internet")
        or _tem(texto, "pesquisa no google")
        or _tem(texto, "me de fontes")
        or _tem(texto, "me dê fontes")
        or _tem(texto, "cite fontes")
        or _tem(texto, "fontes sobre")
    )

    if pesquisa_explicita:
        return {
            "modo": MODO_PESQUISA,
            "objetivo": "consultar_fontes_externas",
            "ferramenta": "web",
            "argumentos": {"consulta": mensagem.strip()},
            "needs_web": True,
            "needs_memory": False,
            "needs_action": False,
            "confidence": 1.0,
            "motivo": "pesquisa_explicita",
        }

    temporais = (
        "hoje", "agora", "atual", "atualmente",
        "ultimo", "ultima", "ultimos", "ultimas",
        "recentemente", "noticia", "noticias",
    )
    if any(_tem(texto, termo) for termo in temporais):
        return {
            "modo": MODO_PESQUISA,
            "objetivo": "informacao_atual",
            "ferramenta": "web",
            "argumentos": {"consulta": mensagem.strip()},
            "needs_web": True,
            "needs_memory": False,
            "needs_action": False,
            "confidence": 0.98,
            "motivo": "informacao_temporal",
        }

    factual_prefixos = (
        "qual ", "quem ", "quando ", "onde ",
        "quanto ", "quantos ", "quantas ",
        "o que e ", "o que sao ", "o que significa ",
        "como funciona ", "me diga ", "diga ",
    )
    if texto.startswith(factual_prefixos):
        return {
            "modo": MODO_PESQUISA,
            "objetivo": "verificar_fato",
            "ferramenta": "web",
            "argumentos": {"consulta": mensagem.strip()},
            "needs_web": True,
            "needs_memory": False,
            "needs_action": False,
            "confidence": 0.90,
            "motivo": "pergunta_potencialmente_factual",
        }

    if conhecimento:
        return {
            "modo": MODO_RESPOSTA,
            "objetivo": "responder_com_core",
            "ferramenta": "knowledge",
            "argumentos": {},
            "needs_web": False,
            "needs_memory": False,
            "needs_action": False,
            "confidence": 1.0,
            "motivo": "conhecimento_verificado",
        }

    # Mensagens sem intenção estruturada permanecem conversacionais.
    return {
        "modo": MODO_CONVERSA,
        "objetivo": "conversar",
        "ferramenta": "local_ai",
        "argumentos": {},
        "needs_web": False,
        "needs_memory": False,
        "needs_action": False,
        "confidence": 0.70,
        "motivo": "nenhuma_intencao_estruturada",
    }
