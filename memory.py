import unicodedata
import json
import uuid

ARQUIVO_MEMORIA = "memory.json"

def gerar_id_memoria():
    return str(uuid.uuid4())

def carregar_memoria():
    try:
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "usuario": {},
            "preferencias": [],
            "projetos": [],
            "objetivos": [],
            "informacoes": []
        }


def salvar_memoria(memoria):
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as arquivo:
        json.dump(
            memoria,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

def registrar_memoria(categoria, texto, memoria):

    categorias_lista = [
        "preferencias",
        "projetos",
        "objetivos",
        "informacoes"
    ]

    if categoria == "usuario":

        if "=" not in texto:
            return False

        chave, valor = texto.split("=", 1)

        chave = chave.strip()
        valor = valor.strip()

        if not chave or not valor:
            return False

        if memoria_existe(categoria, chave, memoria):
            return False

        memoria["usuario"][chave] = valor

    elif categoria in categorias_lista:

        if memoria_existe(categoria, texto, memoria):
            return False

        memoria[categoria].append({
            "id": gerar_id_memoria(),
            "valor": texto
        })

    else:

        return False

    salvar_memoria(memoria)

    return True

def mostrar_memoria(memoria):

    apresentacao = {
        "usuario": memoria.get("usuario", {}),
        "preferencias": [],
        "projetos": [],
        "objetivos": [],
        "informacoes": []
    }

    for categoria in [
        "preferencias",
        "projetos",
        "objetivos",
        "informacoes"
    ]:
        dados = memoria.get(categoria, [])

        for item in dados:

            valor = obter_valor_memoria(item)

            if valor:
                apresentacao[categoria].append(valor)

    linhas = ["Estas são as informações que tenho guardadas, senhor:"]
    total = 0

    usuario = apresentacao["usuario"]
    if usuario:
        linhas.append("• Usuário:")
        for chave, valor in usuario.items():
            linhas.append(f"  - {chave}: {valor}")
            total += 1

    nomes = {
        "preferencias": "Preferências",
        "projetos": "Projetos",
        "objetivos": "Objetivos",
        "informacoes": "Informações"
    }

    for categoria, titulo in nomes.items():
        valores = apresentacao[categoria]
        if valores:
            linhas.append(f"• {titulo}:")
            for valor in valores:
                linhas.append(f"  - {valor}")
                total += 1

    if total == 0:
        return "Não há informações persistentes guardadas no momento, senhor."

    return "\n".join(linhas)

def buscar_memoria(categoria, memoria):

    categorias_validas = [
        "usuario",
        "preferencias",
        "projetos",
        "objetivos",
        "informacoes"
    ]

    if categoria not in categorias_validas:
        return None

    dados = memoria.get(categoria)

    if not dados:
        return {}

    if categoria == "usuario":
        return dados

    resultado = []

    for item in dados:

        valor = obter_valor_memoria(item)

        if valor:
            resultado.append(valor)

    return resultado

def _normalizar_texto(texto):
    texto = str(texto).strip().lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )


def esquecer_memoria(categoria, texto, memoria):
    if categoria == "usuario":
        if texto in memoria.get("usuario", {}):
            del memoria["usuario"][texto]
            salvar_memoria(memoria)
            return True
        return False

    if categoria in memoria:
        texto_normalizado = _normalizar_texto(texto)

        encontrados = [
            item
            for item in memoria[categoria]
            if texto_normalizado in _normalizar_texto(
                obter_valor_memoria(item)
            )
        ]

        if encontrados:
            for item in encontrados:
                memoria[categoria].remove(item)

            salvar_memoria(memoria)
            return True

    return False

def memoria_existe(categoria, texto, memoria):

    if categoria == "usuario":

        return texto in memoria.get("usuario", {})

    if categoria in memoria:

        for item in memoria[categoria]:

            if isinstance(item, str):

                if texto.lower() == item.lower():
                    return True

            elif isinstance(item, dict):

                valor = item.get("valor", "")

                if texto.lower() == valor.lower():
                    return True

        return False

    return False

