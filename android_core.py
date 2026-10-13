"""Stable JSON entry point for the Android-to-Python CORE bridge.

The Android receiver expects exactly one JSON object on stdout. Any diagnostic
output from the orchestrator is redirected to stderr so it cannot corrupt the
wire protocol.
"""
import contextlib
import json
import os
import sys


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
        # Import and execute the CORE with stdout reserved for the JSON reply.
        with contextlib.redirect_stdout(sys.stderr):
            import entity_store
            import memory
            from orchestrator import StacyOrchestrator

            memoria = memory.carregar_memoria()
            entidades = entity_store.carregar_entidades()
            api_key = os.environ.get("GEMINI_API_KEY")
            orchestrator = StacyOrchestrator(
                api_key=api_key,
                memoria=memoria,
                entidades=entidades,
            )
            result = orchestrator.processar(message)

        if not isinstance(result, dict):
            result = {"tipo": "resposta", "resposta": str(result)}
        kind = result.get("tipo", "resposta")
        response = result.get("resposta", "")
        if not isinstance(kind, str):
            kind = "resposta"
        if not isinstance(response, str):
            response = str(response)
        _emit({"tipo": kind, "resposta": response})
    except Exception as error:
        _emit({
            "tipo": "erro",
            "resposta": f"Não consegui concluir o processamento, senhor: {error}",
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
