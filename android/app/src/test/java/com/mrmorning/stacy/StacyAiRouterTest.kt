package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyAiRouterTest {
    @Test
    fun remoteProviderIsBlockedWithoutFreeTierAcknowledgement() {
        val route = StacyAiRouter.choose(
            message = "Olá, STACY",
            freeTierConfirmed = false,
            apiKeyAvailable = true,
        )

        assertEquals(StacyAiProvider.NONE, route.provider)
        assertEquals("external_provider_not_authorized", route.reason)
    }

    @Test
    fun remoteProviderIsBlockedWhenCredentialIsMissing() {
        val route = StacyAiRouter.choose(
            message = "Olá, STACY",
            freeTierConfirmed = true,
            apiKeyAvailable = false,
        )

        assertEquals(StacyAiProvider.NONE, route.provider)
        assertEquals("provider_credential_unavailable", route.reason)
    }

    @Test
    fun freeTierProviderIsSelectedOnlyWithExplicitConsentAndCredential() {
        val route = StacyAiRouter.choose(
            message = "Converse comigo",
            freeTierConfirmed = true,
            apiKeyAvailable = true,
        )

        assertEquals(StacyAiProvider.GEMINI_FREE_TIER, route.provider)
        assertFalse(route.useWebSearch)
    }

    @Test
    fun currentInformationRoutesToResearchOnlyWhenRemoteProviderIsEnabled() {
        val blocked = StacyAiRouter.choose(
            message = "Pesquise as notícias de hoje",
            freeTierConfirmed = false,
            apiKeyAvailable = true,
        )
        val enabled = StacyAiRouter.choose(
            message = "Pesquise as notícias de hoje",
            freeTierConfirmed = true,
            apiKeyAvailable = true,
        )

        assertEquals(StacyAiProvider.NONE, blocked.provider)
        assertTrue(blocked.useWebSearch)
        assertEquals(StacyAiProvider.GEMINI_FREE_TIER, enabled.provider)
        assertTrue(enabled.useWebSearch)
    }

    @Test
    fun localOnlyResearchMessageDoesNotPretendItWasVerified() {
        val route = StacyAiRouter.choose(
            message = "Pesquise a legislação atual",
            freeTierConfirmed = false,
            apiKeyAvailable = false,
        )

        val message = StacyAiRouter.offlineMessage(route)
        assertTrue(message.contains("não vou inventar"))
        assertTrue(message.contains("fontes"))
    }
}
