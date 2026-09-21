"""Validation of model outputs before STACY exposes them to the user."""


class InvalidModelResponse(RuntimeError):
    """Raised when a model produced an unusable response."""


def validar_resposta(texto, consulta=None, limite=12000):
    """Return a clean response or fail closed.

    This is intentionally conservative: an empty, absurdly large, or exact
    echo of the user's query is not a useful assistant response.
    """
    if not isinstance(texto, str):
        raise InvalidModelResponse("modelo retornou conteúdo não textual")

    resposta = texto.strip()
    if not resposta:
        raise InvalidModelResponse("modelo retornou resposta vazia")

    if len(resposta) > limite:
        raise InvalidModelResponse("modelo retornou resposta excessivamente longa")

    if isinstance(consulta, str):
        pergunta = " ".join(consulta.strip().split()).casefold()
        resposta_normalizada = " ".join(resposta.split()).casefold()
        if pergunta and resposta_normalizada == pergunta:
            raise InvalidModelResponse("modelo apenas repetiu a consulta")

    return resposta


def validar_fontes(fontes):
    """Keep only structurally valid HTTP(S) sources."""
    if not isinstance(fontes, list):
        return []

    resultado = []
    vistos = set()
    for fonte in fontes:
        if not isinstance(fonte, dict):
            continue
        titulo = str(fonte.get("titulo") or "Fonte").strip()
        url = fonte.get("url")
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not (url.startswith("https://") or url.startswith("http://")):
            continue
        if url in vistos:
            continue
        vistos.add(url)
        resultado.append({"titulo": titulo, "url": url})

    return resultado
