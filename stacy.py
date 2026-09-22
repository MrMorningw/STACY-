import argparse
import os

import config
import memory
import entity_store
from orchestrator import StacyOrchestrator


def criar_orquestrador():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("AVISO: GEMINI_API_KEY não configurada.")
        print("STACY continuará com o núcleo local ativo.")

    return StacyOrchestrator(
        api_key=api_key,
        memoria=memory.carregar_memoria(),
        entidades=entity_store.carregar_entidades()
    )


def executar_terminal(orquestrador, usar_voz=False):
    print("""
╔══════════════════════════════════════╗
              MODELO 4.0
          STATUS: ONLINE
╚══════════════════════════════════════╝
""")

    from datetime import datetime
    hora = datetime.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
    print(f"{config.NOME_ASSISTENTE}: {saudacao}, senhor. Estou pronta.")
    print("Digite 'sair' para encerrar.\n")

    import voice
    while True:
        try:
            mensagem = voice.ouvir() if usar_voz else input("Você: ")
            if usar_voz:
                print(f"Você: {mensagem}")
        except (KeyboardInterrupt, EOFError):
            print("\nSTACY: Encerrando sessão. Até logo, senhor.")
            break
        except Exception as erro:
            print(f"\nSTACY: Entrada de voz indisponível: {erro}\n")
            if usar_voz:
                print("STACY: Continuando em modo texto.")
                usar_voz = False
            continue

        try:
            resultado = orquestrador.processar(mensagem)
        except Exception as erro:
            print(f"\nSTACY: Ocorreu um erro durante o processamento: {erro}\n")
            continue

        if not isinstance(resultado, dict):
            continue
        if resultado.get("tipo") == "sair":
            print("\nSTACY: Encerrando sessão. Até logo, senhor.")
            break

        resposta = resultado.get("resposta")
        if resposta:
            print(f"\nSTACY: {resposta}")
            if usar_voz:
                voice.falar(resposta)
            fontes = resultado.get("fontes", [])
            if fontes:
                print("\nFontes:")
                for indice, fonte in enumerate(fontes[:5], start=1):
                    print(f"{indice}. {fonte.get('titulo', 'Fonte')}: {fonte.get('url', '')}")
            print()


def main():
    parser = argparse.ArgumentParser(description="STACY")
    parser.add_argument("--web", action="store_true", help="inicia a interface web local")
    parser.add_argument("--voice", action="store_true", help="usa voz pelo Termux")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    orquestrador = criar_orquestrador()

    if args.web:
        import interface
        print(f"STACY: interface local em http://{args.host}:{args.port}")
        interface.iniciar(orquestrador, args.host, args.port)
        return

    executar_terminal(orquestrador, usar_voz=args.voice)


if __name__ == "__main__":
    main()
