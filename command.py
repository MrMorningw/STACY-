def identificar_comando(mensagem):

    comando = mensagem.strip().lower().rstrip("?!.,;: ")

    if comando in ["sair", "exit", "quit"]:
        return "sair"

    if comando == "memoria":
        return "memoria"

    if comando.startswith("buscar "):
        return "buscar"

    if comando.startswith("memorize "):
        return "memorize"

    if comando.startswith("esquecer "):
        return "esquecer"

    return None
