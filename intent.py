import unicodedata

def interpretar(mensagem):

    texto = mensagem.strip()
    normalizado = texto.lower()
    normalizado_sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", normalizado)
        if unicodedata.category(caractere) != "Mn"
    )
    # Tolerância a erro de digitação comum: "saos" -> "sao".
    normalizado_sem_acentos = normalizado_sem_acentos.replace("saos ", "sao ")

    if not texto:
        return None

    # =========================
    # COMANDOS DIRETOS
    # =========================

    if normalizado in ["sair", "exit", "quit"]:
        return {
            "tipo": "comando",
            "acao": "sair"
        }

    if normalizado == "memoria":
        return {
            "tipo": "memoria",
            "acao": "mostrar"
        }

    if normalizado.startswith("buscar "):
        return {
            "tipo": "memoria",
            "acao": "buscar",
            "conteudo": texto[7:].strip()
        }

    if normalizado.startswith("memorize "):
        return interpretar_memoria(
            "memorizar",
            texto[9:].strip()
        )

    if normalizado.startswith("esquecer "):
        return interpretar_memoria(
            "esquecer",
            texto[9:].strip()
        )

    # =========================
    # CONSULTA DE MEMÓRIA
    # =========================

    consultas_usuario = [
        "qual é o meu nome",
        "qual meu nome",
        "como eu me chamo",
        "você sabe meu nome"
    ]

    consultas_projetos = [
        "quais são meus projetos",
        "quais meus projetos",
        "quais projetos eu tenho",
        "você lembra meus projetos"
    ]

    consultas_objetivos = [
        "quais são meus objetivos",
        "quais meus objetivos",
        "quais objetivos eu tenho",
        "você lembra meus objetivos"
    ]

    consulta = normalizado.rstrip("?")
    consulta_flexivel = normalizado_sem_acentos.rstrip("?")

    if consulta in consultas_usuario or consulta_flexivel in [
        "qual e o meu nome",
        "qual meu nome",
        "como eu me chamo",
        "voce sabe meu nome"
    ]:
        return {
            "tipo": "memoria",
            "acao": "consultar",
            "categoria": "usuario"
        }

    if consulta in consultas_projetos or consulta_flexivel in [
        "quais sao meus projetos",
        "quais meus projetos",
        "quais projetos eu tenho",
        "voce lembra meus projetos",
        "quais sao os meus projetos",
        "quais sao as minhas projetos"
    ]:
        return {
            "tipo": "memoria",
            "acao": "consultar",
            "categoria": "projetos"
        }

    if consulta in consultas_objetivos or consulta_flexivel in [
        "quais sao meus objetivos",
        "quais meus objetivos",
        "quais objetivos eu tenho",
        "voce lembra meus objetivos",
        "quais sao os meus objetivos",
        "quais sao as minhas objetivos"
    ]:
        return {
            "tipo": "memoria",
            "acao": "consultar",
            "categoria": "objetivos"
        }

    # =========================
    # TAREFAS
    # =========================

    tarefa = interpretar_tarefa(mensagem)

    if tarefa is not None:
        return tarefa

    # =========================
    # LINGUAGEM NATURAL
    # =========================

    gatilhos_memorizar = [
        "guarde ",
        "guarda ",
        "guardar ",
        "lembre ",
        "lembra ",
        "registre ",
        "registra ",
        "anote ",
        "anota ",
        "memorize "
    ]

    gatilhos_esquecer = [
        "esqueça ",
        "esquece ",
        "apague ",
        "apaga ",
        "remova ",
        "remove "
    ]

    for gatilho in gatilhos_memorizar:

        if normalizado.startswith(gatilho):

            conteudo = texto[len(gatilho):].strip()

            return interpretar_memoria(
                "memorizar",
                conteudo
            )

    for gatilho in gatilhos_esquecer:

        if normalizado.startswith(gatilho):

            conteudo = texto[len(gatilho):].strip()

            return interpretar_memoria(
                "esquecer",
                conteudo
            )

    tarefa = interpretar_tarefa(mensagem)

    if tarefa is not None:
        return tarefa

    return None


