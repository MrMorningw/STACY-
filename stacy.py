import os

import config
import memory
import entity_store
from orchestrator import StacyOrchestrator


def main():

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print(
            "AVISO: GEMINI_API_KEY não configurada."
        )
        print(
            "STACY continuará com o núcleo local ativo."
        )

    memoria = memory.carregar_memoria()
    entidades = entity_store.carregar_entidades()

    orquestrador = StacyOrchestrator(
        api_key=api_key,
        memoria=memoria,
        entidades=entidades
    )

    print("""
╔══════════════════════════════════════╗
              MODELO 4.0
          STATUS: ONLINE
╚══════════════════════════════════════╝
""")

    from datetime import datetime

    hora = datetime.now().hour

    if 5 <= hora < 12:
        saudacao = "Bom dia"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    print(
        f"{config.NOME_ASSISTENTE}: "
        f"{saudacao}, senhor. Estou pronta."
    )

    print(
        "Digite 'sair' para encerrar.\n"
    )

    while True:

        try:
            mensagem = input("Você: ")

        except (KeyboardInterrupt, EOFError):

            print(
                "\n\nSTACY: Encerrando sessão. "
                "Até logo, senhor."
            )

            break

        try:

            resultado = orquestrador.processar(
                mensagem
            )

        except Exception as erro:

            print(
                "\nSTACY: Ocorreu um erro durante "
                f"o processamento: {erro}\n"
            )

            continue

        if not isinstance(resultado, dict):
            continue

        if resultado.get("tipo") == "sair":

            print(
                "\nSTACY: Encerrando sessão. "
                "Até logo, senhor."
            )

            break

        resposta = resultado.get(
            "resposta"
        )

        if resposta:

            print(
                f"\nSTACY: {resposta}"
            )

            fontes = resultado.get("fontes", [])

            if fontes:
                print("\nFontes:")
                for indice, fonte in enumerate(fontes[:5], start=1):
                    print(
                        f"{indice}. {fonte.get('titulo', 'Fonte')}: "
                        f"{fonte.get('url', '')}"
                    )

            print()


if __name__ == "__main__":
    main()
