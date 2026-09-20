import re


CONHECIMENTO_VERIFICADO = [
    (
        re.compile(r"quantas luas tem venus|quantas luas tem vênus", re.I),
        "Vênus não possui luas naturais conhecidas."
    ),
    (
        re.compile(r"qual a capital do brasil", re.I),
        "A capital do Brasil é Brasília."
    ),
    (
        re.compile(r"quantos dentes tem um ser humano adulto|quantos dentes tem um adulto", re.I),
        "Um adulto normalmente tem 32 dentes permanentes, incluindo os quatro sisos."
    ),
    (
        re.compile(r"qual a cor de um carro vermelho", re.I),
        "Um carro vermelho é, por definição, vermelho."
    ),
]


def consultar(mensagem):
    texto = (mensagem or "").strip()
    if not texto:
        return None

    for padrao, resposta in CONHECIMENTO_VERIFICADO:
        if padrao.search(texto):
            return resposta

    return None