def interpretar_memoria(acao, conteudo):

    categoria = None
    valor = conteudo

    # =========================
    # LINGUAGEM NATURAL SIMPLES
    # =========================

    natural = conteudo.strip()
    natural_lower = natural.lower()

    prefixos = [
        "o projeto ",
        "projeto ",
        "os projetos ",
        "projetos ",
        "o objetivo ",
        "objetivo ",
        "os objetivos ",
        "objetivos ",
        "a preferência ",
        "preferência ",
        "as preferências ",
        "preferências "
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
                    "tipo": "memoria",
                    "acao": acao,
                    "categoria": categoria,
                    "valor": resto
                }

    # =========================
    # FORMATO:
    # categoria = valor
    # =========================

    if "=" in conteudo:

        esquerda, valor = conteudo.split("=", 1)

        esquerda = esquerda.strip()
        valor = valor.strip()

        if "." in esquerda:

            categoria, chave = esquerda.split(".", 1)

            categoria = categoria.strip().lower()
            chave = chave.strip()

            return {
                "tipo": "memoria",
                "acao": acao,
                "categoria": categoria,
                "chave": chave,
                "valor": valor
            }

        categoria = esquerda.strip().lower()

        if categoria == "usuario":
            valor = f"nome={valor}"

        return {
            "tipo": "memoria",
            "acao": acao,
            "categoria": categoria,
            "valor": valor
        }

    # =========================
    # FORMATO:
    # categoria.valor
    # =========================

    if "." in conteudo:

        categoria, valor = conteudo.split(".", 1)

        categoria = categoria.strip().lower()
        valor = valor.strip()

        return {
            "tipo": "memoria",
            "acao": acao,
            "categoria": categoria,
            "valor": valor
        }

    # =========================
    # SEM CATEGORIA
    # =========================

    return {
        "tipo": "memoria",
        "acao": acao,
        "conteudo": conteudo
    }


def detectar_memoria_candidata(mensagem):

    texto = mensagem.strip()
    normalizado = texto.lower()

    gatilhos = {

        "objetivos": [
            "meu objetivo é ",
            "meus objetivos são ",
            "meu objetivo será ",
            "meus objetivos serão "
        ],

        "projetos": [
            "meu projeto é ",
            "meus projetos são "
        ],

        "preferencias": [
            "eu prefiro ",
            "minha preferência é ",
            "minhas preferências são "
        ]
    }

    for categoria, lista_gatilhos in gatilhos.items():

        for gatilho in lista_gatilhos:

            if normalizado.startswith(gatilho):

                valor = texto[len(gatilho):].strip()

                if not valor:
                    return None

                return {
                    "tipo": "memoria_candidata",
                    "categoria": categoria,
                    "valor": valor
                }

    return None

def detectar_consulta_memoria(mensagem):

    texto = mensagem.strip().lower()

    consultas = {
        "projetos": [
            "quais são meus projetos",
            "quais sao meus projetos",
            "quais são os meus projetos",
            "quais sao os meus projetos",
            "meus projetos"
        ],

        "objetivos": [
            "quais são meus objetivos",
            "quais sao meus objetivos",
            "quais são os meus objetivos",
            "quais sao os meus objetivos",
            "meus objetivos"
        ],

        "preferencias": [
            "quais são minhas preferências",
            "quais sao minhas preferencias",
            "quais são as minhas preferências",
            "quais sao as minhas preferencias",
            "minhas preferências",
            "minhas preferencias"
        ],

        "informacoes": [
            "quais são minhas informações",
            "quais sao minhas informacoes",
            "quais são as minhas informações",
            "quais sao as minhas informacoes",
            "minhas informações",
            "minhas informacoes"
        ]
    }

    for categoria, frases in consultas.items():

        for frase in frases:

            if texto == frase:
                return {
                    "tipo": "consulta_memoria",
                    "categoria": categoria
                }

    return None

