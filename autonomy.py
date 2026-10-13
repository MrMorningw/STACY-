"""Compatibilidade pública para o gate de autonomia do CORE.

A política é implementada pelo ANPES. Este módulo preserva os nomes históricos
usados por StacyOrchestrator e pelos testes, evitando uma migração disruptiva.
"""
import anpes

ORIGEM_CORE = anpes.ORIGEM_CORE
ORIGEM_IA = anpes.ORIGEM_IA

STATUS_AUTORIZADA = anpes.STATUS_AUTORIZADA
STATUS_CONFIRMAR = anpes.STATUS_CONFIRMAR
STATUS_INVALIDA = anpes.STATUS_INVALIDA


def avaliar_execucao(intencao):
    """Determina se uma intenção pode seguir para execução."""
    return anpes.avaliar_intencao(intencao)


def anpes_estado():
    """Expõe o diagnóstico do ANPES sem alterar o estado do CORE."""
    return anpes.estado()
