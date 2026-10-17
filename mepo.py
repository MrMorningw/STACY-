"""Modelo determinístico dos MEPOs da STACY.

MEPO = Metas Essenciais Para Objetivos. Este módulo mantém apenas o estado
do ciclo de MPs; não executa ações, não usa IA e não concede autonomia.
"""

ESTADOS = {"planejado", "em_execucao", "validado", "fechado"}
ORDEM = tuple(range(1, 13))

_STATUS_INICIAL = {
    1: "fechado", 2: "fechado", 3: "fechado", 4: "fechado",
    5: "fechado", 6: "fechado", 7: "fechado", 8: "fechado",
    9: "fechado", 10: "fechado", 11: "fechado", 12: "fechado",
}

_NOMES = {
    1: "STACY funcional", 2: "inteligência e contexto", 3: "memória avançada",
    4: "ações e ferramentas", 5: "contexto operacional", 6: "voz",
    7: "interface Android", 8: "automação e Android", 9: "trajetória e metas",
    10: "orquestração", 11: "autonomia controlada", 12: "estabilização e finalização",
}


def normalizar_id(identificador):
    if isinstance(identificador, int):
        return f"MP-{identificador:02d}"
    texto = str(identificador or "").strip().upper().replace("_", "-")
    if texto.isdigit():
        texto = f"MP-{int(texto):02d}"
    return texto


def numero(identificador):
    texto = normalizar_id(identificador)
    if not texto.startswith("MP-"):
        return None
    try:
        valor = int(texto[3:])
    except ValueError:
        return None
    return valor if valor in ORDEM else None


def criar_registro(identificador):
    n = numero(identificador)
    if n is None:
        return None
    return {"id": f"MP-{n:02d}", "numero": n, "nome": _NOMES[n], "status": _STATUS_INICIAL[n]}


def listar():
    return [criar_registro(n) for n in ORDEM]


def obter(identificador):
    return criar_registro(identificador)


def validar_transicao(atual, novo):
    atual = str(atual or "").strip().lower()
    novo = str(novo or "").strip().lower()
    if atual not in ESTADOS or novo not in ESTADOS:
        return False
    permitidas = {"planejado": {"em_execucao"}, "em_execucao": {"validado"}, "validado": {"fechado"}, "fechado": set()}
    return novo in permitidas[atual]


def validar_sequencia(registros=None):
    dados = listar() if registros is None else registros
    ids = [item.get("id") for item in dados if isinstance(item, dict)]
    return ids == [f"MP-{n:02d}" for n in ORDEM]


def proximo_aberto():
    for registro in listar():
        if registro["status"] != "fechado":
            return registro
    return None


def resumo():
    registros = listar()
    return {"total": len(registros), "fechados": sum(item["status"] == "fechado" for item in registros), "atual": proximo_aberto(), "sequencia_valida": validar_sequencia(registros)}
