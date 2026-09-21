import re
import unicodedata
from difflib import SequenceMatcher


def normalizar_flexivel(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    texto = " ".join(texto.split())
    return texto.rstrip("?!.,;: ").replace("saos ", "sao ")


def corresponde_frase(texto, candidatos, limiar=0.93):
    """Compara uma intenção sem exigir ortografia perfeita."""
    alvo = normalizar_flexivel(texto)

    for candidato in candidatos:
        candidato_normalizado = normalizar_flexivel(candidato)

        if alvo == candidato_normalizado:
            return True

        if len(alvo) < 8:
            continue

        similaridade = SequenceMatcher(
            None,
            alvo,
            candidato_normalizado
        ).ratio()

        if similaridade >= limiar:
            return True

    return False

def remover_prefixo_conversacional(texto):
    """Remove uma reação/conector inicial sem apagar o pedido seguinte."""
    import re

    texto = (texto or "").strip()
    if not texto:
        return texto

    prefixos = (
        "que bom", "otimo", "ótimo", "perfeito", "certo", "ok",
        "beleza", "entao", "então", "show", "legal", "entendi"
    )
    padrao = r"^\s*(?:" + "|".join(re.escape(p) for p in prefixos) + r")"
    padrao += r"(?:\s*[,;:.!?-]\s*|\s+)(.+)$"
    resultado = re.match(padrao, texto, flags=re.IGNORECASE)
    if resultado:
        return resultado.group(1).strip()
    return texto


def _corrigir_erros_tarefa(texto):
    """Corrige somente erros ortográficos inequívocos no contexto de tarefas."""
    substituicoes = {
        "tarafe": "tarefa",
        "tareffa": "tarefa",
        "estudaf": "estudar",
        "estudr": "estudar",
        "amanhaa": "amanha",
        "amanh": "amanha",
        "cokega": "colega",
        "direto penal": "direito penal",
    }
    resultado = texto
    for errado, correto in substituicoes.items():
        resultado = re.sub(
            r"(?<!\w)" + re.escape(errado) + r"(?!\w)",
            correto,
            resultado,
            flags=re.IGNORECASE
        )
    return resultado


def interpretar(mensagem):

    texto = remover_prefixo_conversacional(mensagem)
    normalizado = texto.lower().rstrip("?!.,;: ")
    normalizado_sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", normalizado)
        if unicodedata.category(caractere) != "Mn"
    )
    normalizado_sem_acentos = normalizado_sem_acentos.rstrip("?!.,;: ")
    normalizado_sem_acentos = normalizado_sem_acentos.replace("saos ", "sao ")

    if not texto:
        return None

    if corresponde_frase(normalizado, ["sair", "exit", "quit"], limiar=0.90):
        return {"tipo": "comando", "acao": "sair"}

    if normalizado_sem_acentos in [
        "memoria", "mostre minha memoria", "mostra minha memoria",
        "mostrar minha memoria", "o que voce guardou",
        "o que voce guardou de mim", "o que voce lembra de mim",
        "o que esta guardado", "o que esta salvo",
        "quais informacoes voce guardou"
    ]:
        return {"tipo": "memoria", "acao": "mostrar"}

    if normalizado.startswith("buscar "):
        return {"tipo": "memoria", "acao": "buscar", "conteudo": texto[7:].strip()}

    if normalizado.startswith("memorize "):
        return interpretar_memoria("memorizar", texto[9:].strip())

    if normalizado.startswith("esquecer "):
        return interpretar_memoria("esquecer", texto[9:].strip())

    consultas_usuario = [
        "qual é o meu nome", "qual meu nome", "como eu me chamo",
        "você sabe meu nome", "e o meu nome", "e meu nome"
    ]

    # Identificação do usuário tem precedência sobre a identidade da STACY.
    # Isso evita que a comparação aproximada de "seu nome" capture
    # erroneamente frases como "e o meu nome?".
    if normalizado_sem_acentos.rstrip("?!. ,;: ") in {
        "qual e o meu nome", "qual meu nome", "como eu me chamo",
        "voce sabe meu nome", "e o meu nome", "e meu nome"
    }:
        return {"tipo": "memoria", "acao": "consultar", "categoria": "usuario"}

    consultas_stacy = [
        "qual seu nome", "qual o seu nome", "como voce se chama",
        "quem e voce", "qual e o seu nome",
    ]

    if corresponde_frase(
        normalizado_sem_acentos.rstrip("?!. ,;: "),
        consultas_stacy,
        limiar=0.90
    ):
        return {"tipo": "identidade", "alvo": "stacy"}

    consultas_projetos = [
        "quais são meus projetos", "quais meus projetos",
        "quais projetos eu tenho", "você lembra meus projetos"
    ]

    consultas_objetivos = [
        "quais são meus objetivos", "quais meus objetivos",
        "quais objetivos eu tenho", "você lembra meus objetivos"
    ]

    consulta = normalizado.rstrip("?!.,;: ")
    consulta_flexivel = normalizado_sem_acentos.rstrip("?!.,;: ")

    prefixos_conversacionais = ("otimo", "certo", "ok", "beleza", "entao")
    consulta_sem_prefixo = consulta_flexivel
    for prefixo in prefixos_conversacionais:
        restante = consulta_sem_prefixo[len(prefixo):]
        if consulta_sem_prefixo == prefixo:
            consulta_sem_prefixo = ""
            break
        if (
            consulta_sem_prefixo.startswith(prefixo)
            and restante
            and restante[0] in " ,;:-.!?"
        ):
            consulta_sem_prefixo = restante.lstrip(" ,;:-.!?").strip()
            break

    if corresponde_frase(consulta_sem_prefixo, consultas_usuario + [
        "qual e o meu nome", "qual meu nome", "como eu me chamo",
        "voce sabe meu nome", "e o meu nome", "e meu nome"
    ]):
        return {"tipo": "memoria", "acao": "consultar", "categoria": "usuario"}

    if corresponde_frase(consulta_sem_prefixo, consultas_projetos + [
        "quais sao meus projetos", "quais meus projetos",
        "quais projetos eu tenho", "voce lembra meus projetos",
        "quais sao os meus projetos", "e os meus projetos", "e meus projetos"
    ]):
        return {"tipo": "memoria", "acao": "consultar", "categoria": "projetos"}

    if corresponde_frase(consulta_sem_prefixo, consultas_objetivos + [
        "quais sao meus objetivos", "quais meus objetivos",
        "quais objetivos eu tenho", "voce lembra meus objetivos",
        "quais sao os meus objetivos", "e os meus objetivos", "e meus objetivos",
        "quais sao minhas metas", "quais sao as minhas metas",
        "quais minhas metas", "e minhas metas", "e as minhas metas", "minhas metas"
    ]):
        return {"tipo": "memoria", "acao": "consultar", "categoria": "objetivos"}

    tarefa = interpretar_tarefa(texto)
    if tarefa is not None:
        return tarefa

    gatilhos_memorizar = [
        "guarde ", "guarda ", "guardar ", "lembre ", "lembra ",
        "registre ", "registra ", "anote ", "anota ", "memorize "
    ]

    gatilhos_esquecer = [
        "esqueça ", "esquece ", "apague ", "apaga ", "remova ", "remove "
    ]

    for gatilho in gatilhos_memorizar:
        if normalizado.startswith(gatilho):
            return interpretar_memoria("memorizar", texto[len(gatilho):].strip())

    for gatilho in gatilhos_esquecer:
        if normalizado.startswith(gatilho):
            return interpretar_memoria("esquecer", texto[len(gatilho):].strip())

    return None


