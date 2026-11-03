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
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.ThreadLocalRandom

/** Native Gemini Interactions transport. */
internal class StacyAiClient(
    context: Context,
    private val endpoint: String = ENDPOINT,
) {
    private val secrets = StacySecretStore(context.applicationContext)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    fun chat(
        message: String,
        useWebSearch: Boolean = false,
        onRetry: ((Int, Long, Int) -> Unit)? = null,
        callback: (CoreResult) -> Unit,
    ) {
        executor.execute {
            val result = try {
                val key = secrets.getGeminiApiKey()
                if (key.isNullOrBlank()) {
                    errorResult("A IA generativa ainda não está conectada. Abra Menu → Ajustes → Conectar IA e salve uma chave Gemini API válida.")
                } else requestGemini(key, message, useWebSearch, onRetry)
            } catch (error: Exception) {
                errorResult("Falha ao preparar a solicitação da IA: ${error.message ?: "erro inesperado"}")
            }
            mainHandler.post { callback(result) }
        }
    }

    fun shutdown() = executor.shutdownNow()

    private fun requestGemini(
        apiKey: String,
        message: String,
        useWebSearch: Boolean,
        onRetry: ((Int, Long, Int) -> Unit)?,
    ): CoreResult = requestGemini(
        apiKey,
        message,
        useWebSearch,
        secrets.getPreviousInteractionId(),
        requestAttempt = 1,
        retriedWithoutPreviousInteraction = false,
        onRetry = onRetry,
    )

    private fun requestGemini(
        apiKey: String,
        message: String,
        useWebSearch: Boolean,
        previousInteractionId: String?,
        requestAttempt: Int,
        retriedWithoutPreviousInteraction: Boolean,
        onRetry: ((Int, Long, Int) -> Unit)?,
    ): CoreResult {
        var connection: HttpURLConnection? = null
        try {
            val generation = JSONObject()
                .put("thinking_level", "medium")
                .put("max_output_tokens", 32768)
            val payload = JSONObject()
                .put("model", MODEL)
                .put("input", message)
                .put("system_instruction", SYSTEM_INSTRUCTION)
                .put("generation_config", generation)
                .put("store", true)

            if (useWebSearch) {
                payload.put("tools", JSONArray().put(JSONObject().put("type", "google_search")))
            }
            previousInteractionId?.takeIf { it.isNotBlank() }?.let { payload.put("previous_interaction_id", it) }

            connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = if (useWebSearch) SEARCH_READ_TIMEOUT_MS else READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("x-goog-api-key", apiKey)
            }

            connection.outputStream.use { it.write(payload.toString().toByteArray(StandardCharsets.UTF_8)) }

            val statusCode = connection.responseCode
            val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
            val responseText = stream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
            val responseJson = try { JSONObject(responseText) } catch (_: Exception) { JSONObject() }

            if (statusCode !in 200..299) {
                val detail = responseJson.optJSONObject("error")?.optString("message").orEmpty()
                if (!retriedWithoutPreviousInteraction && previousInteractionId != null && isStaleInteraction(statusCode, detail)) {
                    secrets.clearPreviousInteractionId()
                    connection.disconnect()
                    return requestGemini(
                        apiKey, message, useWebSearch, null, requestAttempt,
                        retriedWithoutPreviousInteraction = true, onRetry = onRetry,
                    )
                }

                if (requestAttempt < MAX_HTTP_ATTEMPTS && isRetryableHttpStatus(statusCode, detail)) {
                    val delayMs = calculateRetryDelayMs(connection, requestAttempt)
                    connection.disconnect()
                    runCatching { onRetry?.invoke(requestAttempt, delayMs, statusCode) }
                    try {
                        if (delayMs > 0L) Thread.sleep(delayMs)
                    } catch (_: InterruptedException) {
                        Thread.currentThread().interrupt()
                        return errorResult("A tentativa automática de conexão com a IA foi interrompida. Tente novamente.")
                    }
                    return requestGemini(
                        apiKey, message, useWebSearch, previousInteractionId, requestAttempt + 1,
                        retriedWithoutPreviousInteraction, onRetry,
                    )
                }

                val explanation = when (statusCode) {
                    400 -> "A API Gemini recusou a solicitação (HTTP 400)."
                    401, 403 -> "A chave Gemini foi recusada ou não tem permissão para este modelo."
                    404 -> "A API Gemini não encontrou o recurso solicitado (HTTP 404)."
                    408 -> "A API Gemini demorou para responder (HTTP 408)."
                    429 -> "A API Gemini atingiu um limite de uso ou cota (HTTP 429)."
                    503 -> "A API Gemini está temporariamente sobrecarregada (HTTP 503)."
                    in 500..599 -> "A API Gemini apresentou uma instabilidade temporária (HTTP $statusCode)."
                    else -> "A API Gemini retornou HTTP $statusCode."
                }
                val retryNote = if (requestAttempt > 1 && statusCode in 500..599) {
                    " A STACY realizou $requestAttempt tentativas automáticas."
                } else ""
                return errorResult(
                    if (detail.isBlank()) "$explanation$retryNote"
                    else "$explanation$retryNote Detalhe: ${detail.take(MAX_ERROR_DETAIL)}",
                )
            }

            val answer = extractText(responseJson)
            if (answer.isBlank()) {
                val status = responseJson.optString("status")
                return errorResult(when (status) {
                    "requires_action" -> "A API solicitou uma ação adicional que esta versão da STACY ainda não executa."
                    "incomplete" -> "A resposta da IA ficou incompleta. Tente novamente com uma solicitação mais curta."
                    "in_progress", "queued" -> "A solicitação da IA ainda está em processamento. Tente novamente em instantes."
                    else -> "A API Gemini concluiu sem devolver texto."
                })
            }

            responseJson.optString("id").takeIf { it.isNotBlank() && it != "null" }?.let(secrets::savePreviousInteractionId)
            return CoreResult(
                tipo = "resposta",
                response = answer,
                exitCode = 0,
                stderr = "",
                fontes = extractSources(responseJson.optJSONArray("steps")).takeIf { it.length() > 0 },
            )
        } catch (_: UnknownHostException) {
            return errorResult("Sem conexão com a internet. Os comandos locais continuam disponíveis.")
        } catch (_: SocketTimeoutException) {
            return errorResult("A IA demorou mais de ${if (useWebSearch) SEARCH_READ_TIMEOUT_MS / 1000 else READ_TIMEOUT_MS / 1000}s para responder. Verifique a conexão e tente novamente.")
        } catch (error: Exception) {
            return errorResult("Falha na conexão com a IA Gemini: ${(error.message ?: "erro inesperado").take(MAX_ERROR_DETAIL)}")
        } finally {
            connection?.disconnect()
        }
    }

    private fun isRetryableHttpStatus(statusCode: Int, detail: String): Boolean {
        if (statusCode == 408 || statusCode in 500..599) return true
        if (statusCode != 429) return false

        val normalized = detail.lowercase(Locale.ROOT)
        val quotaFailure = listOf("quota", "billing", "prepay", "daily limit", "per day")
            .any(normalized::contains)
        val transientRateLimit = listOf(
            "rate limit", "rate_limit", "too many requests",
            "requests per minute", "requests per second", "rate exceeded",
        ).any(normalized::contains)
        return transientRateLimit && !quotaFailure
    }

    private fun calculateRetryDelayMs(connection: HttpURLConnection, failedAttempt: Int): Long {
        val retryAfter = connection.getHeaderField("Retry-After")?.trim()
        val retryAfterSeconds = retryAfter?.toLongOrNull()?.takeIf { it >= 0L }
        val retryAfterDateMs = if (retryAfterSeconds == null && !retryAfter.isNullOrBlank()) {
            runCatching {
                ZonedDateTime.parse(retryAfter, DateTimeFormatter.RFC_1123_DATE_TIME)
                    .toInstant().toEpochMilli() - System.currentTimeMillis()
            }.getOrNull()?.coerceAtLeast(0L)
        } else null
        val serverDelayMs = retryAfterSeconds?.let { it.coerceAtMost(MAX_RETRY_DELAY_MS / 1000L) * 1000L }
            ?: retryAfterDateMs?.coerceAtMost(MAX_RETRY_DELAY_MS)
        val exponent = (failedAttempt - 1).coerceIn(0, 10)
        val exponentialDelayMs = (INITIAL_RETRY_DELAY_MS * (1L shl exponent)).coerceAtMost(MAX_RETRY_DELAY_MS)
        val baseDelayMs = (serverDelayMs ?: exponentialDelayMs).coerceIn(0L, MAX_RETRY_DELAY_MS)
        val jitterMs = ThreadLocalRandom.current().nextLong(0L, RETRY_JITTER_MAX_MS + 1L)
        return baseDelayMs + jitterMs
    }

    private fun isStaleInteraction(statusCode: Int, detail: String): Boolean {
        if (statusCode != 400 && statusCode != 404) return false
        val text = detail.lowercase(Locale.ROOT)
        return text.contains("previous_interaction_id") ||
            (text.contains("interaction") && listOf("not found", "expired", "unknown").any(text::contains))
    }

    private fun extractText(response: JSONObject): String {
        response.optString("output_text").takeIf { it.isNotBlank() }?.let { return it.trim() }
        val steps = response.optJSONArray("steps") ?: response.optJSONArray("output") ?: response.optJSONArray("outputs") ?: return ""
        val parts = ArrayList<String>()
        for (i in 0 until steps.length()) {
            val step = steps.optJSONObject(i) ?: continue
            val type = step.optString("type")
            if (type.isNotBlank() && type !in setOf("model_output", "text", "output_text")) continue
            step.optString("text").takeIf { it.isNotBlank() }?.let { parts.add(it) }
            val content = step.optJSONArray("content") ?: continue
            for (j in 0 until content.length()) {
                val part = content.optJSONObject(j) ?: continue
                if (part.optString("type").let { it.isBlank() || it == "text" }) {
                    part.optString("text").takeIf { it.isNotBlank() }?.let { parts.add(it) }
                }
            }
        }
        return parts.joinToString("\n").trim()
    }

    private fun extractSources(steps: JSONArray?): JSONArray {
        val sources = JSONArray()
        if (steps == null) return sources
        for (i in 0 until steps.length()) {
            val step = steps.optJSONObject(i) ?: continue
            if (step.optString("type") != "google_search_result") continue
            val results = step.optJSONArray("result") ?: continue
            for (j in 0 until results.length()) {
                val item = results.optJSONObject(j) ?: continue
                val url = item.optString("url").ifBlank { item.optString("uri") }
                if (!url.startsWith("https://")) continue
                val title = item.optString("title").ifBlank { "Fonte consultada" }.take(180)
                if ((0 until sources.length()).none { sources.optJSONObject(it)?.optString("url") == url }) {
                    sources.put(JSONObject().put("titulo", title).put("url", url))
                }
            }
        }
        return sources
    }

    private fun errorResult(message: String) = CoreResult(tipo = "erro", response = message, exitCode = 1, stderr = message)

    private companion object {
        const val ENDPOINT = "https://generativelanguage.googleapis.com/v1/interactions"
        const val MODEL = "gemini-3.8-flash"
        const val CONNECT_TIMEOUT_MS = 10_000
        const val READ_TIMEOUT_MS = 45_000
        const val SEARCH_READ_TIMEOUT_MS = 60_000
        const val MAX_ERROR_DETAIL = 320
        const val MAX_HTTP_ATTEMPTS = 4
        const val INITIAL_RETRY_DELAY_MS = 1_000L
        const val MAX_RETRY_DELAY_MS = 8_000L
        const val RETRY_JITTER_MAX_MS = 250L
        const val SYSTEM_INSTRUCTION = "Você é STACY, uma assistente pessoal em português brasileiro. Sua postura é elegante, respeitosa, inteligente, precisa e prestativa. Responda com clareza e sem fingir que executou ações que não foram executadas. Quando faltar informação, declare a limitação de forma direta. Quando uma informação atual ou verificável for necessária, utilize a busca na web e diferencie fatos de inferências."
    }
}
