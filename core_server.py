"""Persistent local STACY CORE daemon."""
from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core_phase_context import CorePhaseContext

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765


def _load_local_orchestrator():
    """Load the orchestrator shipped beside this daemon, never a shadow module."""
    module_path = ROOT / "orchestrator.py"
    if not module_path.is_file():
        raise FileNotFoundError(f"orchestrator.py ausente em {module_path}")
    spec = importlib.util.spec_from_file_location("stacy_local_orchestrator", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.StacyOrchestrator


class CoreRuntime:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.ready = False
        self.error = None
        self.orchestrator = None
        self.warning = None
        self._phase_context = CorePhaseContext()
        self._load()

    def _load(self) -> None:
        try:
            import entity_store
            import memory
            import stacy_ecc
            StacyOrchestrator = _load_local_orchestrator()
            from android_session import load_api_key, persist_session, restore_session
            self._persist_session = persist_session
            with contextlib.redirect_stdout(sys.stderr):
                memoria = memory.carregar_memoria()
                entidades = entity_store.carregar_entidades()
                self.orchestrator = StacyOrchestrator(api_key=load_api_key(), memoria=memoria, entidades=entidades, phase_callback=self._phase)
                self.warning = restore_session(self.orchestrator)
            self.ready = True
            self.error = None
        except Exception as exc:
            self.ready = False
            self.error = f"{type(exc).__name__}: {exc}"
            traceback.print_exc(file=sys.stderr)

    def _phase(self, state: str) -> None:
        if state not in {"pensando", "pesquisando", "executando"}:
            return
        try:
            import subprocess
            execution_id = self._phase_context.current_execution_id()
            if execution_id is None:
                return
            subprocess.run(
                ["/system/bin/am", "broadcast", "-n", "com.mrmorning.stacy/.StacyCorePhaseReceiver", "-a", "com.mrmorning.stacy.CORE_PHASE", "--ei", "execution_id", str(execution_id), "--es", "state", state],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    def chat(self, message: str, execution_id=None) -> dict:
        normalized = message.strip()
        if not normalized:
            return {"tipo": "erro", "resposta": "A mensagem recebida está vazia."}
        if not self.ready:
            return {"tipo": "erro", "resposta": "O CORE não está saudável: " + (self.error or "falha de inicialização")}

        # HTTP requests run on separate threads. Keep phase events correlated to
        # this request rather than storing its ID on the shared runtime object.
        self._phase_context.set_current_execution_id(execution_id)
        self._phase("pensando")

        with self.lock:
            try:
                import android_tools
                import stacy_ecc
                sec = stacy_ecc.inspect_untrusted_text(normalized)
                if not sec.allowed:
                    return {"tipo": "erro", "resposta": "Detectei conteúdo suspeito e interrompi por segurança, senhor.", "security": {"allowed": False, "reason": sec.reason, "risk": sec.risk}}
                agent = stacy_ecc.select_agent("ia_local")
                print(f"[stacy-ecc] agent={agent.name}", file=sys.stderr)
                self.orchestrator.acao_pendente = getattr(self.orchestrator, "acao_pendente", None)
                android_action = None
                if self.orchestrator.acao_pendente is None and self.orchestrator.conversa.intencao_pendente is None:
                    android_action = android_tools.detectar_acao_android(normalized)
                with contextlib.redirect_stdout(sys.stderr):
                    if android_action is not None:
                        decision = stacy_ecc.authorize_action({"tipo": "android", **android_action}, require_confirmation=True)
                        if not decision.allowed:
                            return {"tipo": "acao_android", "resposta": "A ação foi identificada, mas precisa de confirmação explícita antes de ser executada.", "acao_android": android_action, "security": {"allowed": False, "reason": decision.reason, "risk": decision.risk}}
                        self.orchestrator.conversa.registrar_mensagem(normalized)
                        result = self.orchestrator._registrar_resultado_conversa({"tipo": "acao_android", "resposta": "Solicitação de ação Android recebida.", "acao": {"tipo": "android", **android_action}, "rota": "interno"})
                        result["acao_android"] = android_action
                    elif normalized.casefold() in {"status dos componentes", "status da stacy", "saúde da stacy", "saude da stacy"}:
                        from component_registry import snapshot, render_status
                        result = {"tipo": "resposta", "resposta": render_status(), "registry": snapshot(), "rota": "interno"}
                    else:
                        result = self.orchestrator.processar(normalized)
                self._persist_session(self.orchestrator)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                try:
                    self.orchestrator.acao_pendente = None
                    self.orchestrator.conversa.limpar_operacao()
                    self.orchestrator.conversa.registrar_erro("falha no processamento")
                except Exception:
                    pass
                return {"tipo": "erro", "resposta": "Não consegui concluir o processamento, senhor. A operação foi interrompida com segurança."}
            finally:
                self._phase_context.clear_current_execution_id()

        if not isinstance(result, dict):
            result = {"tipo": "resposta", "resposta": str(result)}

        try:
            verification = stacy_ecc.verify_result(result)
        except Exception:
            verification = None
            traceback.print_exc(file=sys.stderr)

        kind = result.get("tipo", "resposta")
        response = result.get("resposta", "")
        if not isinstance(kind, str) or not kind:
            kind = "resposta"
        if not isinstance(response, str) or not response.strip():
            response, kind = "Não consegui produzir uma resposta válida, senhor.", "erro"

        payload = {"tipo": kind, "resposta": response}
        if verification is not None:
            payload["verification"] = verification.to_dict()
        if self.warning:
            payload["warning"] = self.warning
        for key in ("acao_android", "fontes", "registry", "security"):
            if isinstance(result.get(key), (dict, list)):
                payload[key] = result[key]

        try:
            if payload.get("tipo") not in {"erro", "error"}:
                stacy_ecc.LearningStore().record(trigger=normalized[:200], behavior=str(payload.get("resposta", ""))[:300], scope="conversation", evidence="core_response", success=True)
        except Exception:
            pass

        return payload

    def health(self) -> dict:
        return {"ok": self.ready, "service": "stacy-core", "host": HOST, "port": PORT, "error": self.error, "eccAdaptation": "1.0.1"}


RUNTIME = CoreRuntime()


class Handler(BaseHTTPRequestHandler):
    server_version = "STACY-Core/0.3.1"

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200 if RUNTIME.ready else 503, RUNTIME.health())
            return
        if self.path == "/registry":
            from component_registry import snapshot
            self._json(200, snapshot())
            return
        self._json(404, {"error": "endpoint_not_found"})

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._json(404, {"tipo": "erro", "resposta": "endpoint_not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 64 * 1024:
                self._json(400, {"tipo": "erro", "resposta": "Requisição inválida."})
                return
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            message = body.get("message")
            execution_id = body.get("executionId")
            if not isinstance(message, str):
                raise ValueError("message deve ser texto")
            self._json(200, RUNTIME.chat(message, execution_id))
        except Exception as exc:
            self._json(400, {"tipo": "erro", "resposta": f"Requisição inválida: {exc}"})

    def log_message(self, fmt, *args):
        print(f"[stacy-core] {fmt % args}", file=sys.stderr)


if __name__ == "__main__":
    os.chdir(ROOT)
    print(f"STACY CORE daemon listening on http://{HOST}:{PORT}", file=sys.stderr)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
