import os
import sys
from datetime import datetime

import config
import memory
import entity_store
import interface
from orchestrator import StacyOrchestrator


def main():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("AVISO: GEMINI_API_KEY não configurada.")
        print("STACY continuará com o núcleo local ativo.")

    memoria = memory.carregar_memoria()
    entidades = entity_store.carregar_entidades()

    orquestrador = StacyOrchestrator(
        api_key=api_key,
        memoria=memoria,
        entidades=entidades
    )

    ui = interface.AndroidInterface()
    modo = "voz" if "--voz" in sys.argv else interface.modo_interface_padrao()

    print("""
╔══════════════════════════════════════╗
              MODELO 4.0
          STATUS: ONLINE
╚══════════════════════════════════════╝
""")

    hora = datetime.now().hour
    if 5 <= hora < 12:
        saudacao = "Bom dia"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    saudacao_completa = f"{saudacao}, senhor. Estou pronta."
    print(f"{config.NOME_ASSISTENTE}: {saudacao_completa}")

    if modo == "voz":
        status = ui.status()
        if not status.voz_entrada:
            print(
                "AVISO: entrada por voz indisponível. "
                "Continuando em modo texto."
            )
            modo = "texto"
        elif status.voz_saida:
            ui.falar(saudacao_completa)

    print("Modo:", modo)
    print("Digite 'sair' para encerrar.\n")

    while True:
        try:
            if modo == "voz":
                mensagem = ui.ouvir()
                print(f"Você (voz): {mensagem}")
            else:
                mensagem = input("Você: ")

        except RuntimeError as erro:
            print(f"\nSTACY: {erro}")
            print("STACY: Voltando para o modo texto.\n")
            modo = "texto"
            continue

        except (KeyboardInterrupt, EOFError):
            print("\n\nSTACY: Encerrando sessão. Até logo, senhor.")
            if ui.status().voz_saida:
                ui.falar("Encerrando sessão. Até logo, senhor.")
            break

        try:
            resultado = orquestrador.processar(mensagem)
        except Exception as erro:
            print(
                "\nSTACY: Ocorreu um erro durante "
                f"o processamento: {erro}\n"
            )
            continue

        if not isinstance(resultado, dict):
            continue

        if resultado.get("tipo") == "sair":
            despedida = "Encerrando sessão. Até logo, senhor."
            print(f"\nSTACY: {despedida}")
            if modo == "voz":
                ui.falar(despedida)
            break

        resposta = resultado.get("resposta")
        if resposta:
            print(f"\nSTACY: {resposta}")

            if modo == "voz":
                ui.falar(resposta)

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
