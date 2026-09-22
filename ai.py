import requests
import json
import config
import response_guard
from urllib.parse import urlparse


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
        + "\n\nA ÚLTIMA MENSAGEM DO USUÁRIO é a consulta atual e deve ser o foco "
        + "principal da resposta. Responda diretamente à consulta atual; não responda "
        + "uma mensagem anterior e não repita uma resposta anterior. O histórico serve "
        + "apenas como contexto quando necessário."
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

    historico = historico[-12:] if historico else []

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
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        },
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
        partes = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(
            f"Resposta Gemini inválida: {data}"
        ) from erro

    textos = []
    for parte in partes:
        if isinstance(parte, dict) and parte.get("text"):
            textos.append(parte["text"].strip())

    resposta = "\n".join(texto for texto in textos if texto).strip()
    return response_guard.validar_resposta(resposta, historico[-1]["parts"][0]["text"] if historico and historico[-1].get("parts") else None)


def gerar_resposta_pesquisa(
    api_key,
    historico
):
    """Pesquisa fatos externos com Gemini + Google Search, sem memória persistente."""
    if not api_key:
        raise RuntimeError("Chave da Gemini não configurada.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{config.MODELO}:generateContent"
    )

    # A pesquisa recebe o contexto externo já preparado pelo orchestrator.
    # Não reduza para apenas a última mensagem: referências como "isso",
    # "ele" e "sua classificação" dependem do turno anterior.
    historico_pesquisa = historico[-8:] if historico else []

    sistema = (
        "Você é STACY, assistente pessoal do senhor Danley. "
        "Responda em português, de forma objetiva. "
        "Esta é uma consulta externa. Use obrigatoriamente a Pesquisa Google "
        "para verificar os fatos antes de responder. "
        "Não invente, não chute e não complete lacunas por suposição. "
        "Se as fontes não forem suficientes, diga que não foi possível verificar. "
        "Diferencie fatos de estimativas ou opiniões e informe as fontes quando "
        "forem relevantes. Não revele nem solicite dados pessoais desnecessários. "
        "O histórico anterior existe para resolver referências da conversa, como "
        "ele, ela, isso, sua classificação ou esse objeto. Identifique a referência "
        "pelo contexto antes de responder. A última mensagem do usuário é o pedido "
        "atual e tem prioridade."
    )

    contents = []
    for mensagem in historico_pesquisa:
        texto = ""
        for parte in mensagem.get("parts", []):
            if isinstance(parte, dict):
                texto += parte.get("text", "")
            elif isinstance(parte, str):
                texto += parte

        texto = texto.strip()
        if texto:
            role = mensagem.get("role", "user")
            if role not in {"user", "model"}:
                role = "user"

            contents.append({
                "role": role,
                "parts": [{"text": texto[-2000:]}]
            })

    if not contents:
        raise RuntimeError("Consulta externa vazia.")

    payload = {
        "system_instruction": {"parts": [{"text": sistema}]},
        "contents": contents,
        "tools": [{"google_search": {}}]
    }

    response = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=config.RESEARCH_API_TIMEOUT
    )

    if response.status_code != 200:
        detalhe = response.text[:500]
        raise RuntimeError(
            f"Pesquisa Gemini HTTP {response.status_code}: {detalhe}"
        )

    try:
        data = response.json()
    except ValueError as erro:
        raise RuntimeError("Pesquisa Gemini retornou JSON inválido.") from erro

    try:
        partes = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(
            f"Resposta da pesquisa Gemini inválida: {data}"
        ) from erro

    textos = []
    for parte in partes:
        if isinstance(parte, dict) and parte.get("text"):
            textos.append(parte["text"].strip())

    resposta = "\n".join(texto for texto in textos if texto).strip()
    resposta = response_guard.validar_resposta(resposta, historico_pesquisa[-1]["parts"][0]["text"] if historico_pesquisa and historico_pesquisa[-1].get("parts") else None)

    fontes = []
    vistos = set()
    grounding = data.get("candidates", [{}])[0].get(
        "groundingMetadata", {}
    )

    for chunk in grounding.get("groundingChunks", []):
        web = chunk.get("web", {}) if isinstance(chunk, dict) else {}
        uri = web.get("uri")
        titulo = web.get("title") or uri

        if not isinstance(uri, str):
            continue

        parsed = urlparse(uri)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue

        if uri not in vistos:
            vistos.add(uri)
            fontes.append({
                "titulo": titulo,
                "url": uri
            })

    fontes = response_guard.validar_fontes(fontes)
    if not fontes:
        raise RuntimeError(
            "Pesquisa Gemini não retornou fontes verificáveis."
        )

    return {"resposta": resposta, "fontes": fontes}

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
    historico_local = historico[-4:] if historico else []

    def _limitar(texto, limite):
        texto = texto or ""
        return texto[-limite:]

    memoria_local = _limitar(contexto_memoria, 1000)
    entidade_local = _limitar(contexto_entidade, 500)
    conversa_local = _limitar(contexto_conversa, 800)

    sistema_local = (
        "Você é STACY, assistente pessoal do senhor Danley. "
        "Responda em português, de forma curta, natural e útil. "
        "A ÚLTIMA MENSAGEM DO USUÁRIO é a consulta atual e deve ser o foco principal da resposta. "
        "Responda diretamente à consulta atual; não responda uma mensagem anterior e não repita "
        "uma resposta anterior. O histórico serve apenas para contexto quando necessário. "
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
        sistema_local += (
            "\nCONTEXTO RECENTE (use somente como apoio, nunca como consulta atual):\n"
            + conversa_local
        )

    mensagens = [{"role": "system", "content": sistema_local}]

    # O último item é a consulta atual: mantenha-a explicitamente por último.
    # Isso reduz a chance de modelos pequenos responderem ao histórico anterior.
    mensagens_anteriores = historico_local[:-1]
    mensagem_atual = historico_local[-1] if historico_local else None

    for mensagem in mensagens_anteriores:
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

    if mensagem_atual:
        texto = ""
        for parte in mensagem_atual.get("parts", []):
            if isinstance(parte, dict):
                texto += parte.get("text", "")
            elif isinstance(parte, str):
                texto += parte

        texto = _limitar(texto, 600)
        if texto:
            mensagens.append({"role": "user", "content": texto})

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

    return response_guard.validar_resposta(
        resposta,
        historico_local[-1]["parts"][0]["text"] if historico_local and historico_local[-1].get("parts") else None
    )

def analisar_rota_local(mensagem, contexto_conversa=None):
    """Interpreta linguagem natural para roteamento; não executa ações."""
    if not verificar_ia_local():
        raise RuntimeError("servidor local não está acessível.")

    capacidades = (
        "chat=conversa; answer=conhecimento; research=pesquisa externa; "
        "action=ação executável; memory=memória; clarify=pedido ambíguo."
    )
    contexto = (contexto_conversa or "").strip()
    if len(contexto) > 1200:
        contexto = contexto[-1200:]

    sistema = (
        "Você é o intérprete de linguagem da STACY. "
        "Apenas classifique a intenção e a capacidade necessária. "
        "Não execute ações, não grave memória, não pesquise e não responda. "
        "Retorne SOMENTE JSON válido com as chaves modo, capacidade, consulta, "
        "dados, confidence e motivo. dados deve ser um objeto vazio quando não "
        "houver operação estruturada. Para tarefas, use dados com acao, titulo, "
        "data e hora quando aplicável. Para memória, use acao, categoria e valor "
        "quando aplicável. modo deve ser chat, answer, research, action, memory "
        "ou clarify. capacidade deve ser chat, knowledge, web, tasks, memory ou "
        "core. Se houver dúvida real ou faltar dado essencial para uma ação, use "
        "clarify. Não invente dados. " + capacidades
    )
    if contexto:
        sistema += "\nContexto recente para resolver referências:\n" + contexto

    payload = {
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": mensagem.strip()}
        ],
        "temperature": 0.0,
        "max_tokens": getattr(config, "LOCAL_ROUTER_MAX_TOKENS", 96),
        "stream": False
    }

    modelo = getattr(config, "LOCAL_ROUTER_MODEL", None)
    if modelo:
        payload["model"] = modelo

    response = requests.post(
        config.LOCAL_AI_URL,
        json=payload,
        timeout=config.LOCAL_AI_TIMEOUT
    )
    if response.status_code != 200:
        raise RuntimeError(f"Roteador local HTTP {response.status_code}: {response.text[:500]}")

    data = response.json()
    try:
        texto = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(f"Resposta do roteador local inválida: {data}") from erro

    texto = texto.strip()
    if texto.startswith("```") and texto.endswith("```"):
        texto = texto.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        decisao = json.loads(texto)
    except (ValueError, TypeError) as erro:
        raise RuntimeError(f"Roteador local não retornou JSON válido: {texto}") from erro

    if not isinstance(decisao, dict):
        raise RuntimeError("Roteador local retornou formato inválido.")

    return decisao


