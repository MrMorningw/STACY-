"""Núcleo determinístico de coerência CTAC.

CTAC = Coerência para Trajetória Aperfeiçoada Constante.
Responsabilidade: verificar a coerência estrutural entre a trajetória e os
MEPOs. Não decide metas, não executa ações e não produz autonomia.
"""

import mepo


NOME = "CTAC"
DESCRICAO = "Coerência para Trajetória Aperfeiçoada Constante"


def estado():
    resumo = mepo.resumo()
    atual = resumo["atual"]
    return {
        "nome": NOME,
        "descricao": DESCRICAO,
        "mepo_atual": atual["id"] if atual else None,
        "status_mepo_atual": atual["status"] if atual else None,
        "mepos_fechados": resumo["fechados"],
        "mepos_total": resumo["total"],
    }


def validar_coerencia():
    registros = mepo.listar()
    erros = []

    if not mepo.validar_sequencia(registros):
        erros.append("sequencia_mepo_invalida")

    ativos = [
        item for item in registros
        if item["status"] == "em_execucao"
    ]

    if len(ativos) > 1:
        erros.append("mais_de_um_mepo_em_execucao")

    if ativos:
        numero_atual = ativos[0]["numero"]
        anteriores = registros[:numero_atual - 1]
        if any(item["status"] != "fechado" for item in anteriores):
            erros.append("mepo_anterior_nao_fechado")

    for item in registros:
        if item["status"] == "planejado" and item["numero"] < 9:
            erros.append(f"mepo_historico_inconsistente:{item['id']}")

    return {
        "coerente": not erros,
        "erros": erros,
        "estado": estado(),
    }


def formatar_estado():
    atual = estado()
    validacao = validar_coerencia()
    if atual["mepo_atual"] is None:
        return "CTAC sem MEPO ativo, senhor."
    status = atual["status_mepo_atual"].replace("_", " ")
    situacao = "coerente" if validacao["coerente"] else "com inconsistências"
    return (
        f"CTAC: trajetória {situacao}. "
        f"MEPO atual: {atual['mepo_atual']} — {status}. "
        f"{atual['mepos_fechados']}/{atual['mepos_total']} MEPOs fechados."
    )


def formatar_mepos():
    linhas = ["MEPOs da trajetória, senhor:"]
    for item in mepo.listar():
        status = item["status"].replace("_", " ")
        linhas.append(f"• {item['id']} — {item['nome']} — {status}")
    return "\n".join(linhas)
