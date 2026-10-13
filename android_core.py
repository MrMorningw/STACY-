"""Stable JSON entry point for the Android-to-Python CORE bridge.

Android receives exactly one JSON object on stdout. Diagnostics and tracebacks
are sent to stderr. Session state is persisted because Termux launches a fresh
Python process for each Android message.
"""
import contextlib
import json
import os
import subprocess
import sys
import traceback


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _report_android_phase(execution_id, state):
    if execution_id is None or state not in {"pesquisando", "executando", "pensando"}:
        return
    try:
        subprocess.run(
            [
                "/system/bin/am", "broadcast",
                "-n", "com.mrmorning.stacy/.StacyCorePhaseReceiver",
                "-a", "com.mrmorning.stacy.CORE_PHASE",
                "--ei", "execution_id", str(execution_id),
                "--es", "state", state,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # Phase telemetry is best-effort; the actual JSON result remains authoritative.
        pass


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    execution_id = None
    if args and args[0].startswith("--execution-id="):
        try:
            execution_id = int(args.pop(0).split("=", 1)[1])
        except ValueError:
            execution_id = None
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
            from android_tools import detectar_acao_android
            from android_session import (
                exclusive_session_lock,
                load_api_key,
                persist_session,
                restore_session,
            )

            with exclusive_session_lock():
                memoria = memory.carregar_memoria()
                entidades = entity_store.carregar_entidades()
                orchestrator = StacyOrchestrator(
                    api_key=load_api_key(),
                    memoria=memoria,
                    entidades=entidades,
                    phase_callback=lambda state: _report_android_phase(execution_id, state),
                )
                warning = restore_session(orchestrator)
                try:
                    android_action = None
                    if (
                        orchestrator.acao_pendente is None
                        and orchestrator.conversa.intencao_pendente is None
                    ):
                        android_action = detectar_acao_android(message)

                    if android_action is not None:
                        orchestrator.conversa.registrar_mensagem(message)
                        result = orchestrator._registrar_resultado_conversa({
                            "tipo": "acao_android",
                            "resposta": "Solicitação de ação Android recebida.",
                            "acao": {"tipo": "android", **android_action},
                            "rota": "interno",
                        })
                        result["acao_android"] = android_action
                    else:
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
        payload = {"tipo": kind, "resposta": response}
        if isinstance(result, dict) and isinstance(result.get("acao_android"), dict):
            payload["acao_android"] = result["acao_android"]
        if isinstance(result, dict) and isinstance(result.get("fontes"), list):
            fontes_seguras = []
            for fonte in result["fontes"][:5]:
                if not isinstance(fonte, dict):
                    continue
                url = fonte.get("url")
                titulo = fonte.get("titulo", "Fonte")
                if isinstance(url, str) and url.startswith("https://"):
                    fontes_seguras.append({
                        "titulo": str(titulo)[:180],
                        "url": url[:2048],
                    })
            payload["fontes"] = fontes_seguras
        _emit(payload)
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