def gerar_resposta_hibrida(
    api_key,
    historico,
    contexto_memoria,
    contexto_entidade=None,
    contexto_conversa=None,
    historico_gemini=None
):
    """Política definitiva de geração: IA local primeiro, Gemini como fallback."""
    erros = []

    try:
        if not verificar_ia_local():
            raise RuntimeError("servidor local não está acessível")

        resposta = gerar_resposta_local(
            historico,
            contexto_memoria,
            contexto_entidade,
            contexto_conversa
        )

        if not isinstance(resposta, str) or not resposta.strip():
            raise RuntimeError("IA local retornou resposta vazia")

        return {
            "resposta": resposta.strip(),
            "origem": "local",
            "fallback": False,
            "erros": []
        }

    except Exception as erro_local:
        erros.append(f"IA local: {erro_local}")

    try:
        resposta = gerar_resposta(
            api_key,
            historico_gemini if historico_gemini is not None else historico,
            contexto_memoria,
            contexto_entidade,
            contexto_conversa
        )

        if not isinstance(resposta, str) or not resposta.strip():
            raise RuntimeError("Gemini retornou resposta vazia")

        return {
            "resposta": resposta.strip(),
            "origem": "gemini",
            "fallback": True,
            "erros": erros
        }

    except Exception as erro_gemini:
        erros.append(f"Gemini: {erro_gemini}")
        raise RuntimeError(
            "Não consegui obter uma resposta da IA agora, senhor. "
            "A IA local e o Gemini não responderam corretamente."
        ) from erro_gemini