def interpretar_memoria(acao, conteudo):
    categoria = None
    valor = conteudo
    natural = conteudo.strip()
    natural_lower = natural.lower()

    prefixos = [
        "o projeto ", "projeto ", "os projetos ", "projetos ",
        "o objetivo ", "objetivo ", "os objetivos ", "objetivos ",
        "a preferência ", "preferência ", "as preferências ", "preferências "
    ]

    for prefixo in prefixos:
        if natural_lower.startswith(prefixo):
            resto = natural[len(prefixo):].strip()
            if resto:
                if "projeto" in prefixo:
                    categoria = "projetos"
                elif "objetivo" in prefixo:
                    categoria = "objetivos"
                elif "preferência" in prefixo:
                    categoria = "preferencias"
                return {
                    "tipo": "memoria", "acao": acao,
                    "categoria": categoria, "valor": resto
                }

    if "=" in conteudo:
        esquerda, valor = conteudo.split("=", 1)
        esquerda = esquerda.strip()
        valor = valor.strip()

        if "." in esquerda:
            categoria, chave = esquerda.split(".", 1)
            return {
                "tipo": "memoria", "acao": acao,
                "categoria": categoria.strip().lower(),
                "chave": chave.strip(), "valor": valor
            }

        categoria = esquerda.strip().lower()
        if categoria == "usuario":
            valor = f"nome={valor}"

        return {
            "tipo": "memoria", "acao": acao,
            "categoria": categoria, "valor": valor
        }

    if "." in conteudo:
        categoria, valor = conteudo.split(".", 1)
        return {
            "tipo": "memoria", "acao": acao,
            "categoria": categoria.strip().lower(),
            "valor": valor.strip()
        }

    return {"tipo": "memoria", "acao": acao, "conteudo": conteudo}


