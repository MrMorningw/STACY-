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
 * Native Gemini transport. The user's key is read from Android Keystore-backed
 * storage and sent only in the HTTPS header; it is never placed in the URL or logs.
 */
internal class StacyAiClient(context: Context) {
    private val secrets = StacySecretStore(context.applicationContext)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val history = ArrayList<JSONObject>()

    fun chat(message: String, callback: (CoreResult) -> Unit) {
        executor.execute {
            val key = secrets.getGeminiApiKey()
            val result = if (key.isNullOrBlank()) {
                errorResult(
                    "Os comandos locais estão ativos, senhor, mas a IA generativa ainda não foi conectada. " +
                        "Abra Menu → Ajustes e configure uma chave Gemini API. O Termux não é necessário.",
                )
            } else {
                requestGemini(key, message)
            }
            mainHandler.post { callback(result) }
        }
    }

    fun shutdown() {
        executor.shutdownNow()
    }

    private fun requestGemini(apiKey: String, message: String): CoreResult {
        var connection: HttpURLConnection? = null
        try {
            val contents = JSONArray()
            history.forEach { contents.put(it) }
            val userMessage = JSONObject()
                .put("role", "user")
                .put("parts", JSONArray().put(JSONObject().put("text", message)))
            contents.put(userMessage)

            val payload = JSONObject()
                .put(
                    "systemInstruction",
                    JSONObject().put(
                        "parts",
                        JSONArray().put(
                            JSONObject().put(
                                "text",
                                "Você é STACY, uma assistente pessoal em português brasileiro. " +
                                    "Sua postura é elegante, respeitosa, inteligente, precisa e prestativa. " +
                                    "Responda com clareza e sem fingir que executou ações que não foram executadas. " +
                                    "Quando faltar informação, declare a limitação de forma direta.",
                            ),
                        ),
                    ),
                )
                .put("contents", contents)
                .put(
                    "generationConfig",
                    JSONObject().put("temperature", 0.65).put("maxOutputTokens", 2048),
                )

            connection = (URL(ENDPOINT).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("x-goog-api-key", apiKey)
            }

            connection.outputStream.use { stream ->
                stream.write(payload.toString().toByteArray(StandardCharsets.UTF_8))
            }

            val status = connection.responseCode
            val responseStream = if (status in 200..299) connection.inputStream else connection.errorStream
            val responseText = responseStream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
            val responseJson = try {
                JSONObject(responseText)
            } catch (_: Exception) {
                JSONObject()
            }

            if (status !in 200..299) {
                val detail = responseJson.optJSONObject("error")?.optString("message").orEmpty()
                val explanation = when (status) {
                    400 -> "A API recusou a solicitação (HTTP 400)."
                    401, 403 -> "A chave Gemini foi recusada ou não tem permissão para este modelo."
                    429 -> "A cota ou o limite de solicitações da API Gemini foi atingido."
                    else -> "A API Gemini retornou HTTP " + status + "."
                }
                val fullMessage = if (detail.isBlank()) explanation else explanation + " Detalhe: " + detail.take(MAX_ERROR_DETAIL)
                return errorResult(fullMessage)
            }

            val parts = responseJson.optJSONArray("candidates")
                ?.optJSONObject(0)
                ?.optJSONObject("content")
                ?.optJSONArray("parts")
            val answer = if (parts == null) "" else (0 until parts.length())
                .mapNotNull { index -> parts.optJSONObject(index)?.optString("text")?.takeIf { it.isNotBlank() } }
                .joinToString("\n")
                .trim()

            if (answer.isBlank()) {
                val blockReason = responseJson.optJSONObject("promptFeedback")?.optString("blockReason").orEmpty()
                return errorResult(
                    if (blockReason.isNotBlank()) {
                        "A solicitação não foi respondida pela API Gemini (motivo: " + blockReason + ")."
                    } else {
                        "A API Gemini respondeu sem conteúdo textual. Tente reformular a solicitação."
                    },
                )
            }

            history.add(userMessage)
            history.add(
                JSONObject()
                    .put("role", "model")
                    .put("parts", JSONArray().put(JSONObject().put("text", answer))),
            )
            while (history.size > MAX_HISTORY_MESSAGES) history.removeAt(0)
            return CoreResult(tipo = "resposta", response = answer, exitCode = 0, stderr = "")
        } catch (_: UnknownHostException) {
            return errorResult("Sem conexão com a internet. Os comandos locais continuam disponíveis.")
        } catch (_: SocketTimeoutException) {
            return errorResult("A IA demorou demais para responder. Verifique a conexão e tente novamente.")
        } catch (error: Exception) {
            val detail = error.message?.take(220).orEmpty()
            return errorResult(
                if (detail.isBlank()) "Não foi possível conectar à IA Gemini." else "Falha na conexão com a IA Gemini: " + detail,
            )
        } finally {
            connection?.disconnect()
        }
    }

    private fun errorResult(message: String) =
        CoreResult(tipo = "erro", response = message, exitCode = 1, stderr = message)

    private companion object {
        const val ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        const val CONNECT_TIMEOUT_MS = 15_000
        const val READ_TIMEOUT_MS = 90_000
        const val MAX_ERROR_DETAIL = 320
        const val MAX_HISTORY_MESSAGES = 12
    }
}
