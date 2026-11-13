package com.mrmorning.stacy

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyGrillSupervisorTest {
    @Test
    fun approvesBoundedOrdinaryResponse() {
        val result = CoreResult(
            tipo = "resposta",
            response = "Olá. Estou pronta.",
            exitCode = 0,
            stderr = "",
        )

        val verdict = StacyGrillSupervisor.review("oi", result)

        assertTrue(verdict.approved)
        assertTrue(verdict.checks.values.all { it })
        assertTrue(verdict.risk == "low")
    }

    @Test
    fun rejectsEmptySuccessfulResponse() {
        val result = CoreResult(
            tipo = "resposta",
            response = "",
            exitCode = 0,
            stderr = "",
        )

        val verdict = StacyGrillSupervisor.review("explique isto", result)

        assertFalse(verdict.approved)
        assertTrue(verdict.findings.contains("resposta vazia"))
    }

    @Test
    fun rejectsOversizedResponse() {
        val result = CoreResult(
            tipo = "resposta",
            response = "x".repeat(12_001),
            exitCode = 0,
            stderr = "",
        )

        val verdict = StacyGrillSupervisor.review("responda", result)

        assertFalse(verdict.approved)
        assertTrue(verdict.findings.contains("resposta excede o limite de segurança"))
    }

    @Test
    fun rejectsSuccessfulResearchWithoutSources() {
        val result = CoreResult(
            tipo = "resposta",
            response = "A informação solicitada é esta.",
            exitCode = 0,
            stderr = "",
        )

        val verdict = StacyGrillSupervisor.review(
            request = "pesquise na internet",
            candidate = result,
            requiresExternalEvidence = true,
        )

        assertFalse(verdict.approved)
        assertTrue(verdict.findings.contains("pesquisa concluída sem fontes externas"))
    }

    @Test
    fun permitsExplicitResearchFailureWithoutInventedSources() {
        val result = CoreResult(
            tipo = "erro",
            response = "Não foi possível verificar fontes externas.",
            exitCode = 1,
            stderr = "sem conexão",
        )

        val verdict = StacyGrillSupervisor.review(
            request = "pesquise na internet",
            candidate = result,
            requiresExternalEvidence = true,
        )

        assertTrue(verdict.approved)
    }

    @Test
    fun rejectsContradictoryFailureState() {
        val result = CoreResult(
            tipo = "resposta",
            response = "Concluído.",
            exitCode = 1,
            stderr = "falha",
        )

        val verdict = StacyGrillSupervisor.review("execute", result)

        assertFalse(verdict.approved)
        assertTrue(verdict.findings.contains("resultado relata falha sem tipo de erro"))
    }

    @Test
    fun rejectsExecutionWithoutAnAuthorizedActionObject() {
        val result = CoreResult(
            tipo = "execucao",
            response = "",
            exitCode = 0,
            stderr = "",
        )

        val verdict = StacyGrillSupervisor.review("abra o calendário", result)

        assertFalse(verdict.approved)
        assertTrue(verdict.findings.contains("execução sem uma ação Android identificável"))
    }
}
