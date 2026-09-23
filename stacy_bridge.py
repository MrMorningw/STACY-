"""Bridge HTTP local entre o app Android e o STACY CORE.

Escuta somente em 127.0.0.1 para que o app Android possa conversar
com o núcleo Python já existente no Termux sem expor a STACY à rede.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

import entity_store
import memory
from orchestrator import StacyOrchestrator


HOST = "127.0.0.1"
PORT = int(os.environ.get("STACY_BRIDGE_PORT", "8765"))

_ORCHESTRATOR_LOCK = Lock()


def criar_orquestrador() -> StacyOrchestrator:
    api_key = os.environ.get("GEMINI_API_KEY")
    memoria = memory.carregar_memoria()
    entidades = entity_store.carregar_entidades()
    return StacyOrchestrator(
        api_key=api_key,
        memoria=memoria,
        entidades=entidades,
    )


ORQUESTRADOR = criar_orquestrador()


class Handler(BaseHTTPRequestHandler):
    server_version = "STACY-Bridge/1.1"

    def _responder(self, status: int, dados: dict) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._responder(
                200,
                {
                    "ok": True,
                    "status": "online",
                    "service": "stacy-core",
                    "bridge": "local",
                },
            )
            return

        self._responder(404, {"ok": False, "erro": "rota não encontrada"})

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._responder(404, {"ok": False, "erro": "rota não encontrada"})
            return

        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho <= 0 or tamanho > 256_000:
                raise ValueError("corpo inválido")

            corpo = self.rfile.read(tamanho)
            dados = json.loads(corpo.decode("utf-8"))
            mensagem = str(dados.get("mensagem", "")).strip()

            if not mensagem:
                self._responder(400, {"ok": False, "erro": "mensagem vazia"})
                return

            # O CORE mantém estado conversacional em memória. A serialização
            # evita corrupção desse estado quando o Android envia requisições
            # concorrentes.
            with _ORCHESTRATOR_LOCK:
                resultado = ORQUESTRADOR.processar(mensagem)

            if not isinstance(resultado, dict):
                resultado = {
                    "tipo": "resposta",
                    "resposta": str(resultado),
                }

            self._responder(200, {"ok": True, "resultado": resultado})

        except json.JSONDecodeError:
            self._responder(400, {"ok": False, "erro": "JSON inválido"})
        except Exception as erro:
            self._responder(500, {"ok": False, "erro": str(erro)})

    def log_message(self, format: str, *args) -> None:
        print("[STACY-BRIDGE]", format % args)


def main() -> None:
    servidor = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"STACY Bridge online em http://{HOST}:{PORT}")
    print("GET /health | POST /chat")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSTACY Bridge encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
