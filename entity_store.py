import json
import os

import entity


ARQUIVO_ENTIDADES = "entities.json"


def criar_estrutura():
    return {
        "entidades": []
    }


def carregar_entidades():
    if not os.path.exists(ARQUIVO_ENTIDADES):
        return criar_estrutura()

    try:
        with open(
            ARQUIVO_ENTIDADES,
            "r",
            encoding="utf-8"
        ) as arquivo:
            dados = json.load(arquivo)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return criar_estrutura()

    if not isinstance(dados, dict):
        return criar_estrutura()

    if "entidades" not in dados:
        dados["entidades"] = []

    if not isinstance(dados["entidades"], list):
        dados["entidades"] = []

    return dados


def salvar_entidades(dados):
    with open(
        ARQUIVO_ENTIDADES,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


def listar_entidades(dados):
    if not isinstance(dados, dict):
        return []

    return dados.get("entidades", [])


def adicionar_entidade(dados, categoria, nome):
    entidades = listar_entidades(dados)

    nova_entidade = entity.criar_proxima_entidade(
        entidades,
        categoria,
        nome
    )

    if nova_entidade is None:
        return None

    entidades.append(nova_entidade)

    salvar_entidades(dados)

    return nova_entidade


def obter_por_id(dados, identificador):
    entidades = listar_entidades(dados)

    return entity.obter_entidade_por_id(
        entidades,
        identificador
    )


def obter_por_uuid(dados, identificador):
    entidades = listar_entidades(dados)

    return entity.obter_entidade_por_uuid(
        entidades,
        identificador
    )


def atualizar_por_id(dados, identificador, campo, valor):
    entidade = obter_por_id(
        dados,
        identificador
    )

    if entidade is None:
        return False

    atualizado = entity.atualizar_entidade(
        entidade,
        campo,
        valor
    )

    if atualizado:
        salvar_entidades(dados)

    return atualizado


def excluir_por_id(dados, identificador):
    entidades = listar_entidades(dados)

    excluido = entity.excluir_entidade(
        entidades,
        identificador
    )

    if excluido:
        salvar_entidades(dados)

    return excluido

def obter_por_nome(dados, nome):
    entidades = listar_entidades(dados)

    return entity.obter_entidade_por_nome(
        entidades,
        nome
    )


def buscar_por_texto(dados, texto):
    entidades = listar_entidades(dados)

    return entity.buscar_entidades_por_texto(
        entidades,
        texto
    )
def definir_contexto(dados, identificador):
    entidade = obter_por_id(dados, identificador)

    if entidade is None:
        return None

    return {
        "id": entidade["id"],
        "uuid": entidade["uuid"],
        "categoria": entidade["categoria"],
        "nome": entidade["nome"]
    }

def definir_contexto_persistente(dados, identificador):
    entidade = obter_por_id(dados, identificador)

    if entidade is None:
        return None

    dados["contexto"] = {
        "id": entidade["id"],
        "uuid": entidade["uuid"],
        "categoria": entidade["categoria"],
        "nome": entidade["nome"]
    }

    salvar_entidades(dados)

    return dados["contexto"]


def obter_contexto_persistente(dados):
    return dados.get("contexto")


def limpar_contexto_persistente(dados):
    if "contexto" not in dados:
        return False

    del dados["contexto"]

    salvar_entidades(dados)

    return True

