"""Camada de voz da STACY.

Define o contrato independente de plataforma para entrada e saída de voz.
O módulo não depende de Termux, Android ou internet. A plataforma fornece
adaptadores de captura/STT/TTS e o STACY Core continua responsável pelo
processamento da mensagem.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Protocol


class EstadoVoz(str, Enum):
    OCIOSO = "ocioso"
    OUVINDO = "ouvindo"
    PROCESSANDO = "processando"
    FALANDO = "falando"
    ERRO = "erro"


class ReconhecedorVoz(Protocol):
    def ouvir(self) -> str:
        """Captura áudio e devolve o texto reconhecido."""


class SintetizadorVoz(Protocol):
    def falar(self, texto: str) -> None:
        """Converte texto em áudio e o reproduz."""


@dataclass
class ResultadoVoz:
    estado: EstadoVoz
    texto_entrada: Optional[str] = None
    resposta: Optional[str] = None
    erro: Optional[str] = None


class VoiceController:
    """Orquestra voz sem conhecer a implementação Android."""

    def __init__(
        self,
        processar_mensagem: Callable[[str], dict],
        reconhecedor: ReconhecedorVoz,
        sintetizador: SintetizadorVoz,
    ):
        self._processar_mensagem = processar_mensagem
        self._reconhecedor = reconhecedor
        self._sintetizador = sintetizador
        self.estado = EstadoVoz.OCIOSO

    def executar_uma_interacao(self) -> ResultadoVoz:
        """Executa uma interação fala -> STACY Core -> fala."""
        try:
            self.estado = EstadoVoz.OUVINDO
            texto = self._reconhecedor.ouvir()

            if not isinstance(texto, str) or not texto.strip():
                self.estado = EstadoVoz.OCIOSO
                return ResultadoVoz(
                    estado=self.estado,
                    texto_entrada=texto if isinstance(texto, str) else None,
                )

            self.estado = EstadoVoz.PROCESSANDO
            resultado = self._processar_mensagem(texto)

            if not isinstance(resultado, dict):
                raise TypeError("O STACY Core deve retornar um dicionário.")

            resposta = resultado.get("resposta")

            if isinstance(resposta, str) and resposta.strip():
                self.estado = EstadoVoz.FALANDO
                self._sintetizador.falar(resposta)

            self.estado = EstadoVoz.OCIOSO

            return ResultadoVoz(
                estado=self.estado,
                texto_entrada=texto,
                resposta=resposta,
            )

        except Exception as erro:
            self.estado = EstadoVoz.ERRO
            return ResultadoVoz(
                estado=self.estado,
                erro=str(erro),
            )
