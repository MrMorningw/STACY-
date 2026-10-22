package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyNativeCoreTest {
    @Test
    fun greetingIsAnsweredWithoutNetwork() {
        val result = StacyNativeCore().process("Olá, STACY!")
        assertNotNull(result)
        assertEquals("resposta", result?.tipo)
        assertTrue(result?.response?.contains("CORE nativo") == true)
    }

    @Test
    fun diagnosticReportsLocalRuntime() {
        val result = StacyNativeCore().process("diagnóstico do CORE nativo")
        assertNotNull(result)
        assertTrue(result?.response?.contains("Kotlin / Android") == true)
        assertTrue(result?.response?.contains("CORE NATIVO: ONLINE") == true)
    }

    @Test
    fun unknownQuestionIsNotFalselyReportedAsHandledLocally() {
        assertNull(StacyNativeCore().process("Explique a teoria geral dos contratos"))
    }

    @Test
    fun whatsappCommandIsRoutedToAllowListedAndroidAction() {
        val result = StacyNativeCore().process("Abra o WhatsApp")
        assertNotNull(result)
        assertEquals("abrir_aplicativo", result?.androidAction?.get("acao"))
        assertEquals("com.whatsapp", result?.androidAction?.get("pacote"))
    }

    @Test
    fun unknownAppsAreNotExecutedLocally() {
        assertNull(StacyNativeCore().process("Abra um aplicativo desconhecido"))
    }

    @Test
    fun shareActionPreservesUserTextAndRequiresAndroidChooser() {
        val result = StacyNativeCore().process("Compartilhe: Olá, equipe!")
        assertNotNull(result)
        assertEquals("compartilhar_texto", result?.androidAction?.get("acao"))
        assertEquals("Olá, equipe!", result?.androidAction?.get("texto"))
    }
}
