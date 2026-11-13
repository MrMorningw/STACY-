package com.mrmorning.stacy

/**
 * Provider-agnostic decision point for the hybrid manager.
 *
 * The native CORE is always attempted before this router. The only currently
 * implemented remote adapter is Gemini; it is selectable only after explicit
 * Free-tier acknowledgement and key availability.
 */
internal enum class StacyAiProvider {
    NONE,
    GEMINI_FREE_TIER,
}

internal data class StacyAiRoute(
    val provider: StacyAiProvider,
    val useWebSearch: Boolean,
    val reason: String,
)

internal object StacyAiRouter {
    fun choose(
        message: String,
        freeTierConfirmed: Boolean,
        apiKeyAvailable: Boolean,
    ): StacyAiRoute {
        val useWebSearch = StacyRequestClassifier.requiresWebSearch(message)
        if (message.isBlank()) {
            return StacyAiRoute(StacyAiProvider.NONE, useWebSearch, "empty_request")
        }
        if (!freeTierConfirmed) {
            return StacyAiRoute(StacyAiProvider.NONE, useWebSearch, "external_provider_not_authorized")
        }
        if (!apiKeyAvailable) {
            return StacyAiRoute(StacyAiProvider.NONE, useWebSearch, "provider_credential_unavailable")
        }
        return StacyAiRoute(
            provider = StacyAiProvider.GEMINI_FREE_TIER,
            useWebSearch = useWebSearch,
            reason = if (useWebSearch) "free_tier_research" else "free_tier_chat",
        )
    }

    fun offlineMessage(route: StacyAiRoute): String = when (route.reason) {
        "empty_request" -> "Não recebi uma solicitação válida."
        "provider_credential_unavailable" ->
            "O CORE local continua disponível, mas nenhum provedor generativo está configurado. Nenhuma chamada externa foi feita."
        else -> if (route.useWebSearch) {
            "Esta solicitação exige pesquisa externa. A conexão externa está bloqueada para evitar custos; não vou inventar ou apresentar fatos atuais sem fontes."
        } else {
            "O CORE local está ativo. A conversa generativa externa permanece bloqueada para impedir cobranças não autorizadas. Tarefas, memória e comandos locais continuam disponíveis."
        }
    }
}