def buscar_por_id(memoria, identificador):

    for categoria, dados in memoria.items():

        if categoria == "usuario":
            continue

        if not isinstance(dados, list):
            continue

        for item in dados:

            if isinstance(item, dict):

                if item.get("id") == identificador:

                    return {
                        "categoria": categoria,
                        "memoria": item
                    }

    return None

def buscar_por_texto(memoria, texto):
    texto_normalizado = _normalizar_texto(texto)

    if not texto_normalizado:
        return []

    resultados = []

    for categoria, dados in memoria.items():
        if categoria == "usuario":
            continue

        if not isinstance(dados, list):
            continue

        for item in dados:
            valor = obter_valor_memoria(item)

            if texto_normalizado in _normalizar_texto(valor):
                resultados.append({
                    "categoria": categoria,
                    "memoria": item
                })

    return resultados

def esquecer_por_id(memoria, identificador):

    for categoria, dados in memoria.items():

        if categoria == "usuario":
            continue

        if not isinstance(dados, list):
            continue

        for item in dados:

            if isinstance(item, dict):

                if item.get("id") == identificador:

                    dados.remove(item)

                    salvar_memoria(memoria)

                    return True

    return False

def migrar_memorias_antigas(memoria):

    categorias = [
        "preferencias",
        "projetos",
        "objetivos",
        "informacoes"
    ]

    quantidade = 0

    for categoria in categorias:

        dados = memoria.get(categoria, [])

        if not isinstance(dados, list):
            continue

        novas_memorias = []

        for item in dados:

            if isinstance(item, str):

                novas_memorias.append({
                    "id": gerar_id_memoria(),
                    "valor": item
                })

                quantidade += 1

            elif isinstance(item, dict):

                novas_memorias.append(item)

        memoria[categoria] = novas_memorias

    return quantidade

def obter_valor_memoria(item):

    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return item.get("valor", "")

    return ""

def resolver_memoria(memoria, texto):

    resultados = buscar_por_texto(
        memoria,
        texto
    )

    if not resultados:
        return {
            "status": "nao_encontrada",
            "resultados": []
        }

    if len(resultados) == 1:
        return {
            "status": "encontrada",
            "resultados": resultados
        }

    return {
        "status": "ambigua",
        "resultados": resultados
    }

def descrever_memoria(resultado):

    if not resultado:
        return None

    categoria = resultado.get("categoria")
    memoria = resultado.get("memoria")

    if not categoria or not memoria:
        return None

    valor = obter_valor_memoria(memoria)
    identificador = memoria.get("id")

    return {
        "categoria": categoria,
        "valor": valor,
        "id": identificador
    }

def atualizar_memoria_por_id(memoria, identificador, novo_valor):

    novo_valor = novo_valor.strip()

    if not novo_valor:
        return False

    resultado = buscar_por_id(
        memoria,
        identificador
    )

    if resultado is None:
        return False

    memoria_item = resultado["memoria"]

    if not isinstance(memoria_item, dict):
        return False

    memoria_item["valor"] = novo_valor

    salvar_memoria(memoria)

    return True

def excluir_memoria_por_id(memoria, identificador):

    resultado = buscar_por_id(
        memoria,
        identificador
    )

    if resultado is None:
        return False

    categoria = resultado["categoria"]
    memoria_item = resultado["memoria"]

    if not isinstance(memoria_item, dict):
        return False

    memoria[categoria].remove(memoria_item)

    salvar_memoria(memoria)

    return True

def memoria_existe_por_id(memoria, identificador):

    return buscar_por_id(
        memoria,
        identificador
    ) is not None

def obter_memoria_por_id(memoria, identificador):

    resultado = buscar_por_id(
        memoria,
        identificador
    )

    if resultado is None:
        return None

    return resultado["memoria"]

def estatisticas_memoria(memoria):

    categorias = [
        "preferencias",
        "projetos",
        "objetivos",
        "informacoes"
    ]

    estatisticas = {}

    total = 0

    for categoria in categorias:

        dados = memoria.get(categoria, [])

        quantidade = len(dados)

        estatisticas[categoria] = quantidade

        total += quantidade

    estatisticas["total"] = total

    return estatisticas
