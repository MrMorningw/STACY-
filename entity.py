import string
import uuid


PREFIXOS_CATEGORIA = {
    "projetos": "P",
    "objetivos": "O",
    "preferencias": "F",
    "informacoes": "I"
}


CATEGORIAS_VALIDAS = list(PREFIXOS_CATEGORIA.keys())


def gerar_uuid():
    return str(uuid.uuid4())


def obter_prefixo(categoria):
    return PREFIXOS_CATEGORIA.get(categoria)


def gerar_id_stacy(categoria, indice):
    prefixo = obter_prefixo(categoria)

    if prefixo is None:
        return None

    if not isinstance(indice, int) or indice < 1:
        return None

    bloco = (indice - 1) // 9
    numero = ((indice - 1) % 9) + 1

    if bloco >= len(string.ascii_uppercase):
        return None

    letra = string.ascii_uppercase[bloco]

    return f"{prefixo}-{letra}{numero}"


def criar_entidade(categoria, nome, indice):
    id_stacy = gerar_id_stacy(categoria, indice)

    if id_stacy is None:
        return None

    return {
        "id": id_stacy,
        "uuid": gerar_uuid(),
        "categoria": categoria,
        "nome": nome,
        "atributos": {},
        "relacoes": [],
        "historico": []
    }


def obter_entidade_por_id(entidades, identificador):
    if not isinstance(entidades, list):
        return None

    for entidade in entidades:
        if not isinstance(entidade, dict):
            continue

        if entidade.get("id") == identificador:
            return entidade

    return None


def obter_entidade_por_uuid(entidades, identificador):
    if not isinstance(entidades, list):
        return None

    for entidade in entidades:
        if not isinstance(entidade, dict):
            continue

        if entidade.get("uuid") == identificador:
            return entidade

    return None


def obter_proximo_indice(entidades, categoria):
    prefixo = obter_prefixo(categoria)

    if prefixo is None:
        return None

    maior_indice = 0

    if not isinstance(entidades, list):
        return 1

    for entidade in entidades:
        if not isinstance(entidade, dict):
            continue

        identificador = entidade.get("id", "")

        if not identificador.startswith(f"{prefixo}-"):
            continue

        parte = identificador[2:]

        if len(parte) < 2:
            continue

        letra = parte[0]
        numero = parte[1:]

        if letra not in string.ascii_uppercase:
            continue

        if not numero.isdigit():
            continue

        indice = (
            string.ascii_uppercase.index(letra) * 9
            + int(numero)
        )

        if indice > maior_indice:
            maior_indice = indice

    return maior_indice + 1


def criar_proxima_entidade(entidades, categoria, nome):
    indice = obter_proximo_indice(entidades, categoria)

    if indice is None:
        return None

    return criar_entidade(
        categoria,
        nome,
        indice
    )


def atualizar_entidade(entidade, campo, valor):
    if not isinstance(entidade, dict):
        return False

    if not campo:
        return False

    if campo in [
        "id",
        "uuid",
        "categoria"
    ]:
        return False

    if campo == "nome":
        entidade["nome"] = valor
        return True

    if "atributos" not in entidade:
        entidade["atributos"] = {}

    entidade["atributos"][campo] = valor

    return True

def excluir_entidade(entidades, identificador):
    if not isinstance(entidades, list):
        return False

    for indice, entidade in enumerate(entidades):
        if not isinstance(entidade, dict):
            continue

        if entidade.get("id") == identificador:
            entidades.pop(indice)
            return True

    return False

def obter_entidade_por_nome(entidades, nome):
    if not isinstance(entidades, list):
        return None

    nome_normalizado = nome.strip().lower()

    for entidade in entidades:

        if not isinstance(entidade, dict):
            continue

        nome_entidade = entidade.get("nome", "")

        if not isinstance(nome_entidade, str):
            continue

        if nome_entidade.strip().lower() == nome_normalizado:
            return entidade

    return None


def buscar_entidades_por_texto(entidades, texto):
    resultados = []

    if not isinstance(entidades, list):
        return resultados

    texto_normalizado = texto.strip().lower()

    if not texto_normalizado:
        return resultados

    for entidade in entidades:

        if not isinstance(entidade, dict):
            continue

        nome = entidade.get("nome", "")

        if isinstance(nome, str):
            if texto_normalizado in nome.lower():
                resultados.append(entidade)
                continue

        atributos = entidade.get("atributos", {})

        if isinstance(atributos, dict):

            for valor in atributos.values():

                if isinstance(valor, str):
                    if texto_normalizado in valor.lower():
                        resultados.append(entidade)
                        break

    return resultados
