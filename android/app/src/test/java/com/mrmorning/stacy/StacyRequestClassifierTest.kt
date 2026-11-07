package com.mrmorning.stacy

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyRequestClassifierTest {

    @Test
    fun ordinaryConversationDoesNotTriggerWebResearch() {
        assertFalse(StacyRequestClassifier.requiresWebSearch("Como você está hoje?"))
        assertFalse(StacyRequestClassifier.requiresWebSearch("Explique o que é inteligência artificial."))
        assertFalse(StacyRequestClassifier.requiresWebSearch("Me ajude a escrever uma mensagem para hoje."))
        assertFalse(StacyRequestClassifier.requiresWebSearch("O que significa pesquisar em um trabalho acadêmico?"))
    }

    @Test
    fun explicitWebResearchAlwaysUsesResearchProfile() {
        assertTrue(StacyRequestClassifier.requiresWebSearch("Pesquise na internet as últimas notícias de tecnologia."))
        assertTrue(StacyRequestClassifier.requiresWebSearch("Busque na web fontes externas sobre inteligência artificial."))
        assertTrue(StacyRequestClassifier.requiresWebSearch("Procure na internet onde assistir ao torneio."))
    }

    @Test
    fun currentInformationTopicsUseResearchProfile() {
        assertTrue(StacyRequestClassifier.requiresWebSearch("Qual é o preço do dólar hoje?"))
        assertTrue(StacyRequestClassifier.requiresWebSearch("Qual é a legislação atual sobre proteção de dados?"))
        assertTrue(StacyRequestClassifier.requiresWebSearch("Quais são as notícias mais recentes?"))
        assertTrue(StacyRequestClassifier.requiresWebSearch("Qual é a versão atual do Android?"))
    }

    @Test
    fun currentSignalWithoutCurrentTopicDoesNotTriggerResearch() {
        assertFalse(StacyRequestClassifier.requiresWebSearch("Hoje quero estudar contratos."))
        assertFalse(StacyRequestClassifier.requiresWebSearch("Agora me explique a diferença entre dolo e culpa."))
    }
}
