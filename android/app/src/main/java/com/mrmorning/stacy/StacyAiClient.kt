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

/** Direct HTTPS Gemini transport. No Termux, localhost daemon, or Python runtime is required. */
internal class StacyAiClient(context: Context) {
    private val secrets = StacySecretStore(context.applicationContext)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    fun chat(message: String, callback: (CoreResult) -> Unit) {
        executor.execute {
            val key = secrets.getGeminiApiKey()
            val result = if (key.isNullOrBlank()) {
                errorResult("Os comandos locais estão ativos, senhor, mas a IA generativa ainda não foi conectada. Abra Menu → Ajustes e configure uma chave Gemini API. O Termux não é necessário.")
            } else {
                requestGemini(key, message)
            }
            mainHandler.post { callback(result) }
        }
    }

    fun shutdown() = executor.shutdownNow()

    private fun requestGemini(apiKey: String, message: String): CoreResult {
        var connection: HttpURLConnection? = null
        try {
            val payload = JSONObject()
                .put("model", MODEL)
                .put("input", message)
                .put("system_instruction", SYSTEM_INSTRUCTION)
                .put("generation_config", JSONObject().put("thinking_level", "low").put("max_output_tokens", 2048))
                .put("tools", JSONArray().put(JSONObject().put("type", "google_search").put("search_types", JSONArray().put("web_search"))))
                .put("store", true)

            secrets.getPreviousInteractionId()?.let { payload.put("previous_interaction_id", it) }

            connection = (URL(ENDPOINT).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("x-goog-api-key", apiKey)
            }
            connection.outputStream.use { it.write(payload.toString().toByteArray(StandardCharsets.UTF_8)) }

            val statusCode = connection.responseCode
            val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
            val raw = stream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
            val json = runCatching { JSONObject(raw) }.getOrElse { JSONObject() }

            if (statusCode !in 200..299) {
                val detail = json.optJSONObject("error")?.optString("message").orEmpty()
                val explanation = when (statusCode) {
                    400 -> "A API Gemini recusou a solicitação (HTTP 400)."
                    401, 403 -> "A chave Gemini foi recusada ou não tem permissão para este modelo."
                    404 -> "A API Gemini não encontrou o recurso solicitado. Confira o modelo e a conexão."
                    429 -> "A cota ou o limite de solicitações da API Gemini foi atingido."
                    else -> "A API Gemini retornou HTTP $statusCode."
                }
                return errorResult(if (detail.isBlank()) explanation else "$explanation Detalhe: ${detail.take(MAX_ERROR_DETAIL)}")
            }

            val answer = extractText(json)
            if (answer.isBlank()) {
                val status = json.optString("status")
                val explanation = when (status) {
                    "requires_action" -> "A IA solicitou uma ação adicional que esta versão ainda não executa."
                    "incomplete" -> "A resposta da IA ficou incompleta. Peça uma resposta mais curta ou tente novamente."
                    "failed" -> "A interação com a IA falhou. Tente novamente."
                    "queued", "in_progress" -> "A IA ainda está processando a solicitação. Tente novamente em instantes."
                    else -> "A API Gemini terminou sem devolver texto. Tente novamente."
                }
                return errorResult(explanation)
            }

            json.optString("id").takeIf { it.isNotBlank() && it != "null" }?.let(secrets::savePreviousInteractionId)
            val sources = extractSources(json.optJSONArray("steps"))
            return CoreResult("resposta", answer, 0, "", fontes = sources.takeIf { it.length() > 0 })
        } catch (_: UnknownHostException) {
            return errorResult("Sem conexão com a internet. Os comandos locais continuam disponíveis.")
        } catch (_: SocketTimeoutException) {
            return errorResult("A IA demorou demais para responder. Verifique a conexão e tente novamente.")
        } catch (error: Exception) {
            val detail = error.message?.take(MAX_ERROR_DETAIL).orEmpty()
            return errorResult(if (detail.isBlank()) "Não foi possível conectar à IA Gemini." else "Falha na conexão com a IA Gemini: $detail")
        } finally {
            connection?.disconnect()
        }
    }

    private fun extractText(response: JSONObject): String {
        val steps = response.optJSONArray("steps") ?: return ""
        val output = ArrayList<String>()
        for (i in 0 until steps.length()) {
            val step = steps.optJSONObject(i) ?: continue
            if (step.optString("type") != "model_output") continue
            val content = step.optJSONArray("content") ?: continue
            for (j in 0 until content.length()) {
                val part = content.optJSONObject(j) ?: continue
                if (part.optString("type") == "text") {
                    val text = part.optString("text")
                    if (text.isNotBlank()) output.add(text)
                }
            }
        }
        return output.joinToString("\n").trim()
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
                if ((0 until sources.length()).none { k -> sources.optJSONObject(k)?.optString("url") == url }) {
                    sources.put(JSONObject().put("titulo", title).put("url", url))
                }
            }
        }
        return sources
    }

    private fun errorResult(message: String) = CoreResult("erro", message, 1, message)

    private companion object {
        const val ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
        const val MODEL = "gemini-3.8-flash"
        const val CONNECT_TIMEOUT_MS = 10_000
        const val READ_TIMEOUT_MS = 45_000
        const val MAX_ERROR_DETAIL = 320
        const val SYSTEM_INSTRUCTION = "Você é STACY, uma assistente pessoal em português brasileiro. Sua postura é elegante, respeitosa, inteligente, precisa e prestativa. Responda com clareza e nunca finja que executou uma ação que não executou. Quando faltar informação, declare a limitação de forma direta. Quando uma informação atual ou verificável for necessária, utilize a busca na web e diferencie fatos de inferências."
    }
}
