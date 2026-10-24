package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors

/**
 * Native Gemini Interactions API transport.
 * The key is sent only in the HTTPS header. Conversation continuity is handled by
 * the provider's previous_interaction_id instead of fabricating model turns.
 */
internal class StacyAiClient(
    context: Context,
    private val endpoint: String = ENDPOINT,
) {
    private val secrets = StacySecretStore(context.applicationContext)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    fun chat(message: String, useWebSearch: Boolean = false, callback: (CoreResult) -> Unit) {
        executor.execute {
            val result = try {
                val key = secrets.getGeminiApiKey()
                if (key.isNullOrBlank()) {
                    errorResult(
                        "Os comandos locais estão ativos, senhor, mas a IA generativa ainda não foi conectada. " +
                            "Abra Menu → Ajustes → Conectar IA e salve uma chave Gemini API válida. O Termux não é necessário.",
                    )
                } else {
                    requestGemini(key, message, useWebSearch)
                }
            } catch (error: Exception) {
                errorResult("Falha ao preparar a solicitação da IA: " + (error.message ?: "erro inesperado"))
            }
            mainHandler.post { callback(result) }
        }
    }

    fun shutdown() {
        executor.shutdownNow()
    }

    private fun requestGemini(apiKey: String, message: String, useWebSearch: Boolean): CoreResult =
        requestGemini(
            apiKey = apiKey,
            message = message,
            useWebSearch = useWebSearch,
            previousInteractionId = secrets.getPreviousInteractionId(),
            retriedWithoutPreviousInteraction = false,
        )

    private fun requestGemini(
        apiKey: String,
        message: String,
        useWebSearch: Boolean,
        previousInteractionId: String?,
        retriedWithoutPreviousInteraction: Boolean,
    ): CoreResult {
        var connection: HttpURLConnection? = null
        try {
            val payload = JSONObject()
                .put("model", MODEL)
                .put("input", message)
                .put("system_instruction", SYSTEM_INSTRUCTION)
                .put(
                    "generation_config",
                    JSONObject()
                        .put("thinking_level", "low")
                        .put("max_output_tokens", 4096),
                )
                // Keep normal chat light; attach Google Search only when explicitly needed.
                .put("store", true)

            if (useWebSearch) {
                payload.put("tools", JSONArray().put(JSONObject().put("type", "google_search")))
            }
            previousInteractionId?.let { previousId ->
                payload.put("previous_interaction_id", previousId)
            }

            connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = if (useWebSearch) SEARCH_READ_TIMEOUT_MS else READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("x-goog-api-key", apiKey)
            }

            connection.outputStream.use { stream ->
                stream.write(payload.toString().toByteArray(StandardCharsets.UTF_8))
            }

            val statusCode = connection.responseCode
            val responseStream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
            val responseText = responseStream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
            val responseJson = try {
                JSONObject(responseText)
            } catch (_: Exception) {
                JSONObject()
            }

            if (statusCode !in 200..299) {
                val detail = responseJson.optJSONObject("error")?.optString("message").orEmpty()
                if (
                    !retriedWithoutPreviousInteraction &&
                    previousInteractionId != null &&
                    indicatesExpiredInteraction(statusCode, detail)
                ) {
                    // Free-tier interaction history expires after a limited retention
                    // period. Drop a stale pointer and retry once as a fresh conversation
                    // instead of leaving subsequent chat requests permanently broken.
                    secrets.clearPreviousInteractionId()
                    connection.disconnect()
                    return requestGemini(
                        apiKey = apiKey,
                        message = message,
                        useWebSearch = useWebSearch,
                        previousInteractionId = null,
                        retriedWithoutPreviousInteraction = true,
                    )
                }
                val explanation = when (statusCode) {
                    400 -> "A API Gemini recusou a solicitação (HTTP 400)."
                    401, 403 -> "A chave Gemini foi recusada ou não tem permissão para este modelo."
                    404 -> "A API Gemini não encontrou o recurso solicitado. Confira o modelo e a conexão."
                    429 -> "A cota ou o limite de solicitações da API Gemini foi atingido."
                    else -> "A API Gemini retornou HTTP " + statusCode + "."
                }
                val fullMessage = if (detail.isBlank()) {
                    explanation
                } else {
                    explanation + " Detalhe: " + detail.take(MAX_ERROR_DETAIL)
                }
                return errorResult(fullMessage)
            }

            val answer = extractText(responseJson)
            if (answer.isBlank()) {
                val status = responseJson.optString("status")
                return errorResult(
                    when (status) {
                        "requires_action" -> "A API solicitou uma ação adicional que esta versão da STACY ainda não executa."
                        "incomplete" -> "A resposta da IA ficou incompleta. Reformule a solicitação ou peça uma resposta mais curta."
                        else -> "A API Gemini terminou sem devolver texto. Tente novamente."
                    },
                )
            }

            responseJson.optString("id")
                .takeIf { it.isNotBlank() && it != "null" }
                ?.let(secrets::savePreviousInteractionId)

            val sources = extractSources(responseJson.optJSONArray("steps"))
            return CoreResult(
                tipo = "resposta",
                response = answer,
                exitCode = 0,
                stderr = "",
                fontes = sources.takeIf { it.length() > 0 },
            )
        } catch (_: UnknownHostException) {
            return errorResult("Sem conexão com a internet. Os comandos locais continuam disponíveis.")
        } catch (_: SocketTimeoutException) {
            return errorResult("A IA demorou demais para responder. Verifique a conexão e tente novamente.")
        } catch (error: Exception) {
            val detail = error.message?.take(MAX_ERROR_DETAIL).orEmpty()
            return errorResult(
                if (detail.isBlank()) "Não foi possível conectar à IA Gemini." else "Falha na conexão com a IA Gemini: " + detail,
            )
        } finally {
            connection?.disconnect()
        }
    }

    private fun indicatesExpiredInteraction(statusCode: Int, detail: String): Boolean {
        if (statusCode != 400 && statusCode != 404) return false
        val normalized = detail.lowercase(java.util.Locale.ROOT)
        if (normalized.contains("previous_interaction_id")) return true
        return normalized.contains("interaction") &&
            listOf("not found", "expired", "unknown").any(normalized::contains)
    }

    private fun extractText(response: JSONObject): String {
        // Prefer the convenience field when supplied; standard REST responses expose steps.
        val direct = response.opt("output_text")
        if (direct is String && direct.isNotBlank()) return direct.trim()

        val steps = response.optJSONArray("steps")
            ?: response.optJSONArray("output")
            ?: response.optJSONArray("outputs")
            ?: return ""
        val output = ArrayList<String>()
        for (i in 0 until steps.length()) {
            val step = steps.optJSONObject(i) ?: continue
            val type = step.optString("type")
            if (type.isNotBlank() && type !in setOf("model_output", "text", "output_text")) continue

            val directText = step.opt("text")
            if (directText is String && directText.isNotBlank()) {
                output.add(directText)
                continue
            }

            val content = step.optJSONArray("content")
            if (content != null) {
                for (j in 0 until content.length()) {
                    val part = content.optJSONObject(j) ?: continue
                    val partType = part.optString("type")
                    if (partType.isNotBlank() && partType != "text") continue
                    part.optString("text").takeIf { it.isNotBlank() }?.let(output::add)
                }
            } else {
                step.optString("output_text").takeIf { it.isNotBlank() }?.let(output::add)
            }
        }
        return output.joinToString("\n").trim()
    }

    /**
     * Extract links if the provider supplies structured URLs in search result steps.
     * Response shapes that don't supply URLs produce no source list.
     */
    private fun extractSources(steps: JSONArray?): JSONArray {
        val sources = JSONArray()
        if (steps == null) return sources
        for (i in 0 until steps.length()) {
            val step = steps.optJSONObject(i) ?: continue
            if (step.optString("type") != "google_search_result") continue
            val results = step.optJSONArray("result") ?: continue
            for (j in 0 until results.length()) {
                val item = results.optJSONObject(j) ?: continue
                val url = (item.optString("url").ifBlank { item.optString("uri") })
                    .takeIf { it.startsWith("https://") } ?: continue
                val title = item.optString("title").ifBlank { "Fonte consultada" }.take(180)
                if ((0 until sources.length()).none { k -> sources.optJSONObject(k)?.optString("url") == url }) {
                    sources.put(JSONObject().put("titulo", title).put("url", url))
                }
            }
        }
        return sources
    }

    private fun errorResult(message: String) =
        CoreResult(tipo = "erro", response = message, exitCode = 1, stderr = message)

    private companion object {
        const val ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
        const val MODEL = "gemini-3.8-flash"
        const val CONNECT_TIMEOUT_MS = 10_000
        const val READ_TIMEOUT_MS = 25_000
        const val SEARCH_READ_TIMEOUT_MS = 35_000
        const val MAX_ERROR_DETAIL = 320
        const val SYSTEM_INSTRUCTION =
            "Você é STACY, uma assistente pessoal em português brasileiro. " +
                "Sua postura é elegante, respeitosa, inteligente, precisa e prestativa. " +
                "Responda com clareza e sem fingir que executou ações que não foram executadas. " +
                "Quando faltar informação, declare a limitação de forma direta. " +
                "Quando uma informação atual ou verificável for necessária, utilize a busca na web e diferencie fatos de inferências."
    }
}
