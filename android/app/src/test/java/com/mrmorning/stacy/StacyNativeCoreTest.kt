package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyNativeCoreTest {
    private val core = StacyNativeCore()

    @Test
    fun diagnosticProbeIsAnsweredLocallyWithoutTermux() {
        val result = core.process("Teste de comunicação sem Termux") 
        assertNotNull(result)
        assertTrue(result!!.response.contains("CORE NATIVO: ONLINE"))
        assertTrue(result.response.contains("Termux para este teste: não utilizado"))
        assertTrue(result.response.contains("IA generativa / Orchestrator Python: não testados"))
    }

    @Test
    fun earlierResponseProbeIsCompatible() {
        val result = core.process("Olá, STACY. Responda apenas: Estou funcionando, senhor.")
        assertNotNull(result)
        assertEquals("Estou funcionando, senhor.", result!!.response)
    }

    @Test
    fun greetingIsFastAndDeterministic() {
        val result = core.process("BOM DIA, STACY!")
        assertNotNull(result)
        assertEquals("resposta", result!!.tipo)
        assertTrue(result.response.contains("CORE nativo"))
    }

    @Test
    fun unrelatedRequestsFallThroughToExistingPythonCore() {
        assertNull(core.process("Pesquise a previsão do tempo para amanhã."))
        assertNull(core.process("Crie uma tarefa para sexta-feira."))
    }
}
