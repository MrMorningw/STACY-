import re
import unicodedata


def _normalizar(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(texto.split())


def _tem_pistas_abacate(texto):
    return (
        "fruta" in texto
        and "verde" in texto
        and "comeca com a" in texto
        and "caroco" in texto
    )


CONHECIMENTO_VERIFICADO = [
    (
        re.compile(r"quantas luas tem venus|quantas luas.*venus", re.I),
        "Vênus não possui luas naturais conhecidas."
    ),
    (
        re.compile(r"qual a capital do brasil|qual e a capital do brasil", re.I),
        "A capital do Brasil é Brasília."
    ),
    (
        re.compile(
            r"quantos dentes tem um ser humano adulto|"
            r"quantos dentes tem um adulto",
            re.I
        ),
        "Um adulto normalmente tem 32 dentes permanentes, incluindo os quatro sisos."
    ),
    (
        re.compile(
            r"qual a cor de um carro vermelho|qual e a cor de um carro vermelho",
            re.I
        ),
        "Um carro vermelho é, por definição, vermelho."
    ),
]


def consultar(mensagem):
    texto = _normalizar(mensagem)

    if not texto:
        return None

    for padrao, resposta in CONHECIMENTO_VERIFICADO:
        if padrao.search(texto):
            return resposta

    if "qual a cor" in texto and "sol" in texto:
        return (
            "Visto do espaço, o Sol parece branco. "
            "Da superfície da Terra, a atmosfera pode fazê-lo parecer amarelado, "
            "alaranjado ou avermelhado, especialmente perto do horizonte."
        )

    if _tem_pistas_abacate(texto):
        return "A fruta que corresponde a essas pistas é o abacate."

    if "fruta" in texto and "verde" in texto and "caroco" in texto:
        return (
            "Uma fruta verde com caroço pode ser o abacate, "
            "entre outras possibilidades."
        )

    return None


def consultar_contextual(mensagem, historico):
    """Resolve pistas factuais simples usando mensagens recentes do usuário."""
    atual = _normalizar(mensagem)

    if not atual:
        return None

    anteriores = []

    for item in reversed(historico or []):
        if not isinstance(item, dict):
            continue

        if item.get("tipo") != "usuario":
            continue

        conteudo = item.get("conteudo", "")

        if conteudo:
            anteriores.append(_normalizar(conteudo))

        if len(anteriores) >= 4:
            break

    if (
        "caroco" in atual
        and any(
            "fruta" in item
            and "verde" in item
            and "comeca com a" in item
            for item in anteriores
        )
    ):
        return "A fruta que corresponde a essas pistas é o abacate."

    if "fruta" in atual and "verde" in atual and "caroco" in atual:
        return (
            "Uma fruta verde com caroço pode ser o abacate, "
            "entre outras possibilidades."
        )

    return None
