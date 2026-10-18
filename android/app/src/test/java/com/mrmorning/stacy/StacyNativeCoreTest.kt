package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyNativeCoreTest {
    private val core = StacyNativeCore()

    @Test
    fun diagnosticProbeIsAnsweredLocallyWithoutTermux() {
        val result = requireNotNull(core.process("Teste de comunicação sem Termux"))
        assertTrue(result.response.contains("CORE NATIVO: ONLINE"))
        assertTrue(result.response.contains("Termux para este teste: não utilizado"))
        assertTrue(result.response.contains("IA generativa / Orchestrator Python: não testados"))
    }

    @Test
    fun earlierResponseProbeIsCompatible() {
        val result = requireNotNull(core.process("Olá, STACY. Responda apenas: Estou funcionando, senhor."))
        assertEquals("Estou funcionando, senhor.", result.response)
    }

    @Test
    fun greetingIsFastAndDeterministic() {
        val result = requireNotNull(core.process("BOM DIA, STACY!"))
        assertEquals("resposta", result.tipo)
        assertTrue(result.response.contains("CORE nativo"))
    }

    @Test
    fun unrelatedRequestsFallThroughToExistingPythonCore() {
        assertNull(core.process("Pesquise a previsão do tempo para amanhã."))
        assertNull(core.process("Crie uma tarefa para sexta-feira."))
    }
}
