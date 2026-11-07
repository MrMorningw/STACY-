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
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Future
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture

/** Bounded Gemini Interactions transport with per-conversation context and absolute deadlines. */
internal class StacyAiClient(
    context: Context,
    private val endpoint: String = ENDPOINT,
) {
    private val appContext = context.applicationContext
    private val secrets = StacySecretStore(appContext)
    private val localStore = StacyLocalStore(appContext)
    private val executor = ThreadPoolExecutor(
        WORKER_COUNT, WORKER_COUNT, 0L, TimeUnit.MILLISECONDS,
        ArrayBlockingQueue(MAX_QUEUED_REQUESTS),
        { runnable -> Thread(runnable, "stacy-gemini-worker").apply { isDaemon = true } },
        ThreadPoolExecutor.AbortPolicy(),
    )
    private val deadlineExecutor = Executors.newSingleThreadScheduledExecutor { runnable ->
        Thread(runnable, "stacy-gemini-deadlines").apply { isDaemon = true }
    }
    private val mainHandler = Handler(Looper.getMainLooper())
    private val activeRequests = ConcurrentHashMap<String, PendingRequest>()

    private class PendingRequest(
        val conversationId: String,
        val deadlineNanos: Long,
        val callback: (CoreResult) -> Unit,
    ) {
        val completed = AtomicBoolean(false)
        val connection = AtomicReference<HttpURLConnection?>(null)
        @Volatile var future: Future<*>? = null
        @Volatile var deadlineFuture: ScheduledFuture<*>? = null
    }

    /** Backward-compatible entry point retained for transport tests and older callers. */
    fun chat(
        message: String,
        useWebSearch: Boolean = false,
        onRetry: ((Int, Long, Int) -> Unit)? = null,
        callback: (CoreResult) -> Unit,
    ) = chat(message, LEGACY_CONVERSATION_ID, useWebSearch, onRetry, callback)

    /** Production entry point; context is isolated by the local conversation ID. */
    fun chat(
        message: String,
        conversationId: String,
        useWebSearch: Boolean = false,
        onRetry: ((Int, Long, Int) -> Unit)? = null,
        callback: (CoreResult) -> Unit,
    ) {
        val cleaned = message.trim()
        if (cleaned.isEmpty()) {
            post(callback, errorResult("A mensagem está vazia."))
            return
        }
        if (conversationId.isBlank()) {
            post(callback, errorResult("Não foi possível identificar a conversa atual."))
            return
        }
        val budgetMs = if (useWebSearch) SEARCH_DEADLINE_MS else CHAT_DEADLINE_MS
        submitRequest(conversationId, budgetMs, callback) { request ->
            val key = secrets.getGeminiApiKey()
            if (key.isNullOrBlank()) {
                errorResult("A IA generativa ainda não está conectada. Abra Menu → Ajustes → Conectar IA e salve uma chave Gemini API válida.")
            } else {
                val priorId = if (conversationId == LEGACY_CONVERSATION_ID) {
                    secrets.getPreviousInteractionId()
                } else {
                    localStore.getPreviousInteractionId(conversationId)
                }
                requestGemini(key, cleaned, useWebSearch, conversationId, priorId, true, request, onRetry)
            }
        }
    }

    /** Real authenticated generation; does not read or mutate any conversation context. */
    fun testConnection(callback: (CoreResult) -> Unit) {
        submitRequest(TEST_CONVERSATION_ID, CONNECTION_DEADLINE_MS, callback) { request ->
            val key = secrets.getGeminiApiKey()
            if (key.isNullOrBlank()) {
                errorResult("Nenhuma chave Gemini API está salva neste aparelho.")
            } else {
                requestGemini(
                    apiKey = key,
                    message = "Responda somente com: Conexão da STACY validada.",
                    useWebSearch = false,
                    conversationId = TEST_CONVERSATION_ID,
                    previousInteractionId = null,
                    saveInteraction = false,
                    pending = request,
                    onRetry = null,
                )
            }
        }
    }

    fun cancelConversation(conversationId: String) {
        activeRequests[conversationId]?.let { request ->
            request.connection.getAndSet(null)?.disconnect()
            request.future?.cancel(true)
            finish(request, errorResult("A solicitação foi cancelada."))
        }
    }

    private fun submitRequest(
        conversationId: String,
        budgetMs: Long,
        callback: (CoreResult) -> Unit,
        work: (PendingRequest) -> CoreResult,
    ) {
        val request = PendingRequest(
            conversationId = conversationId,
            deadlineNanos = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(budgetMs),
            callback = callback,
        )
        if (activeRequests.putIfAbsent(conversationId, request) != null) {
            post(callback, errorResult("Já existe uma solicitação em andamento nesta conversa. Aguarde a resposta antes de enviar outra."))
            return
        }

        request.deadlineFuture = deadlineExecutor.schedule({
            request.connection.getAndSet(null)?.disconnect()
            request.future?.cancel(true)
            finish(
                request,
                errorResult(
                    if (conversationId == TEST_CONVERSATION_ID) {
                        "O teste da conexão Gemini excedeu ${budgetMs / 1000}s."
                    } else if (budgetMs == SEARCH_DEADLINE_MS) {
                        "A pesquisa excedeu o limite de espera. Tente novamente."
                    } else {
                        "A conversa excedeu o limite de 10 segundos. A rede ou o serviço Gemini pode estar lento; tente novamente."
                    },
                ),
            )
        }, budgetMs, TimeUnit.MILLISECONDS)

        try {
            request.future = executor.submit {
                val result = try {
                    if (remainingMs(request) <= 0L) {
                        errorResult("A solicitação expirou enquanto aguardava disponibilidade do núcleo.")
                    } else {
                        work(request)
                    }
                } catch (_: InterruptedException) {
                    Thread.currentThread().interrupt()
                    errorResult("A solicitação foi interrompida.")
                } catch (error: Exception) {
                    errorResult("Falha ao preparar a solicitação da IA: ${(error.message ?: "erro inesperado").take(MAX_ERROR_DETAIL)}")
                }
                finish(request, result)
            }
        } catch (_: java.util.concurrent.RejectedExecutionException) {
            request.deadlineFuture?.cancel(false)
            finish(request, errorResult("O núcleo está ocupado. Aguarde alguns segundos e tente novamente."))
        }
    }

    private fun finish(request: PendingRequest, result: CoreResult) {
        if (!request.completed.compareAndSet(false, true)) return
        request.deadlineFuture?.cancel(false)
        request.connection.getAndSet(null)?.disconnect()
        activeRequests.remove(request.conversationId, request)
        mainHandler.post { request.callback(result) }
    }

    private fun post(callback: (CoreResult) -> Unit, result: CoreResult) {
        mainHandler.post { callback(result) }
    }

    private fun remainingMs(request: PendingRequest): Long =
        TimeUnit.NANOSECONDS.toMillis(request.deadlineNanos - System.nanoTime()).coerceAtLeast(0L)

    private fun requestGemini(
        apiKey: String,
        message: String,
        useWebSearch: Boolean,
        conversationId: String,
        previousInteractionId: String?,
        saveInteraction: Boolean,
        pending: PendingRequest,
        onRetry: ((Int, Long, Int) -> Unit)?,
    ): CoreResult {
        var attempt = 1
        var activePreviousInteractionId = previousInteractionId
        var retriedWithoutPreviousInteraction = false
        while (remainingMs(pending) > MIN_ATTEMPT_BUDGET_MS && !Thread.currentThread().isInterrupted) {
            var connection: HttpURLConnection? = null
            try {
                val generation = JSONObject()
                    .put("thinking_level", if (useWebSearch) "medium" else "low")
                    .put("max_output_tokens", if (useWebSearch) 8192 else 4096)
                val payload = JSONObject()
                    .put("model", MODEL)
                    .put("input", message)
                    .put("system_instruction", SYSTEM_INSTRUCTION)
                    .put("generation_config", generation)
                    .put("store", true)

                if (useWebSearch) {
                    payload.put("tools", JSONArray().put(JSONObject().put("type", "google_search")))
                }
                activePreviousInteractionId?.takeIf { it.isNotBlank() }?.let {
                    payload.put("previous_interaction_id", it)
                }

                val remaining = remainingMs(pending).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
                connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = minOf(CONNECT_TIMEOUT_MS, remaining).coerceAtLeast(1)
                    readTimeout = minOf(if (useWebSearch) SEARCH_READ_TIMEOUT_MS else READ_TIMEOUT_MS, remaining).coerceAtLeast(1)
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                    setRequestProperty("Accept", "application/json")
                    setRequestProperty("x-goog-api-key", apiKey)
                }
                pending.connection.set(connection)
                if (remainingMs(pending) <= 0L) return errorResult("O prazo da solicitação expirou antes do envio.")
                connection.outputStream.use { it.write(payload.toString().toByteArray(StandardCharsets.UTF_8)) }

                val statusCode = connection.responseCode
                val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
                val responseText = stream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
                val responseJson = try { JSONObject(responseText) } catch (_: Exception) { JSONObject() }

                if (statusCode !in 200..299) {
                    val detail = responseJson.optJSONObject("error")?.optString("message").orEmpty()
                    if (!retriedWithoutPreviousInteraction && activePreviousInteractionId != null &&
                        isStaleInteraction(statusCode, detail)
                    ) {
                        if (conversationId == LEGACY_CONVERSATION_ID) secrets.clearPreviousInteractionId()
                        else localStore.savePreviousInteractionId(conversationId, null)
                        activePreviousInteractionId = null
                        retriedWithoutPreviousInteraction = true
                        connection.disconnect()
                        pending.connection.compareAndSet(connection, null)
                        if (remainingMs(pending) < MIN_ATTEMPT_BUDGET_MS) break
                        continue
                    }

                    if (attempt < MAX_HTTP_ATTEMPTS && isRetryableHttpStatus(statusCode, detail)) {
                        val delayMs = calculateRetryDelayMs(connection, attempt)
                        connection.disconnect()
                        pending.connection.compareAndSet(connection, null)
                        if (remainingMs(pending) <= delayMs + MIN_ATTEMPT_BUDGET_MS) {
                            return httpError(statusCode, detail, attempt)
                        }
                        runCatching { onRetry?.invoke(attempt, delayMs, statusCode) }
                        try {
                            Thread.sleep(delayMs)
                        } catch (_: InterruptedException) {
                            Thread.currentThread().interrupt()
                            return errorResult("A tentativa automática de conexão com a IA foi interrompida.")
                        }
                        attempt++
                        continue
                    }
                    return httpError(statusCode, detail, attempt)
                }

                val status = responseJson.optString("status")
                if (status.isNotBlank() && status !in setOf("completed", "succeeded")) {
                    return errorResult(when (status) {
                        "requires_action" -> "A API solicitou uma ação adicional que esta versão da STACY ainda não executa."
                        "incomplete" -> "A resposta da IA ficou incompleta. Tente novamente com uma solicitação mais curta."
                        "in_progress", "queued" -> "A API aceitou a solicitação, mas ainda não concluiu a resposta. Tente novamente em instantes."
                        else -> "A API Gemini retornou um estado não concluído ($status)."
                    })
                }
                val answer = extractText(responseJson)
                if (answer.isBlank()) return errorResult("A API Gemini concluiu sem devolver texto utilizável.")

                val interactionId = responseJson.optString("id").takeIf { it.isNotBlank() && it != "null" }
                if (saveInteraction && !interactionId.isNullOrBlank()) {
                    if (conversationId == LEGACY_CONVERSATION_ID) secrets.savePreviousInteractionId(interactionId)
                    else localStore.savePreviousInteractionId(conversationId, interactionId)
                }
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
                if (remainingMs(pending) <= 0L) break
                return errorResult("O tempo de conexão com a IA expirou. Verifique a rede e tente novamente.")
            } catch (error: Exception) {
                if (Thread.currentThread().isInterrupted) {
                    return errorResult("A solicitação foi interrompida.")
                }
                return errorResult("Falha na conexão com a IA Gemini: ${(error.message ?: "erro inesperado").take(MAX_ERROR_DETAIL)}")
            } finally {
                pending.connection.compareAndSet(connection, null)
                connection?.disconnect()
            }
        }
        return errorResult("O prazo total da solicitação terminou. Tente novamente.")
    }

    private fun httpError(statusCode: Int, detail: String, attempts: Int): CoreResult {
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
        val retryNote = if (attempts > 1) " A STACY realizou $attempts tentativas totais." else ""
        return errorResult(if (detail.isBlank()) "$explanation$retryNote" else "$explanation$retryNote Detalhe: ${detail.take(MAX_ERROR_DETAIL)}")
    }

    private fun isRetryableHttpStatus(statusCode: Int, detail: String): Boolean {
        if (statusCode == 408 || statusCode in 500..599) return true
        if (statusCode != 429) return false
        val normalized = detail.lowercase(Locale.ROOT)
        val quotaFailure = listOf("quota", "billing", "prepay", "daily limit", "per day").any(normalized::contains)
        val transientRateLimit = listOf(
            "rate limit", "rate_limit", "too many requests",
            "requests per minute", "requests per second", "rate exceeded",
        ).any(normalized::contains)
        return transientRateLimit && !quotaFailure
    }

    private fun calculateRetryDelayMs(connection: HttpURLConnection, failedAttempt: Int): Long {
        val retryAfter = connection.getHeaderField("Retry-After")?.trim()
        val seconds = retryAfter?.toLongOrNull()?.takeIf { it >= 0L }
        val dateDelay = if (seconds == null && !retryAfter.isNullOrBlank()) {
            runCatching {
                ZonedDateTime.parse(retryAfter, DateTimeFormatter.RFC_1123_DATE_TIME)
                    .toInstant().toEpochMilli() - System.currentTimeMillis()
            }.getOrNull()?.coerceAtLeast(0L)
        } else null
        val serverDelay = seconds?.let { it.coerceAtMost(MAX_RETRY_DELAY_MS / 1000L) * 1000L }
            ?: dateDelay?.coerceAtMost(MAX_RETRY_DELAY_MS)
        val exponent = (failedAttempt - 1).coerceIn(0, 10)
        val backoff = (INITIAL_RETRY_DELAY_MS * (1L shl exponent)).coerceAtMost(MAX_RETRY_DELAY_MS)
        val base = (serverDelay ?: backoff).coerceIn(0L, MAX_RETRY_DELAY_MS)
        return base + java.util.concurrent.ThreadLocalRandom.current().nextLong(0L, RETRY_JITTER_MAX_MS + 1L)
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

    private fun errorResult(message: String) =
        CoreResult(tipo = "erro", response = message, exitCode = 1, stderr = message)

    fun shutdown() {
        activeRequests.values.toList().forEach { request ->
            request.connection.getAndSet(null)?.disconnect()
            request.future?.cancel(true)
            finish(request, errorResult("A solicitação foi interrompida porque o núcleo foi encerrado."))
        }
        executor.shutdownNow()
        deadlineExecutor.shutdownNow()
        localStore.close()
    }

    private companion object {
        const val ENDPOINT = "https://generativelanguage.googleapis.com/v1/interactions"
        const val MODEL = "gemini-3.8-flash"
        const val CONNECT_TIMEOUT_MS = 5_000
        const val READ_TIMEOUT_MS = 8_000
        const val SEARCH_READ_TIMEOUT_MS = 55_000
        const val MAX_ERROR_DETAIL = 320
        const val MAX_HTTP_ATTEMPTS = 4
        const val INITIAL_RETRY_DELAY_MS = 350L
        const val MAX_RETRY_DELAY_MS = 2_000L
        const val RETRY_JITTER_MAX_MS = 150L
        const val CHAT_DEADLINE_MS = 10_000L
        const val SEARCH_DEADLINE_MS = 60_000L
        const val CONNECTION_DEADLINE_MS = 8_000L
        const val MIN_ATTEMPT_BUDGET_MS = 500L
        const val WORKER_COUNT = 3
        const val MAX_QUEUED_REQUESTS = 24
        const val LEGACY_CONVERSATION_ID = "__legacy_default__"
        const val TEST_CONVERSATION_ID = "__connection_test__"
        const val SYSTEM_INSTRUCTION = "Você é STACY, uma assistente pessoal em português brasileiro. Sua postura é elegante, respeitosa, inteligente, precisa e prestativa. Responda com clareza e sem fingir que executou ações que não foram executadas. Quando faltar informação, declare a limitação de forma direta. Quando uma informação atual ou verificável for necessária, utilize a busca na web e diferencie fatos de inferências."
    }
}
