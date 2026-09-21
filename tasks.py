import json
import os
import uuid
from datetime import datetime


ARQUIVO = os.path.join(
    os.path.dirname(__file__),
    "tasks.json"
)


def carregar():

    if not os.path.exists(ARQUIVO):
        return []

    try:
        with open(
            ARQUIVO,
            "r",
            encoding="utf-8"
        ) as arquivo:
            dados = json.load(arquivo)

        if isinstance(dados, list):
            return dados

    except (json.JSONDecodeError, OSError):
        pass

    return []


def salvar(tarefas):

    with open(
        ARQUIVO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            tarefas,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


def criar(titulo, data=None, hora=None):

    if not titulo or not titulo.strip():
        return None

    tarefa = {
        "id": str(uuid.uuid4()),
        "titulo": titulo.strip(),
        "data": data,
        "hora": hora,
        "status": "pendente",
        "criada_em": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    tarefas = carregar()
    tarefas.append(tarefa)
    salvar(tarefas)

    return tarefa


def listar(
    data=None,
    status="pendente"
):

    tarefas = carregar()

    resultado = []

    for tarefa in tarefas:

        if status is not None:
            if tarefa.get("status") != status:
                continue

        if data is not None:
            if tarefa.get("data") != data:
                continue

        resultado.append(tarefa)

    return resultado


def buscar(termo, status=None):

    if not termo:
        return None

    termo = termo.lower().strip()

    tarefas = carregar()

    encontrados = []

    for tarefa in tarefas:

        titulo = tarefa.get(
            "titulo",
            ""
        ).lower()

        if status is not None:
            if tarefa.get("status") != status:
                continue

        if termo in titulo:

            encontrados.append(
                tarefa
            )

    return encontrados


def concluir(tarefa_id):

    tarefas = carregar()

    for tarefa in tarefas:

        if tarefa.get("id") == tarefa_id:

            tarefa["status"] = "concluida"

            tarefa["concluida_em"] = (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )

            salvar(tarefas)

            return tarefa

    return None


def remover(tarefa_id):

    tarefas = carregar()

    novas_tarefas = []

    removida = None

    for tarefa in tarefas:

        if tarefa.get("id") == tarefa_id:
            removida = tarefa
        else:
            novas_tarefas.append(tarefa)

    if removida is None:
        return None

    salvar(novas_tarefas)

    return removida


def atualizar(tarefa_id, data=None, hora=None):
    """Atualiza somente os campos fornecidos de uma tarefa existente."""
    if not tarefa_id:
        return None

    tarefas = carregar()

    for tarefa in tarefas:
        if tarefa.get("id") != tarefa_id:
            continue

        if data is not None:
            tarefa["data"] = data
        if hora is not None:
            tarefa["hora"] = hora

        salvar(tarefas)
        return tarefa

    return None
