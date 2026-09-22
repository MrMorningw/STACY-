"""Núcleo determinístico de autonomia controlada da STACY.

Responsabilidade: impedir que decisões produzidas por IA executem ações
diretamente. Ações determinísticas identificadas pelo CORE continuam
executáveis; ações originadas exclusivamente da IA exigem confirmação
explícita antes da execução.
"""

ORIGEM_CORE = "core"
ORIGEM_IA = "ia"

STATUS_AUTORIZADA = "autorizada"
STATUS_CONFIRMAR = "confirmar"
STATUS_INVALIDA = "invalida"


def avaliar_execucao(intencao):
    """Determina se uma intenção pode seguir para execução."""
    if not isinstance(intencao, dict):
        return {
            "status": STATUS_INVALIDA,
            "executar": False,
            "motivo": "intencao_invalida",
        }

    tipo = intencao.get("tipo")
    if tipo not in {"tarefa", "memoria"}:
        return {
            "status": STATUS_INVALIDA,
            "executar": False,
            "motivo": "tipo_nao_executavel",
        }

    origem = intencao.get("origem", ORIGEM_CORE)

    if origem == ORIGEM_IA:
        return {
            "status": STATUS_CONFIRMAR,
            "executar": False,
            "motivo": "acao_originada_por_ia_requer_confirmacao",
        }

    if origem != ORIGEM_CORE:
        return {
            "status": STATUS_INVALIDA,
            "executar": False,
            "motivo": "origem_nao_autorizada",
        }

    return {
        "status": STATUS_AUTORIZADA,
        "executar": True,
        "motivo": "acao_deterministica_do_core",
    }
