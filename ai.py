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
        + "\n\nDADOS CONFIÁVEIS DO SISTEMA — MEMÓRIA PERSISTENTE:\n"
        + contexto_memoria
        + "\n\nINSTRUÇÃO CRÍTICA SOBRE OS DADOS:\n"
        + "Os dados acima são fornecidos pelo STACY CORE e estão disponíveis "
        + "para você nesta resposta. Quando o usuário perguntar sobre nome, "
        + "projetos, objetivos ou outras informações presentes nesses dados, "
        + "responda usando-os diretamente. NÃO diga que não possui acesso à "
        + "memória quando os dados estiverem presentes. NÃO invente dados."
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


def verificar_ia_local():
    """Verifica rapidamente se o llama-server local está acessível."""
    health_url = config.LOCAL_AI_URL.rsplit("/v1/", 1)[0] + "/health"

    try:
        response = requests.get(
            health_url,
            timeout=config.LOCAL_HEALTH_TIMEOUT
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def gerar_resposta_local(
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None
):
    url = config.LOCAL_AI_URL

    # O modelo local roda no telefone: mantenha o prompt pequeno.
    # Contexto excessivo aumenta muito o tempo de processamento no Qwen 1.5B.
    historico_local = historico[-2:] if historico else []

    def _limitar(texto, limite):
        texto = texto or ""
        return texto[-limite:]

    memoria_local = _limitar(contexto_memoria, 1000)
    entidade_local = _limitar(contexto_entidade, 500)
    conversa_local = _limitar(contexto_conversa, 800)

    sistema_local = (
        "Você é STACY, assistente pessoal do senhor Danley. "
        "Responda em português, de forma curta, natural e útil. "
        "Use os dados fornecidos pelo STACY CORE quando forem relevantes. "
        "Não diga que não possui acesso à memória quando os dados estiverem presentes. "
        "Não invente informações. Não afirme experiências próprias que não aconteceram. "
        "Para perguntas comuns, seguras e permitidas, responda diretamente e não recuse sem motivo. "
        "Quando não tiver conhecimento confiável sobre um fato, não invente nem chute; "
        "admita a incerteza de forma curta. "
        "Não termine uma frase pela metade; conclua a resposta antes de encerrar."
    )

    if memoria_local:
        sistema_local += "\nMEMÓRIA DO CORE:\n" + memoria_local

    if entidade_local:
        sistema_local += "\nENTIDADE ATUAL:\n" + entidade_local

    if conversa_local:
        sistema_local += "\nCONTEXTO RECENTE:\n" + conversa_local

    mensagens = [{"role": "system", "content": sistema_local}]

    for mensagem in historico_local:
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
            # Evita reenviar mensagens extensas de erro/quota ao modelo local.
            texto = _limitar(texto, 400)
            mensagens.append({"role": role, "content": texto})

    payload = {
        "messages": mensagens,
        "temperature": 0.3,
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
            f"IA local HTTP {response.status_code}: " + response.text
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
