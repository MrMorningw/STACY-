import os
import subprocess
import requests
import config


def gerar_resposta(
    api_key,
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{config.MODELO}:generateContent"
        f"?key={api_key}"
    )

    prompt_sistema = (
        config.PERSONALIDADE
        + "\n\n"
        + "MEMÓRIA PERSISTENTE DO USUÁRIO:\n"
        + contexto_memoria
    )

    if contexto_entidade is not None:

        prompt_sistema += (
            "\n\n"
            + "ENTIDADE ATUAL NO CONTEXTO:\n"
            + contexto_entidade
        )

    if contexto_conversa is not None:

        prompt_sistema += (
            "\n\n"
            + "CONTEXTO CONVERSACIONAL RECENTE:\n"
            + contexto_conversa
        )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": prompt_sistema
                }
            ]
        },
        "contents": historico
    }

    response = requests.post(
        url,
        json=payload,
        timeout=config.TIMEOUT_API
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"API retornou {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    return (
        data["candidates"][0]
        ["content"]["parts"][0]
        ["text"]
    )

def gerar_resposta_local(
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):
    url = "http://127.0.0.1:8080/v1/chat/completions"

    mensagens = [
        {
            "role": "system",
            "content": (
                config.PERSONALIDADE
                + "\n\nMEMÓRIA PERSISTENTE DO USUÁRIO:\n"
                + contexto_memoria
            )
        }
    ]

    if contexto_entidade:
        mensagens[0]["content"] += (
            "\n\nENTIDADE ATUAL:\n"
            + contexto_entidade
        )

    if contexto_conversa:
        mensagens[0]["content"] += (
            "\n\nCONTEXTO CONVERSACIONAL:\n"
            + contexto_conversa
        )

    for mensagem in historico:
        texto = ""

        for parte in mensagem.get("parts", []):
            if isinstance(parte, dict):
                texto += parte.get("text", "")
            elif isinstance(parte, str):
                texto += parte

        if texto:
            role = mensagem.get("role", "user")

            if role == "model":
                role = "assistant"

            mensagens.append({
                "role": role,
                "content": texto
            })

    payload = {
        "messages": mensagens,
        "temperature": 0.7,
        "max_tokens": 64,
        "stream": False
    }

    response = requests.post(
        url,
        json=payload,
        timeout=15
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"IA local HTTP {response.status_code}: "
            + response.text
        )

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()
