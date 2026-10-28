"""Text-only terminal adapter for the standalone Python core.

Android voice, speech output, notifications and device actions are provided by the
native Android application. This module intentionally has no Android bridge,
background daemon, shell-command adapter or mobile-runtime dependency.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterfaceStatus:
    voz_entrada: bool = False
    voz_saida: bool = False
    notificacoes: bool = False

    @property
    def alguma_capacidade_android(self) -> bool:
        return False


class ConsoleInterface:
    """Minimal console interface; the caller owns input and output."""

    def status(self) -> InterfaceStatus:
        return InterfaceStatus()

    def ouvir(self) -> str:
        raise RuntimeError(
            "A interface Python trabalha em modo texto. Para voz, use a versão Android nativa."
        )

    def falar(self, texto: str) -> bool:
        return False

    def notificar(self, titulo: str, conteudo: str) -> bool:
        return False


def modo_interface_padrao() -> str:
    """The standalone Python entry point remains text-only."""
    return "texto"