def detectar_memoria_candidata(mensagem):
    texto = mensagem.strip()
    normalizado = texto.lower()
    gatilhos = {
        "objetivos": ["meu objetivo é ", "meus objetivos são ", "meu objetivo será ", "meus objetivos serão "],
        "projetos": ["meu projeto é ", "meus projetos são "],
        "preferencias": ["eu prefiro ", "minha preferência é ", "minhas preferências são "]
    }

    for categoria, lista_gatilhos in gatilhos.items():
        for gatilho in lista_gatilhos:
            if normalizado.startswith(gatilho):
                valor = texto[len(gatilho):].strip()
                if not valor:
                    return None
                return {"tipo": "memoria_candidata", "categoria": categoria, "valor": valor}
    return None


def detectar_consulta_memoria(mensagem):
    texto = mensagem.strip().lower()
    consultas = {
        "projetos": [
            "quais são meus projetos", "quais sao meus projetos",
            "quais são os meus projetos", "quais sao os meus projetos", "meus projetos"
        ],
        "objetivos": [
            "quais são meus objetivos", "quais sao meus objetivos",
            "quais são os meus objetivos", "quais sao os meus objetivos", "meus objetivos"
        ],
        "preferencias": [
            "quais são minhas preferências", "quais sao minhas preferencias",
            "quais são as minhas preferências", "quais sao as minhas preferencias",
            "minhas preferências", "minhas preferencias"
        ],
        "informacoes": [
            "quais são minhas informações", "quais sao minhas informacoes",
            "quais são as minhas informações", "quais sao as minhas informacoes",
            "minhas informações", "minhas informacoes"
        ]
    }

    for categoria, frases in consultas.items():
        for frase in frases:
            if texto == frase:
                return {"tipo": "consulta_memoria", "categoria": categoria}
    return None


def detectar_consulta_especifica_memoria(mensagem):
    texto = mensagem.strip()
    prefixos = [
        "qual é o meu projeto ", "qual e o meu projeto ",
        "qual é o meu objetivo ", "qual e o meu objetivo ",
        "qual é a minha preferência ", "qual e a minha preferencia ",
        "o que é o meu projeto ", "o que e o meu projeto ",
        "o que você sabe sobre meu projeto ", "o que voce sabe sobre meu projeto "
    ]
    texto_lower = texto.lower()

    for prefixo in prefixos:
        if texto_lower.startswith(prefixo):
            termo = texto[len(prefixo):].strip()
            if not termo:
                return None
            if "projeto" in prefixo:
                categoria = "projetos"
            elif "objetivo" in prefixo:
                categoria = "objetivos"
            elif "preferência" in prefixo or "preferencia" in prefixo:
                categoria = "preferencias"
            else:
                categoria = "projetos"
            return {"tipo": "consulta_especifica_memoria", "categoria": categoria, "termo": termo}
    return None


def detectar_referencia_memoria(mensagem):
    texto = mensagem.strip().lower()
    for caractere in "?!.,;:":
        texto = texto.replace(caractere, "")
    texto = " ".join(texto.split())

    referencias = [
        "qual é o id dele", "qual e o id dele", "qual é o id dela", "qual e o id dela",
        "qual é o id desse projeto", "qual e o id desse projeto",
        "qual é o id dessa memória", "qual e o id dessa memoria",
        "qual é o valor dele", "qual e o valor dele",
        "qual é o valor dessa memória", "qual e o valor dessa memoria"
    ]

    for referencia in referencias:
        if texto == referencia:
            return {"tipo": "referencia_memoria", "acao": "consultar"}

    tarefa = interpretar_tarefa(mensagem)
    if tarefa is not None:
        return tarefa
    return None


