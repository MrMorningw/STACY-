import entity_store


def criar_atualizacao_atributo(
    entidade_id,
    campo,
    valor
):
    if not entidade_id:
        return None

    if not campo:
        return None

    if valor is None:
        return None

    return {
        "tipo": "atualizar_atributo",
        "entidade_id": entidade_id,
        "campo": campo,
        "valor": valor
    }


def executar(
    acao,
    entidades
):
    if not isinstance(acao, dict):
        return {
            "status": "invalida"
        }

    tipo = acao.get(
        "tipo"
    )

    if tipo == "atualizar_atributo":

        entidade_id = acao.get(
            "entidade_id"
        )

        campo = acao.get(
            "campo"
        )

        valor = acao.get(
            "valor"
        )

        if not entidade_id or not campo:
            return {
                "status": "invalida"
            }

        sucesso = entity_store.atualizar_por_id(
            entidades,
            entidade_id,
            campo,
            valor
        )

        if sucesso:

            return {
                "status": "executada",
                "tipo": tipo,
                "entidade_id": entidade_id,
                "campo": campo,
                "valor": valor
            }

        return {
            "status": "falhou",
            "tipo": tipo
        }

    return {
        "status": "acao_desconhecida",
        "tipo": tipo
    }

def detectar_atualizacao(mensagem, entidade):

    if not isinstance(mensagem, str):
        return None

    if entidade is None:
        return None

    texto = mensagem.strip()
    normalizado = texto.lower()

    gatilhos = [
        "adicione ",
        "adicionar ",
        "registre ",
        "registrar ",
        "defina ",
        "definir ",
        "altere ",
        "alterar ",
        "atualize ",
        "atualizar "
    ]

    gatilho_encontrado = None

    for gatilho in gatilhos:

        if normalizado.startswith(gatilho):
            gatilho_encontrado = gatilho
            break

    if gatilho_encontrado is None:
        return None

    conteudo = texto[len(gatilho_encontrado):].strip()

    if not conteudo:
        return None

    entidade_id = entidade.get("id")

    if entidade_id is None:
        return None

    return {
        "tipo": "acao_candidata",
        "acao": "atualizar_atributo",
        "entidade_id": entidade_id,
        "conteudo": conteudo
    }

def interpretar_atualizacao(candidata):

    if not isinstance(candidata, dict):
        return None

    if candidata.get("tipo") != "acao_candidata":
        return None

    if candidata.get("acao") != "atualizar_atributo":
        return None

    entidade_id = candidata.get("entidade_id")
    conteudo = candidata.get("conteudo")

    if not entidade_id or not conteudo:
        return None

    texto = conteudo.strip()

    regras = [
        (" aos objetivos", "objetivos"),
        (" aos projetos", "projetos"),
        (" às preferências", "preferencias"),
        (" as preferências", "preferencias"),
        (" à preferência", "preferencias"),
        (" a preferência", "preferencias"),
        (" como objetivo", "objetivos"),
        (" como projeto", "projetos"),
        (" como preferência", "preferencias"),
    ]

    normalizado = texto.lower()

    for sufixo, campo in regras:

        if normalizado.endswith(sufixo):

            valor = texto[:-len(sufixo)].strip()

            if not valor:
                return None

            return criar_atualizacao_atributo(
                entidade_id,
                campo,
                valor
            )

    return None

def executar_adicao_em_colecao(
    entidades,
    entidade_id,
    campo,
    valor
):

    entidade = entity_store.obter_por_id(
        entidades,
        entidade_id
    )

    if entidade is None:
        return {
            "status": "entidade_nao_encontrada"
        }

    atributos = entidade.setdefault(
        "atributos",
        {}
    )

    atual = atributos.get(campo)

    if atual is None:
        atual = []

    elif isinstance(atual, str):
        atual = [atual]

    elif not isinstance(atual, list):
        atual = [atual]

    if valor in atual:

        return {
            "status": "ja_existente",
            "entidade_id": entidade_id,
            "campo": campo,
            "valor": valor
        }

    atual.append(valor)

    atributos[campo] = atual

    entity_store.salvar_entidades(
        entidades
    )

    return {
        "status": "executada",
        "tipo": "adicionar",
        "entidade_id": entidade_id,
        "campo": campo,
        "valor": valor
    }

def executar_remocao_de_colecao(
    entidades,
    entidade_id,
    campo,
    valor
):

    entidade = entity_store.obter_por_id(
        entidades,
        entidade_id
    )

    if entidade is None:
        return {
            "status": "entidade_nao_encontrada"
        }

    atributos = entidade.setdefault(
        "atributos",
        {}
    )

    atual = atributos.get(campo)

    if atual is None:
        return {
            "status": "nao_encontrado",
            "entidade_id": entidade_id,
            "campo": campo,
            "valor": valor
        }

    if isinstance(atual, str):
        atual = [atual]

    elif not isinstance(atual, list):
        atual = [atual]

    if valor not in atual:
        return {
            "status": "nao_encontrado",
            "entidade_id": entidade_id,
            "campo": campo,
            "valor": valor
        }

    atual.remove(valor)

    atributos[campo] = atual

    entity_store.salvar_entidades(
        entidades
    )

    return {
        "status": "executada",
        "tipo": "remover",
        "entidade_id": entidade_id,
        "campo": campo,
        "valor": valor
    }

