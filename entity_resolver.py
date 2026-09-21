import entity_store


REFERENCIAS = {
    "ele",
    "ela",
    "dele",
    "dela",
    "esse projeto",
    "essa entidade",
    "o projeto",
    "a entidade",
    "desse projeto",
    "dessa entidade"
}


def normalizar(texto):
    if not isinstance(texto, str):
        return ""

    texto = texto.strip().lower()

    for caractere in "?!.,;:":
        texto = texto.replace(caractere, "")

    return " ".join(texto.split())


def detectar_referencia(texto):
    normalizado = normalizar(texto)

    referencias = sorted(
        REFERENCIAS,
        key=len,
        reverse=True
    )

    for referencia in referencias:

        if referencia in normalizado:

            return referencia

    return None


def buscar_por_nome(
    texto,
    dados
):
    normalizado = normalizar(texto)

    if not normalizado:
        return None

    entidades = entity_store.listar_entidades(
        dados
    )

    candidatos = []

    for entidade in entidades:

        if not isinstance(entidade, dict):
            continue

        nome = entidade.get(
            "nome",
            ""
        )

        if not isinstance(nome, str):
            continue

        nome_normalizado = normalizar(nome)

        if not nome_normalizado:
            continue

        if nome_normalizado in normalizado:

            candidatos.append(
                entidade
            )

    if len(candidatos) == 1:

        return {
            "status": "encontrada",
            "entidade": candidatos[0]
        }

    if len(candidatos) > 1:

        return {
            "status": "ambigua",
            "entidades": candidatos
        }

    return None


def resolver_referencia(
    texto,
    dados,
    contexto_atual=None,
    usar_contexto_persistente=True
):
    referencia = detectar_referencia(
        texto
    )

    if referencia is None:

        return None

    if contexto_atual is None and usar_contexto_persistente:

        contexto_atual = (
            entity_store.obter_contexto_persistente(
                dados
            )
        )

    if contexto_atual is None:

        return None

    identificador = contexto_atual.get(
        "id"
    )

    if not identificador:

        return None

    entidade = entity_store.obter_por_id(
        dados,
        identificador
    )

    if entidade is None:

        return None

    return {
        "status": "encontrada",
        "referencia": referencia,
        "entidade": entidade
    }


def resolver(
    texto,
    dados,
    contexto_atual=None,
    usar_contexto_persistente=True
):
    por_nome = buscar_por_nome(
        texto,
        dados
    )

    if por_nome is not None:

        return {
            "tipo": "nome",
            **por_nome
        }

    por_referencia = resolver_referencia(
        texto,
        dados,
        contexto_atual,
        usar_contexto_persistente=usar_contexto_persistente
    )

    if por_referencia is not None:

        return {
            "tipo": "referencia",
            **por_referencia
        }

    return None