def detectar_consulta_especifica_memoria(mensagem):

    texto = mensagem.strip()

    prefixos = [
        "qual é o meu projeto ",
        "qual e o meu projeto ",
        "qual é o meu objetivo ",
        "qual e o meu objetivo ",
        "qual é a minha preferência ",
        "qual e a minha preferencia ",
        "o que é o meu projeto ",
        "o que e o meu projeto ",
        "o que você sabe sobre meu projeto ",
        "o que voce sabe sobre meu projeto "
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

            return {
                "tipo": "consulta_especifica_memoria",
                "categoria": categoria,
                "termo": termo
            }

    return None

def detectar_referencia_memoria(mensagem):

    texto = mensagem.strip().lower()

    for caractere in "?!.,;:":
        texto = texto.replace(caractere, "")

    texto = " ".join(texto.split())

    referencias = [
        "qual é o id dele",
        "qual e o id dele",
        "qual é o id dela",
        "qual e o id dela",
        "qual é o id desse projeto",
        "qual e o id desse projeto",
        "qual é o id dessa memória",
        "qual e o id dessa memoria",
        "qual é o valor dele",
        "qual e o valor dele",
        "qual é o valor dessa memória",
        "qual e o valor dessa memoria"
    ]

    for referencia in referencias:

        if texto == referencia:

            return {
                "tipo": "referencia_memoria",
                "acao": "consultar"
            }

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

    # =========================
    # HORA
    # =========================

    padroes_hora = [
        r"\s+às\s+(\d{1,2})(?:[:h](\d{2}))?\s*$",
        r"\s+as\s+(\d{1,2})(?:[:h](\d{2}))?\s*$",
        r"\s+(\d{1,2})h(\d{2})?\s*$"
    ]

    for padrao in padroes_hora:
        resultado = re.search(
            padrao,
            restante,
            flags=re.IGNORECASE
        )

        if resultado:
            horas = int(resultado.group(1))
            minutos = (
                int(resultado.group(2))
                if resultado.group(2)
                else 0
            )

            if 0 <= horas <= 23 and 0 <= minutos <= 59:
                hora = f"{horas:02d}:{minutos:02d}"
                restante = restante[:resultado.start()].strip()
                break

    # =========================
    # DATA RELATIVA
    # =========================

    datas_relativas = {
        "hoje": agora.date(),
        "amanhã": agora.date() + timedelta(days=1),
        "amanha": agora.date() + timedelta(days=1),
        "depois de amanhã": agora.date() + timedelta(days=2),
        "depois de amanha": agora.date() + timedelta(days=2)
    }

    encontrada = None

    for expressao, data_calculada in sorted(
        datas_relativas.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        padrao = r"\b" + re.escape(expressao) + r"\b"

        if re.search(
            padrao,
            restante,
            flags=re.IGNORECASE
        ):
            encontrada = (
                expressao,
                data_calculada
            )
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

    # =========================
    # DATA ISO: 2026-09-01
    # =========================

    if data is None:
        resultado = re.search(
            r"\b(\d{4}-\d{2}-\d{2})\b",
            restante
        )

        if resultado:
            try:
                datetime.strptime(
                    resultado.group(1),
                    "%Y-%m-%d"
                )

                data = resultado.group(1)

                restante = (
                    restante[:resultado.start()]
                    + " "
                    + restante[resultado.end():]
                ).strip()

            except ValueError:
                pass

    # =========================
    # LIMPEZA
    # =========================

    restante = re.sub(
        r"\s+",
        " ",
        restante
    ).strip()

    restante = re.sub(
        r"\s+(?:às|as)\s*$",
        "",
        restante,
        flags=re.IGNORECASE
    ).strip()

    return restante, data, hora



def interpretar_tarefa(mensagem):

    texto = mensagem.strip()
    normalizado = texto.lower()

    # =========================
    #    texto = mensagem.strip()
    # =========================

    gatilhos_criar = [
        "crie uma tarefa ",
        "criar uma tarefa ",
        "adicione uma tarefa ",
        "adicionar uma tarefa ",
        "anote uma tarefa ",
        "anotar uma tarefa ",
        "lembre-me de ",
        "lembre de ",
        "me lembre de ",
        "não esquecer de ",
        "nao esquecer de "
    ]

    for gatilho in gatilhos_criar:

        if normalizado.startswith(gatilho):

            titulo_bruto = texto[len(gatilho):].strip()

            if not titulo_bruto:
                return None

            titulo, data, hora = extrair_data_hora_tarefa(
                titulo_bruto
            )

            if not titulo:
                return None

            return {
                "tipo": "tarefa",
                "acao": "criar",
                "titulo": titulo,
                "data": data,
                "hora": hora
            }

    # =========================
    # LISTAR TAREFAS
    # =========================

    consultas_listar = [
        "minhas tarefas",
        "listar minhas tarefas",
        "liste minhas tarefas",
        "mostre minhas tarefas",
        "mostrar minhas tarefas",
        "quais são minhas tarefas",
        "quais sao minhas tarefas",
        "quais tarefas eu tenho",
        "listar tarefas",
        "mostrar tarefas",
        "ver minhas tarefas",
        "o que tenho para fazer"
    ]

    normalizado_flexivel = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", normalizado)
        if unicodedata.category(caractere) != "Mn"
    ).replace("saos ", "sao ")

    consultas_listar_flexiveis = [
        "quais sao as minhas tarefas",
        "quais sao minhas tarefas",
        "quais tarefas eu tenho",
        "minhas tarefas"
    ]

    if normalizado in consultas_listar or normalizado_flexivel in consultas_listar_flexiveis:

        return {
            "tipo": "tarefa",
            "acao": "listar",
            "data": None
        }

    # =========================
    # CONCLUIR TAREFA
    # =========================

    gatilhos_concluir = [
        "conclua a tarefa ",
        "concluir a tarefa ",
        "terminei a tarefa ",
        "terminei ",
        "marque como concluída ",
        "marque como concluida ",
        "finalizei a tarefa "
    ]

    for gatilho in gatilhos_concluir:

        if normalizado.startswith(gatilho):

            termo = texto[len(gatilho):].strip()

            if not termo:
                return None

            return {
                "tipo": "tarefa",
                "acao": "concluir",
                "termo": termo
            }

    # =========================
    # REMOVER TAREFA
    # =========================

    gatilhos_remover = [
        "remova a tarefa ",
        "remover a tarefa ",
        "remover tarefa ",
        "remova tarefa ",
        "apague a tarefa ",
        "apagar a tarefa ",
        "delete a tarefa ",
        "exclua a tarefa "
    ]

    for gatilho in gatilhos_remover:

        if normalizado.startswith(gatilho):

            termo = texto[len(gatilho):].strip()

            if not termo:
                return None

            return {
                "tipo": "tarefa",
                "acao": "remover",
                "termo": termo
            }