def extrair_data_hora_tarefa(texto):
    from datetime import datetime, timedelta
    import re

    data = None
    hora = None
    restante = texto.strip()
    agora = datetime.now()

    padroes_hora = [
        r"\s+às\s+(\d{1,2})(?:[:h](\d{2}))?\s+horas?(?=\s|$)",
        r"\s+às\s+(\d{1,2})(?:[:h](\d{2}))?(?=\s|$)",
        r"\s+as\s+(\d{1,2})(?:[:h](\d{2}))?\s+horas?(?=\s|$)",
        r"\s+as\s+(\d{1,2})(?:[:h](\d{2}))?(?=\s|$)",
        r"\s+(\d{1,2})h(\d{2})?(?=\s|$)",
        r"\s+(\d{1,2})\s+horas?(?=\s|$)",
        r"\s+(\d{1,2})(?!\s+horas?)(?=\s|$)"
    ]

    for padrao in padroes_hora:
        resultado = re.search(padrao, restante, flags=re.IGNORECASE)
        if resultado:
            horas = int(resultado.group(1))
            minutos = 0
            if resultado.lastindex and resultado.lastindex >= 2 and resultado.group(2):
                minutos = int(resultado.group(2))
            if 0 <= horas <= 23 and 0 <= minutos <= 59:
                hora = f"{horas:02d}:{minutos:02d}"
                # Remove somente o horário; preserva o texto posterior do título.
                restante = (
                    restante[:resultado.start()]
                    + restante[resultado.end():]
                ).strip()
                break

    datas_relativas = {
        "hoje": agora.date(),
        "amanhã": agora.date() + timedelta(days=1),
        "amanha": agora.date() + timedelta(days=1),
        "depois de amanhã": agora.date() + timedelta(days=2),
        "depois de amanha": agora.date() + timedelta(days=2)
    }

    encontrada = None
    for expressao, data_calculada in sorted(
        datas_relativas.items(), key=lambda item: len(item[0]), reverse=True
    ):
        padrao = r"\b" + re.escape(expressao) + r"\b"
        if re.search(padrao, restante, flags=re.IGNORECASE):
            encontrada = (expressao, data_calculada)
            break

    if encontrada:
        expressao, data_calculada = encontrada
        data = data_calculada.isoformat()
        restante = re.sub(
            r"\b" + re.escape(expressao) + r"\b",
            "",
            restante,
            count=1,
            flags=re.IGNORECASE
        ).strip()
        restante = re.sub(r"\bde\s*$", "", restante, flags=re.IGNORECASE).strip()

    if data is None:
        resultado = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", restante)
        if resultado:
            try:
                datetime.strptime(resultado.group(1), "%Y-%m-%d")
                data = resultado.group(1)
                restante = (
                    restante[:resultado.start()] + " " + restante[resultado.end():]
                ).strip()
            except ValueError:
                pass

    restante = re.sub(r"\s+", " ", restante).strip()
    restante = re.sub(r"\s+(?:às|as)\s*$", "", restante, flags=re.IGNORECASE).strip()
    return restante, data, hora


