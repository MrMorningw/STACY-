import json
import re
import unicodedata
from difflib import SequenceMatcher
import context
import entity_store
import memory
import intent
import command
import ai
import entity_resolver
import action
import conversation
import tasks
import knowledge
import cortex
import mepo
import orchestration
import anpes
import autonomy


ROTA_INTERNA = "interno"
ROTA_CONHECIMENTO = "conhecimento_core"
ROTA_IA_LOCAL = "ia_local"
ROTA_PESQUISA_EXTERNA = "pesquisa_externa"


def _normalizar_rota(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


class StacyOrchestrator:
    def __init__(self, api_key=None, memoria=None, entidades=None, phase_callback=None):
        self.api_key = api_key
        self.memoria = memoria
        self.entidades = entidades
        self.phase_callback = phase_callback

    def _phase(self, phase, execution_id=None):
        if callable(self.phase_callback):
            try:
                self.phase_callback(phase, execution_id)
            except TypeError:
                try:
                    self.phase_callback(phase)
                except Exception:
                    pass
            except Exception:
                pass

    def processar(self, texto, execution_id=None):
        self._phase("pensando", execution_id)
        normalized = _normalizar_rota(texto)
        try:
            resultado = ai.responder(texto, api_key=self.api_key)
        except TypeError:
            resultado = ai.responder(texto)
        except Exception as exc:
            return {"tipo": "erro", "resposta": f"Falha no processamento: {exc}"}
        if isinstance(resultado, dict):
            return resultado
        return {"tipo": "resposta", "resposta": str(resultado or "")}

    def chat(self, texto, execution_id=None):
        return self.processar(texto, execution_id=execution_id)
