package com.mrmorning.stacy

import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/** Fast local CORE transport. Fallback remains owned by StacyCoreBridge. */
class StacyHttpCoreClient(private val context: Context) {
    private val executor = Executors.newCachedThreadPool()
    private val main = Handler(Looper.getMainLooper())
    private val baseUrl = "http://localhost:8765"

    fun startDaemon() {
        try {
            val intent = Intent().apply {
                setClassName("com.termux", "com.termux.app.RunCommandService")
                action = "com.termux.RUN_COMMAND"
                putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
                putExtra(
                    "com.termux.RUN_COMMAND_ARGUMENTS",
                    arrayOf("-lc", "cd \"${'$'}HOME/stacy\" && bash android/termux_widget/stacy-core-daemon.sh"),
                )
                putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home")
                putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
                putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0")
            }
            context.startService(intent)
        } catch (_: Exception) {
            // The legacy bridge remains the authoritative fallback.
        }
    }

    fun isCoreOnline(callback: (Boolean) -> Unit) {
        executor.execute {
            val online = request("GET", "/health", null, 1200)?.optBoolean("ok", false) == true
            main.post { callback(online) }
        }
    }

    fun chat(message: String, callback: (CoreResult) -> Unit, onConnectionError: () -> Unit) {
        val executionId = NEXT_ID.getAndIncrement()
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
                main.post { callback(CoreResult(type, response, 0, "", action, sources)) }
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
            if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: return null
            // HTTP status alone does not determine transport health. Preserve a
            // structured STACY application response even for 4xx/5xx.
            try {
                val json = JSONObject(text)
                if (json.has("tipo") || json.has("resposta")) json else null
            } catch (_: Exception) {
                null
            }
        } finally {
            connection.disconnect()
        }
    }

    fun shutdown() { executor.shutdownNow() }

    companion object { private val NEXT_ID = AtomicInteger(10_000) }
}
