"""Stable JSON entry point for the Android-to-Python CORE bridge.

Android receives exactly one JSON object on stdout. Diagnostics and tracebacks
are sent to stderr. Session state is persisted because Termux launches a fresh
Python process for each Android message.
"""
import contextlib
import json
import os
import sys
import traceback


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    message = " ".join(str(arg) for arg in args).strip()
    if not message:
        _emit({"tipo": "erro", "resposta": "A mensagem recebida está vazia."})
        return 0

    try:
        # Keep stdout as a machine-readable protocol, even if modules print logs.
        with contextlib.redirect_stdout(sys.stderr):
            import entity_store
            import memory
            from orchestrator import StacyOrchestrator
            from android_session import (
                exclusive_session_lock,
                persist_session,
                restore_session,
            )

            with exclusive_session_lock():
                memoria = memory.carregar_memoria()
                entidades = entity_store.carregar_entidades()
                orchestrator = StacyOrchestrator(
                    api_key=os.environ.get("GEMINI_API_KEY"),
                    memoria=memoria,
                    entidades=entidades,
                )
                warning = restore_session(orchestrator)
                try:
                    result = orchestrator.processar(message)
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    # Never replay a possibly half-completed confirmation action.
                    orchestrator.acao_pendente = None
                    orchestrator.conversa.limpar_operacao()
                    orchestrator.conversa.registrar_erro("falha no processamento")
                    result = {
                        "tipo": "erro",
                        "resposta": (
                            "Não consegui concluir o processamento, senhor. "
                            "A operação foi interrompida com segurança."
                        ),
                    }

                persist_session(orchestrator)

        if not isinstance(result, dict):
            result = {"tipo": "resposta", "resposta": str(result)}
        kind = result.get("tipo", "resposta")
        response = result.get("resposta", "")
        if not isinstance(kind, str):
            kind = "resposta"
        if not isinstance(response, str) or not response.strip():
            response = "Não consegui produzir uma resposta válida, senhor."
            kind = "erro"
        if warning:
            response = f"{warning}\n\n{response}"
        _emit({"tipo": kind, "resposta": response})
    except Exception:
        traceback.print_exc(file=sys.stderr)
        _emit({
            "tipo": "erro",
            "resposta": (
                "O núcleo da STACY encontrou uma falha interna. "
                "Nenhuma nova ação foi confirmada; verifique o diagnóstico do CORE."
            ),
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
