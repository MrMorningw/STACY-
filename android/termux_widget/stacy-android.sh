#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/stacy"
INPUT="${1:-}" python - <<'PY'
import json
import os
import entity_store
import memory
from orchestrator import StacyOrchestrator

mensagem = os.environ.get("INPUT", "").strip()
if not mensagem:
    print(json.dumps({"tipo": "vazio", "resposta": ""}, ensure_ascii=False))
    raise SystemExit(0)

api_key = os.environ.get("GEMINI_API_KEY")
memoria = memory.carregar_memoria()
entidades = entity_store.carregar_entidades()
orquestrador = StacyOrchestrator(api_key=api_key, memoria=memoria, entidades=entidades)
try:
    resultado = orquestrador.processar(mensagem)
except Exception as erro:
    resultado = {"tipo": "erro", "resposta": f"Não consegui concluir o processamento, senhor: {erro}"}
if not isinstance(resultado, dict):
    resultado = {"tipo": "resposta", "resposta": str(resultado)}
print(json.dumps({"tipo": resultado.get("tipo", "resposta"), "resposta": resultado.get("resposta", "")}, ensure_ascii=False))
PY
