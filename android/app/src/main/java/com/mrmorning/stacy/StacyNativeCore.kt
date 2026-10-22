package com.mrmorning.stacy

import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

/**
 * Lightweight, deterministic Android-side fast path.
 *
 * It handles greetings, runtime probes, and an allow-listed set of Android
 * actions locally. Unknown requests are sent to the native HTTPS AI transport.
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
                    "IA generativa/API: não testada neste diagnóstico.",
                ).joinToString("\n"),
            )
        }

        if (normalized in GREETINGS) {
            return response("Olá, senhor. Estou funcionando pelo CORE nativo.")
        }

        actionFor(message, normalized)?.let { return it }

        return null
    }

    private fun actionFor(original: String, normalized: String): CoreResult? {
        if (normalized in OPEN_SETTINGS_PHRASES) {
            return androidAction("abrir_configuracoes")
        }

        if (normalized in OPEN_CALENDAR_PHRASES) {
            return androidAction("abrir_calendario")
        }

        if (normalized in SELECT_FILE_PHRASES) {
            return androidAction("selecionar_arquivo", mimeType = "*/*")
        }

        val openMatch = OPEN_APP_PATTERN.matchEntire(normalized)
        if (openMatch != null) {
            val target = openMatch.groupValues[1].trim()
            val app = ALLOWED_APPS[target]
            if (app != null) {
                return androidAction(
                    operation = "abrir_aplicativo",
                    packageName = app.first,
                    appName = app.second,
                )
            }
        }

        val shareMatch = SHARE_PATTERN.matchEntire(original.trim())
        if (shareMatch != null) {
            val text = shareMatch.groupValues[1].trim()
            if (text.isNotEmpty()) {
                return androidAction("compartilhar_texto", shareText = text)
            }
        }

        return null
    }

    private fun androidAction(
        operation: String,
        packageName: String? = null,
        appName: String? = null,
        shareText: String? = null,
        mimeType: String? = null,
    ): CoreResult {
        val action = JSONObject().put("acao", operation)
        if (packageName != null) action.put("pacote", packageName)
        if (appName != null) action.put("nome", appName)
        if (shareText != null) action.put("texto", shareText)
        if (mimeType != null) action.put("mime_type", mimeType)
        return CoreResult(
            tipo = "execucao",
            response = "",
            exitCode = 0,
            stderr = "",
            androidAction = action,
        )
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

        val OPEN_SETTINGS_PHRASES = setOf(
            "abrir configuracoes",
            "abre configuracoes",
            "abra configuracoes",
            "abrir ajustes",
            "abre ajustes",
            "abra ajustes",
            "configuracoes do android",
            "ajustes do android",
        )

        val OPEN_CALENDAR_PHRASES = setOf(
            "abrir calendario",
            "abre calendario",
            "abra calendario",
            "abrir agenda",
            "abre agenda",
            "abra agenda",
        )

        val SELECT_FILE_PHRASES = setOf(
            "selecionar arquivo",
            "selecione arquivo",
            "escolher arquivo",
            "escolha arquivo",
            "abrir seletor de arquivos",
        )

        val OPEN_APP_PATTERN = Regex(
            "^(?:abra|abrir|abre|inicie|iniciar|execute|executar)\\\\s+(?:(?:o|a|os|as)\\\\s+)?(.+)$",
        )

        val SHARE_PATTERN = Regex(
            "^(?:compartilhar|compartilhe|compartilha)\\\\s*(?::|-)?\\\\s*(.+)$",
            RegexOption.IGNORE_CASE,
        )

        val ALLOWED_APPS = mapOf(
            "whatsapp" to ("com.whatsapp" to "WhatsApp"),
            "youtube" to ("com.google.android.youtube" to "YouTube"),
            "chrome" to ("com.android.chrome" to "Chrome"),
            "gmail" to ("com.google.android.gm" to "Gmail"),
            "spotify" to ("com.spotify.music" to "Spotify"),
            "google maps" to ("com.google.android.apps.maps" to "Google Maps"),
            "maps" to ("com.google.android.apps.maps" to "Google Maps"),
        )
    }
}
