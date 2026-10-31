package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class StacyCoreProviderTest {
    @Test
    fun unconfiguredProviderReturnsExplicitErrorInsteadOfCallingLegacyCore() {
        val provider = UnconfiguredStacyCoreProvider()
        var result: CoreResult? = null

        provider.process("Olá, STACY") { result = it }

        assertNotNull(result)
        assertEquals("erro", result?.tipo)
        assertEquals(2, result?.exitCode)
        assertEquals("CORE_PROVIDER_NOT_CONFIGURED", result?.stderr)
    }

    @Test
    fun providerHasStableReplaceableIdentity() {
        assertEquals("unconfigured", UnconfiguredStacyCoreProvider().providerId)
    }
}
