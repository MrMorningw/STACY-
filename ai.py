import requests
import config


def _construir_mensagens(
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):
    sistema = (
        config.PERSONALIDADE
        + "\n\nMEMÓRIA PERSISTENTE DO USUÁRIO:\n"
        + contexto_memoria
    )

    if contexto_entidade:
        sistema += (
            "\n\nENTIDADE ATUAL:\n"
            + contexto_entidade
        )

    if contexto_conversa:
        sistema += (
            "\n\nCONTEXTO CONVERSACIONAL RECENTE:\n"
            + contexto_conversa
        )

    mensagens = [
        {
            "role": "system",
            "content": sistema
        }
    ]

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

    return mensagens


def gerar_resposta(
    api_key,
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):
    if not api_key:
        raise RuntimeError("Chave da Gemini não configurada.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{config.MODELO}:generateContent"
        f"?key={api_key}"
    )

    mensagens = _construir_mensagens(
        historico,
        contexto_memoria,
        contexto_entidade,
        contexto_conversa
    )

    contents = []

    for mensagem in mensagens[1:]:
        contents.append({
            "role": (
                "model"
                if mensagem["role"] == "assistant"
                else "user"
            ),
            "parts": [
                {
                    "text": mensagem["content"]
                }
            ]
        })

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": mensagens[0]["content"]
                }
            ]
        },
        "contents": contents
    }

    response = requests.post(
        url,
        json=payload,
        timeout=config.TIMEOUT_API
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"API Gemini retornou {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    try:
        return (
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        ).strip()
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(
            f"Resposta Gemini inválida: {data}"
        ) from erro


def gerar_resposta_local(
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):
    url = config.LOCAL_AI_URL

    # A IA local roda no telefone: use um contexto compacto para
    # evitar que memória/histórico grande provoque timeouts.
    historico_local = historico[-6:] if historico else []

    def _limitar(texto, limite):
        texto = texto or ""
        return texto[-limite:]

    memoria_local = _limitar(contexto_memoria, 2000)
    entidade_local = _limitar(contexto_entidade, 1000)
    conversa_local = _limitar(contexto_conversa, 2000)

    mensagens = _construir_mensagens(
        historico_local,
        memoria_local,
        entidade_local,
        conversa_local
    )

    payload = {
        "messages": mensagens,
        "temperature": 0.7,
        "max_tokens": config.LOCAL_MAX_TOKENS,
        "stream": False
    }

    response = requests.post(
        url,
        json=payload,
        timeout=config.LOCAL_AI_TIMEOUT
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"IA local HTTP {response.status_code}: "
            + response.text
        )

    data = response.json()

    try:
        resposta = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(
            f"Resposta da IA local inválida: {data}"
        ) from erro

    if not resposta:
        raise RuntimeError("IA local retornou resposta vazia.")

    return resposta
