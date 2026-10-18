package com.mrmorning.stacy

import java.text.Normalizer
import java.util.Locale

/**
 * Lightweight, deterministic Android-side fast path.
 *
 * This is intentionally not presented as a replacement for the generative
 * Python/LLM orchestrator: it handles greetings and explicit health probes
 * locally, without Termux, a server socket, or a network request.
 */
internal class StacyNativeCore {

    fun process(message: String): CoreResult? {
        val normalized = normalize(message)
        if (normalized.isBlank()) return null

        if (isResponseProbe(normalized)) {
            return response("Estou funcionando, senhor.")
        }

        if (isDiagnosticProbe(normalized)) {
            return response(
                listOf(
                    "CORE NATIVO: ONLINE",
                    "Runtime: Kotlin / Android",
                    "Caminho: interface → ponte Android → Core Native → interface",
                    "Termux para este teste: não utilizado",
                    "IA generativa / Orchestrator Python: não testados neste diagnóstico.",
                ).joinToString("\n"),
            )
        }

        if (normalized in GREETINGS) {
            return response("Olá, senhor. Estou funcionando pelo CORE nativo.")
        }

        return null
    }

    private fun response(text: String) = CoreResult(
        tipo = "resposta",
        response = text,
        exitCode = 0,
        stderr = "",
    )

    private fun isResponseProbe(text: String): Boolean =
        text == "teste de resposta nativa" ||
            text == "teste nativo de resposta" ||
            text.contains("responda apenas estou funcionando senhor") ||
            text.contains("responda somente estou funcionando senhor")

    private fun isDiagnosticProbe(text: String): Boolean {
        val probes = listOf(
            "teste nativo",
            "teste do nucleo nativo",
            "teste de comunicacao",
            "teste de comunicacao sem termux",
            "diagnostico nativo",
            "diagnostico do core",
            "status do core nativo",
            "status operacional do nucleo stacy",
            "verifique o status operacional do nucleo stacy",
            "status dos componentes",
            "saude da stacy",
        )
        return probes.any(text::contains)
    }

    private fun normalize(value: String): String =
        Normalizer.normalize(value, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
            .replace(Regex("[^a-z0-9\\s]"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()

    private companion object {
        val GREETINGS = setOf(
            "oi",
            "ola",
            "ola stacy",
            "oi stacy",
            "bom dia",
            "bom dia stacy",
            "boa tarde",
            "boa tarde stacy",
            "boa noite",
            "boa noite stacy",
            "tudo bem",
            "como vai",
            "como esta",
        )
    }
}
