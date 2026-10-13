"""ANPES — camada inicial de planejamento e execução controlada da STACY.

Este módulo valida planos e delega apenas ferramentas explicitamente registradas.
Não executa código arbitrário, shell, nem alterações no próprio núcleo.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Optional

VERSAO_PLANO = 1
MAX_ETAPAS = 8
MAX_TAMANHO_TEXTO = 500
MAX_ARGUMENTOS = 32

RISCO_BAIXO = "baixo"
RISCO_MEDIO = "medio"
RISCO_ALTO = "alto"
RISCO_CRITICO = "critico"

MODO_ASSISTIDO = "assistido"
MODO_AUTONOMIA_LIMITADA = "autonomia_limitada"

# Catálogo de capacidades planejáveis, não uma afirmação de que os executores
# já estejam conectados. A execução só ocorre quando o runtime fornece handler.
FERRAMENTAS = {
    "diagnostico.status": {
        "risco": RISCO_BAIXO,
        "descricao": "Consultar o estado operacional da STACY.",
    },
    "diagnostico.executar_testes": {
        "risco": RISCO_BAIXO,
        "descricao": "Executar uma suíte de testes previamente definida.",
    },
    "codigo.inspecionar": {
        "risco": RISCO_BAIXO,
        "descricao": "Inspecionar arquivos e produzir diagnóstico sem alterá-los.",
    },
    "memoria.consultar": {
        "risco": RISCO_BAIXO,
        "descricao": "Consultar memória autorizada do usuário.",
    },
    "android.abrir_app": {
        "risco": RISCO_MEDIO,
        "descricao": "Solicitar ao executor Android a abertura de um aplicativo conhecido.",
    },
    "memoria.registrar": {
        "risco": RISCO_MEDIO,
        "descricao": "Adicionar uma informação à memória pessoal.",
    },
    "codigo.propor_alteracao": {
        "risco": RISCO_ALTO,
        "descricao": "Preparar uma proposta de mudança sem aplicá-la.",
    },
    "codigo.aplicar_alteracao": {
        "risco": RISCO_CRITICO,
        "descricao": "Aplicar uma mudança de código; exige aprovação explícita.",
    },
    "android.acao_externa": {
        "risco": RISCO_ALTO,
        "descricao": "Executar uma ação que possa afetar terceiros ou serviços externos.",
    },
}



# Contrato compatível com o gate de autonomia que o CORE já utiliza.
# Mantém a política histórica: intenções extraídas pela IA não executam
# diretamente; comandos determinísticos do CORE seguem pelo fluxo existente.
ORIGEM_CORE = "core"
ORIGEM_IA = "ia"
STATUS_AUTORIZADA = "autorizada"
STATUS_CONFIRMAR = "confirmar"
STATUS_INVALIDA = "invalida"


def avaliar_intencao(intencao: Any) -> dict:
    """Avalia uma intenção do CORE usando o gate central do ANPES."""
    if not isinstance(intencao, dict):
        return {"status": STATUS_INVALIDA, "executar": False, "motivo": "intencao_invalida"}

    tipo = intencao.get("tipo")
    if tipo not in {"tarefa", "memoria"}:
        return {"status": STATUS_INVALIDA, "executar": False, "motivo": "tipo_nao_executavel"}

    origem = intencao.get("origem", ORIGEM_CORE)
    if origem == ORIGEM_IA:
        return {"status": STATUS_CONFIRMAR, "executar": False, "motivo": "acao_originada_por_ia_requer_confirmacao"}
    if origem != ORIGEM_CORE:
        return {"status": STATUS_INVALIDA, "executar": False, "motivo": "origem_nao_autorizada"}

    return {"status": STATUS_AUTORIZADA, "executar": True, "motivo": "acao_deterministica_do_core"}


def _erro(codigo: str, detalhe: str = "") -> dict:
    resultado = {"status": "invalido", "executar": False, "motivo": codigo}
    if detalhe:
        resultado["detalhe"] = detalhe[:MAX_TAMANHO_TEXTO]
    return resultado


def validar_plano(plano: Any) -> dict:
    """Valida formato, tamanho e ferramentas de um plano sem executar ações."""
    if not isinstance(plano, dict):
        return _erro("plano_deve_ser_objeto")

    if plano.get("versao") != VERSAO_PLANO:
        return _erro("versao_de_plano_nao_suportada")

    titulo = plano.get("titulo")
    etapas = plano.get("etapas")
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > MAX_TAMANHO_TEXTO:
        return _erro("titulo_invalido")
    if not isinstance(etapas, list) or not etapas:
        return _erro("etapas_invalidas")
    if len(etapas) > MAX_ETAPAS:
        return _erro("limite_de_etapas_excedido")

    ids = set()
    etapas_validadas = []
    for indice, etapa in enumerate(etapas):
        if not isinstance(etapa, dict):
            return _erro("etapa_invalida", f"Índice {indice}")
        etapa_id = etapa.get("id")
        ferramenta = etapa.get("ferramenta")
        argumentos = etapa.get("argumentos", {})
        if not isinstance(etapa_id, str) or not etapa_id.strip() or len(etapa_id) > 64:
            return _erro("id_de_etapa_invalido", f"Índice {indice}")
        if etapa_id in ids:
            return _erro("id_de_etapa_duplicado", etapa_id)
        ids.add(etapa_id)
        if not isinstance(ferramenta, str) or ferramenta not in FERRAMENTAS:
            return _erro("ferramenta_nao_autorizada", str(ferramenta))
        if not isinstance(argumentos, dict) or len(argumentos) > MAX_ARGUMENTOS:
            return _erro("argumentos_invalidos", etapa_id)
        if any(not isinstance(chave, str) or len(chave) > 100 for chave in argumentos):
            return _erro("chave_de_argumento_invalida", etapa_id)
        etapas_validadas.append({
            "id": etapa_id,
            "ferramenta": ferramenta,
            "argumentos": argumentos,
            "risco": FERRAMENTAS[ferramenta]["risco"],
        })

    return {
        "status": "valido",
        "executar": False,
        "motivo": "plano_validado_sem_execucao",
        "titulo": titulo.strip(),
        "etapas": etapas_validadas,
        "quantidade_etapas": len(etapas_validadas),
    }


def avaliar_plano(plano: Any, modo: str = MODO_ASSISTIDO) -> dict:
    """Classifica o plano e aponta as aprovações necessárias."""
    if modo not in {MODO_ASSISTIDO, MODO_AUTONOMIA_LIMITADA}:
        return _erro("modo_de_autonomia_invalido")

    validacao = validar_plano(plano)
    if validacao["status"] != "valido":
        return validacao

    exige_confirmacao = [
        etapa["id"] for etapa in validacao["etapas"]
        if etapa["risco"] != RISCO_BAIXO
    ]
    # Ambos os modos mantêm a mesma política conservadora nesta fase inicial;
    # perfis de rotina pré-aprovada serão adicionados apenas com configuração
    # confiável, separada dos planos produzidos pela IA.

    return {
        "status": "aguardando_confirmacao" if exige_confirmacao else "pronto",
        "executar": False,
        "motivo": "aprovacao_explicita_necessaria" if exige_confirmacao else "plano_de_baixo_risco",
        "titulo": validacao["titulo"],
        "etapas": validacao["etapas"],
        "etapas_que_exigem_confirmacao": exige_confirmacao,
        "modo": modo,
    }


def executar_plano(
    plano: Any,
    executores: Mapping[str, Callable[[dict], Any]],
    *,
    etapas_aprovadas: Iterable[str] = (),
    modo: str = MODO_ASSISTIDO,
    simulacao: bool = True,
    auditoria: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Executa um plano validado com handlers explícitos.

    A simulação é o padrão. Para executar, o chamador precisa definir
    simulacao=False e fornecer aprovação para cada etapa que não seja de baixo
    risco. A autorização nunca é inferida do texto gerado pelo modelo.
    """
    avaliacao = avaliar_plano(plano, modo)
    if avaliacao["status"] == "invalido":
        return avaliacao

    aprovadas = set(etapas_aprovadas)
    pendentes = [
        etapa["id"] for etapa in avaliacao["etapas"]
        if etapa["risco"] != RISCO_BAIXO and etapa["id"] not in aprovadas
    ]
    if pendentes:
        return {
            "status": "aguardando_confirmacao",
            "executar": False,
            "motivo": "etapas_sem_aprovacao_explicita",
            "etapas_pendentes": pendentes,
        }

    faltantes = [
        etapa["ferramenta"] for etapa in avaliacao["etapas"]
        if etapa["ferramenta"] not in executores
    ]
    if faltantes:
        return {
            "status": "indisponivel",
            "executar": False,
            "motivo": "executor_nao_conectado",
            "ferramentas": sorted(set(faltantes)),
        }

    if simulacao:
        return {
            "status": "simulacao",
            "executar": False,
            "motivo": "nenhuma_ferramenta_foi_executada",
            "titulo": avaliacao["titulo"],
            "etapas": [
                {"id": e["id"], "ferramenta": e["ferramenta"], "risco": e["risco"]}
                for e in avaliacao["etapas"]
            ],
        }

    resultados = []
    for etapa in avaliacao["etapas"]:
        evento = {
            "etapa": etapa["id"],
            "ferramenta": etapa["ferramenta"],
            "estado": "iniciando",
        }
        if auditoria:
            auditoria(dict(evento))
        try:
            valor = executores[etapa["ferramenta"]](dict(etapa["argumentos"]))
            resultado = {
                "id": etapa["id"],
                "status": "concluida",
                "resultado": valor,
            }
        except Exception:
            # Não expor tracebacks ou segredos na resposta operacional.
            resultado = {
                "id": etapa["id"],
                "status": "falhou",
                "motivo": "falha_interna_do_executor",
            }
        resultados.append(resultado)
        if auditoria:
            auditoria({
                "etapa": etapa["id"],
                "ferramenta": etapa["ferramenta"],
                "estado": resultado["status"],
            })
        if resultado["status"] == "falhou":
            return {
                "status": "falhou",
                "executar": False,
                "motivo": "execucao_interrompida_apos_falha",
                "resultados": resultados,
            }

    return {
        "status": "concluido",
        "executar": True,
        "motivo": "todos_os_executores_retornaram",
        "resultados": resultados,
    }