def interpretar_tarefa(mensagem):
    texto_original = mensagem.strip()
    normalizado_original = texto_original.lower().rstrip("?!.,;: ")
    texto = _corrigir_erros_tarefa(texto_original)
    normalizado = texto.lower().rstrip("?!.,;: ")

    referencias_tarefa = (
        "crie essa tarefa", "criar essa tarefa",
        "adicione essa tarefa", "adicionar essa tarefa",
        "anote essa tarefa", "anotar essa tarefa"
    )

    consultas_ultima_tarefa = (
        "qual a ultima tarefa criada",
        "qual e a ultima tarefa criada",
        "qual a última tarefa criada",
        "qual é a última tarefa criada",
        "qual foi a ultima tarefa criada",
        "qual foi a última tarefa criada"
    )
    if normalizado in consultas_ultima_tarefa or corresponde_frase(normalizado, consultas_ultima_tarefa, limiar=0.88):
        return {"tipo": "tarefa", "acao": "ultima"}

    referencias_ultima = (
        "exclua a ultima tarefa criada", "exclua a ultima tarefa",
        "exclua a última tarefa criada", "exclua a última tarefa",
        "delete a ultima tarefa criada", "delete a ultima tarefa",
        "delete a última tarefa criada", "delete a última tarefa",
        "apague a ultima tarefa criada", "apague a ultima tarefa",
        "apague a última tarefa criada", "apague a última tarefa",
        "remova a ultima tarefa criada", "remova a ultima tarefa",
        "remova a última tarefa criada", "remova a última tarefa",
        "exclua ela", "apague ela", "remova ela", "delete ela"
    )
    if normalizado in referencias_ultima or corresponde_frase(normalizado, referencias_ultima, limiar=0.88):
        return {"tipo": "tarefa", "acao": "remover", "referencia": "ultima"}

    normalizado_correcao = re.sub(
        r"\s+da\s+(?:ultima|última)\s+tarefa(?:\s+criada)?$",
        "",
        normalizado_original,
        flags=re.IGNORECASE
    ).strip()
    padrao_correcao_titulo = re.match(
        r"^(?:arrume|corrija|corrigir|altere|altera|mude|mudar|troque|trocar|atualize|atualizar)"
        r"\s+o\s+nome(?:\s+de\s+(.+?))?\s+para\s+(.+)$",
        normalizado_correcao,
        flags=re.IGNORECASE
    )
    if padrao_correcao_titulo:
        antigo = padrao_correcao_titulo.group(1)
        novo = padrao_correcao_titulo.group(2).strip()
        return {
            "tipo": "tarefa",
            "acao": "corrigir_titulo",
            "referencia": "ultima",
            "antigo": antigo.strip() if antigo else None,
            "novo": novo
        }
    for referencia in referencias_tarefa:
        if normalizado == referencia or normalizado.startswith(referencia + " "):
            return {"tipo": "tarefa", "acao": "referencia", "referencia": "ultima"}

    gatilhos_criar = [
        "crie uma tarefa ", "criar uma tarefa ",
        "adicione uma tarefa ", "adicionar uma tarefa ",
        "anote uma tarefa ", "anotar uma tarefa ",
        "lembre-me de ", "lembre de ", "me lembre de ",
        "não esquecer de ", "nao esquecer de "
    ]

    for gatilho in gatilhos_criar:
        gatilho_limpo = gatilho.rstrip()
        corresponde = normalizado.startswith(gatilho)
        tamanho_prefixo = len(gatilho_limpo)

        if not corresponde and len(normalizado) >= tamanho_prefixo:
            prefixo_digitado = normalizado[:tamanho_prefixo]
            corresponde = SequenceMatcher(None, prefixo_digitado, gatilho_limpo).ratio() >= 0.84

        if corresponde:
            titulo_bruto = texto[tamanho_prefixo:].strip()
            if not titulo_bruto:
                return None

            titulo, data, hora = extrair_data_hora_tarefa(titulo_bruto)
            titulo = titulo.strip()
            if titulo.lower().startswith("para "):
                titulo = titulo[5:].strip()

            if not titulo:
                return None

            return {
                "tipo": "tarefa", "acao": "criar",
                "titulo": titulo, "data": data, "hora": hora
            }

    consultas_listar = [
        "minhas tarefas", "listar minhas tarefas", "liste minhas tarefas",
        "mostre minhas tarefas", "mostrar minhas tarefas",
        "quais são minhas tarefas", "quais sao minhas tarefas",
        "e as minhas tarefas", "e minhas tarefas", "e as tarefas",
        "quais tarefas eu tenho", "listar tarefas", "mostrar tarefas",
        "ver minhas tarefas", "o que tenho para fazer"
    ]

    consultas_listar_flexiveis = [
        "quais sao as minhas tarefas", "e as minhas tarefas", "e minhas tarefas",
        "e as tarefas", "quais sao minhas tarefas", "quais tarefas eu tenho",
        "minhas tarefas"
    ]

    if corresponde_frase(normalizado, consultas_listar + consultas_listar_flexiveis, limiar=0.88):
        return {"tipo": "tarefa", "acao": "listar", "data": None}

    gatilhos_concluir = [
        "conclua a tarefa ", "concluir a tarefa ", "terminei a tarefa ",
        "terminei ", "marque como concluída ", "marque como concluida ",
        "finalizei a tarefa "
    ]

    for gatilho in gatilhos_concluir:
        if normalizado.startswith(gatilho):
            termo = texto[len(gatilho):].strip()
            if not termo:
                return None
            return {"tipo": "tarefa", "acao": "concluir", "termo": termo}

    gatilhos_remover = [
        "remova a tarefa ", "remover a tarefa ", "remover tarefa ",
        "remova tarefa ", "apague a tarefa ", "apagar a tarefa ",
        "delete a tarefa ", "exclua a tarefa "
    ]

    for gatilho in gatilhos_remover:
        if normalizado.startswith(gatilho):
            termo = texto[len(gatilho):].strip()
            if not termo:
                return None
            return {"tipo": "tarefa", "acao": "remover", "termo": termo}

    return None
