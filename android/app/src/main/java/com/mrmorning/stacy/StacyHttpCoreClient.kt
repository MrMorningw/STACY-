package com.mrmorning.stacy

import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/** Fast local CORE transport. It never owns fallback decisions; callers do. */
class StacyHttpCoreClient {
    private val executor = Executors.newCachedThreadPool()
    private val main = Handler(Looper.getMainLooper())
    private val baseUrl = "http://localhost:8765"

    fun isCoreOnline(callback: (Boolean) -> Unit) {
        executor.execute {
            val online = request("GET", "/health", null, 1200)?.optBoolean("ok", false) == true
            main.post { callback(online) }
        }
    }

    fun chat(message: String, executionId: Int, callback: (CoreResult) -> Unit, onConnectionError: () -> Unit) {
        executor.execute {
            try {
                val body = JSONObject().apply {
                    put("message", message)
                    put("executionId", executionId)
                }
                val result = request("POST", "/chat", body, 45_000)
                if (result == null) {
                    main.post(onConnectionError)
                    return@execute
                }
                val type = result.optString("tipo", "resposta")
                val response = result.optString("resposta", "")
                val action = result.optJSONObject("acao_android")
                val sources = result.optJSONArray("fontes")
                main.post {
                    callback(CoreResult(type, response, 0, "", action, sources))
                }
            } catch (_: Exception) {
                main.post(onConnectionError)
            }
        }
    }

    private fun request(method: String, path: String, body: JSONObject?, timeoutMs: Int): JSONObject? {
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 1200
            readTimeout = timeoutMs
            useCaches = false
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        return try {
            if (body != null) {
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: return null
            if (code !in 200..299) return null
            JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    fun shutdown() {
        executor.shutdownNow()
    }
}
