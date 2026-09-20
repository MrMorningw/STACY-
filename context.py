import entity_resolver


def obter_entidade_contextual(
    entity_store,
    entidades
):
    contexto = entity_store.obter_contexto_persistente(
        entidades
    )

    if contexto is None:
        return None

    identificador = contexto.get("id")

    if not identificador:
        return None

    return entity_store.obter_por_id(
        entidades,
        identificador
    )


def detectar_consulta_entidade(mensagem):

    texto = mensagem.strip().lower()

    for caractere in "?!.,;:":
        texto = texto.replace(caractere, "")

    texto = " ".join(texto.split())

    consultas = [
        (
            [
                "qual é o objetivo principal",
                "qual e o objetivo principal",
                "qual é o objetivo",
                "qual e o objetivo",
                "qual o objetivo principal",
                "qual o objetivo"
            ],
            "objetivo_principal"
        ),
        (
            [
                "quais são os objetivos",
                "quais sao os objetivos",
                "quais os objetivos",
                "e os objetivos",
                "os objetivos"
            ],
            "objetivos"
        ),
        (
            [
                "qual é o nome",
                "qual e o nome",
                "qual o nome",
                "e o nome"
            ],
            "nome"
        ),
        (
            [
                "o que você sabe sobre",
                "o que voce sabe sobre",
                "o que sabe sobre"
            ],
            None
        )
    ]

    for frases, atributo in consultas:

        for frase in frases:

            if frase in texto:

                return {
                    "tipo": "consulta_entidade",
                    "atributo": atributo
                }

    return None


def interpretar_contexto(
    mensagem,
    entity_store,
    entidades
):

    consulta = detectar_consulta_entidade(
        mensagem
    )

    if consulta is None:
        return None

    resolvida = entity_resolver.resolver(
        mensagem,
        entidades,
        obter_entidade_contextual(
            entity_store,
            entidades
        )
    )

    if resolvida is not None:

        if resolvida.get("status") != "encontrada":
            return None

        entidade = resolvida.get("entidade")

        if entidade is None:
            return None

        referencia = resolvida.get(
            "referencia",
            entidade.get("nome")
        )

    else:

        entidade = obter_entidade_contextual(
            entity_store,
            entidades
        )

        if entidade is None:
            return None

        referencia = "contexto_atual"

    return {
        "tipo": consulta["tipo"],
        "referencia": referencia,
        "entidade_id": entidade["id"],
        "entidade": entidade,
        "atributo": consulta["atributo"]
    }


def resolver_consulta(interpretação):

    if not isinstance(interpretação, dict):
        return None

    if interpretação.get("tipo") != "consulta_entidade":
        return None

    entidade = interpretação.get("entidade")

    if not isinstance(entidade, dict):
        return None

    atributo = interpretação.get("atributo")

    nome = entidade.get("nome")

    if atributo == "nome":

        return {
            "status": "encontrada",
            "entidade_id": entidade.get("id"),
            "atributo": "nome",
            "valor": nome
        }

    atributos = entidade.get(
        "atributos",
        {}
    )

    if not isinstance(atributos, dict):
        atributos = {}

    if atributo is not None:

        if atributo not in atributos:

            return {
                "status": "nao_encontrado",
                "entidade_id": entidade.get("id"),
                "atributo": atributo,
                "valor": None
            }

        return {
            "status": "encontrada",
            "entidade_id": entidade.get("id"),
            "atributo": atributo,
            "valor": atributos[atributo]
        }

    return {
        "status": "entidade_completa",
        "entidade_id": entidade.get("id"),
        "nome": nome,
        "categoria": entidade.get("categoria"),
        "atributos": atributos
    }
