"""Camada de interface da STACY.

O CORE não depende desta camada. Em Android/Termux, quando o Termux:API
estiver instalado, ela oferece entrada/saída por voz e notificações.
Sem Termux:API, a interface retorna indisponibilidade controlada e o
modo texto continua funcionando.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


@dataclass(frozen=True)
class InterfaceStatus:
    voz_entrada: bool
    voz_saida: bool
    notificacoes: bool

    @property
    def alguma_capacidade_android(self) -> bool:
        return self.voz_entrada or self.voz_saida or self.notificacoes


class AndroidInterface:
    """Adaptador opcional para Termux:API.

    Nenhum método executa ação da STACY CORE; apenas captura/apresenta texto.
    """

    def __init__(
        self,
        runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    ):
        self._runner = runner or subprocess.run

    @staticmethod
    def _comando_disponivel(nome: str) -> bool:
        return shutil.which(nome) is not None

    def status(self) -> InterfaceStatus:
        return InterfaceStatus(
            voz_entrada=self._comando_disponivel("termux-speech-to-text"),
            voz_saida=self._comando_disponivel("termux-tts-speak"),
            notificacoes=self._comando_disponivel("termux-notification"),
        )

    def ouvir(self) -> str:
        if not self._comando_disponivel("termux-speech-to-text"):
            raise RuntimeError(
                "Entrada por voz indisponível. Instale o Termux:API "
                "e o aplicativo Termux:API no Android."
            )

        resultado = self._runner(
            ["termux-speech-to-text"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if resultado.returncode != 0:
            detalhe = (resultado.stderr or "").strip()
            raise RuntimeError(
                "Falha na entrada por voz."
                + (f" {detalhe}" if detalhe else "")
            )

        texto = (resultado.stdout or "").strip()
        if not texto:
            raise RuntimeError("A entrada por voz não retornou texto.")
        return texto

    def falar(self, texto: str) -> bool:
        texto = (texto or "").strip()
        if not texto:
            return False
        if not self._comando_disponivel("termux-tts-speak"):
            return False

        resultado = self._runner(
            ["termux-tts-speak", texto],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return resultado.returncode == 0

    def notificar(self, titulo: str, conteudo: str) -> bool:
        titulo = (titulo or "").strip()
        conteudo = (conteudo or "").strip()
        if not titulo or not conteudo:
            return False
        if not self._comando_disponivel("termux-notification"):
            return False

        resultado = self._runner(
            ["termux-notification", "--title", titulo, "--content", conteudo],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return resultado.returncode == 0


def modo_interface_padrao() -> str:
    """Seleciona a interface sem esconder indisponibilidade."""
    valor = os.environ.get("STACY_INTERFACE", "texto").strip().lower()
    if valor in {"texto", "voz"}:
        return valor
    return "texto";
