package com.mrmorning.stacy

import org.json.JSONArray
import java.net.URI

/**
 * GRILL: deterministic supervisory gate for every result leaving the native CORE.
 *
 * This layer validates response integrity, evidence metadata and Android action
 * allow-lists. It does not claim to prove factual correctness; that requires
 * source content review or an independent verifier.
 */
internal data class GrillVerdict(
    val approved: Boolean,
    val risk: String,
    val checks: Map<String, Boolean>,
    val findings: List<String>,
) {
    val decision: String get() = if (approved) "APPROVE" else "VETO"
}

internal object StacyGrillSupervisor {
    private const val MAX_RESPONSE_CHARS = 12_000
    private const val MAX_SOURCES = 20
    private const val MAX_SHARED_TEXT_CHARS = 4_000

    private val allowedPackages = setOf(
        "com.whatsapp",
        "com.google.android.youtube",
        "com.android.chrome",
        "com.google.android.gm",
        "com.spotify.music",
        "com.google.android.apps.maps",
    )

    fun review(
        request: String,
        candidate: CoreResult,
        requiresExternalEvidence: Boolean = false,
    ): GrillVerdict {
        val findings = mutableListOf<String>()
        val checks = linkedMapOf(
            "request_nonempty" to request.isNotBlank(),
            "type_nonempty" to candidate.tipo.isNotBlank(),
            "result_state_consistent" to true,
            "response_bounded" to true,
            "action_allowlisted" to true,
            "sources_well_formed" to true,
            "research_has_sources" to true,
        )

        if (!checks.getValue("request_nonempty")) findings += "solicitação vazia"
        if (!checks.getValue("type_nonempty")) findings += "tipo de resultado ausente"

        val isError = candidate.tipo.equals("erro", ignoreCase = true) ||
            candidate.tipo.equals("error", ignoreCase = true)

        if (candidate.exitCode != 0 && !isError) {
            checks["result_state_consistent"] = false
            findings += "resultado relata falha sem tipo de erro"
        }

        val action = candidate.androidAction
        if (action != null) {
            checks["action_allowlisted"] = validateAction(candidate)
            if (!checks.getValue("action_allowlisted")) {
                findings += "ação Android inválida ou fora da lista autorizada"
            }
        } else {
            if (candidate.tipo.equals("execucao", ignoreCase = true)) {
                checks["action_allowlisted"] = false
                findings += "execução sem uma ação Android identificável"
            }
            if (!isError && candidate.response.isBlank()) {
                checks["response_bounded"] = false
                findings += "resposta vazia"
            }
            if (candidate.response.length > MAX_RESPONSE_CHARS) {
                checks["response_bounded"] = false
                findings += "resposta excede o limite de segurança"
            }
        }

        val sourceCount = candidate.fontes?.length() ?: 0
        val sourcesValid = validateSources(candidate.fontes)
        if (!sourcesValid) {
            checks["sources_well_formed"] = false
            findings += "metadados de fontes inválidos"
        }

        if (requiresExternalEvidence && !isError && sourceCount == 0) {
            checks["research_has_sources"] = false
            findings += "pesquisa concluída sem fontes externas"
        }

        val risk = when {
            action != null -> "high"
            requiresExternalEvidence -> "medium"
            else -> "low"
        }
        return GrillVerdict(
            approved = checks.values.all { it },
            risk = risk,
            checks = checks.toMap(),
            findings = findings.toList(),
        )
    }

    private fun validateAction(candidate: CoreResult): Boolean {
        if (!candidate.tipo.equals("execucao", ignoreCase = true)) return false
        if (candidate.response.isNotBlank()) return false

        val action = candidate.androidAction ?: return false
        val operation = action.optString("acao").trim()
        return when (operation) {
            "abrir_configuracoes", "abrir_calendario", "selecionar_arquivo" -> true
            "abrir_aplicativo" -> action.optString("pacote") in allowedPackages
            "compartilhar_texto" -> action.optString("texto").let {
                it.isNotBlank() && it.length <= MAX_SHARED_TEXT_CHARS
            }
            else -> false
        }
    }

    private fun validateSources(sources: JSONArray?): Boolean {
        if (sources == null) return true
        if (sources.length() > MAX_SOURCES) return false

        val seen = mutableSetOf<String>()
        for (index in 0 until sources.length()) {
            val item = sources.optJSONObject(index) ?: return false
            val rawUrl = item.optString("url").trim()
            val title = item.optString("titulo").trim()
            if (title.isEmpty() || rawUrl.isEmpty()) return false

            val uri = try {
                URI(rawUrl)
            } catch (_: Exception) {
                return false
            }
            if (!uri.scheme.equals("https", ignoreCase = true) || uri.host.isNullOrBlank()) {
                return false
            }
            if (!seen.add(rawUrl)) return false
        }
        return true
    }
}
