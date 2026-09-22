"""Núcleo determinístico de orquestração da STACY.

Responsabilidade: resolver a rota final a partir das decisões já produzidas
pelo Core. Não executa ações, não chama IA/Web e não concede autonomia.
"""

ROTA_INTERNA = "interno"
ROTA_PESQUISA_EXTERNA = "pesquisa_externa"


def resolver_rota(rota_previa, decisao):
    """Aplica uma única política de prioridade à decisão de roteamento.

    A rota interna permanece soberana quando o Core identificou memória ou
    ação. A necessidade explícita de Web só vence uma rota que ainda não seja
    interna. Rotas de conversa/conhecimento permanecem como foram definidas.
    """
    if rota_previa == ROTA_INTERNA:
        return ROTA_INTERNA

    if not isinstance(decisao, dict):
        return rota_previa

    if decisao.get("needs_memory") or decisao.get("needs_action"):
        return ROTA_INTERNA

    if decisao.get("needs_web"):
        return ROTA_PESQUISA_EXTERNA

    return rota_previa


def validar_decisao(decisao):
    """Valida a forma mínima de uma decisão de orquestração."""
    if not isinstance(decisao, dict):
        return False

    campos = ("needs_memory", "needs_action", "needs_web")
    if not all(campo in decisao for campo in campos):
        return False

    return all(isinstance(decisao[campo], bool) for campo in campos)
