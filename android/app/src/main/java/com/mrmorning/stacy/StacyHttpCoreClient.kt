package com.mrmorning.stacy

import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

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
                    arrayOf(
                        "-lc",
                        """
                        set -u
                        ROOT="${'$'}HOME/stacy"
                        SCRIPT="${'$'}ROOT/android/termux_widget/stacy-core-daemon.sh"
                        mkdir -p "${'$'}ROOT/android/termux_widget"
                        TMP="${'$'}SCRIPT.download"
                        URL="https://raw.githubusercontent.com/MrMorningw/STACY-/main/android/termux_widget/stacy-core-daemon.sh?ars=${'$'}(date +%s)"
                        if command -v curl >/dev/null 2>&1 && curl -fsSL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 1 "${'$'}URL" -o "${'$'}TMP" && test -s "${'$'}TMP"; then
                            mv "${'$'}TMP" "${'$'}SCRIPT"
                        else
                            rm -f "${'$'}TMP"
                            test -s "${'$'}SCRIPT" || { echo "STACY CORE: não foi possível obter o daemon atualizado." >&2; exit 1; }
                        fi
                        exec bash "${'$'}SCRIPT"
                        """.trimIndent(),
                    ),
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
                main.post { callback(CoreResult(type, response, 0, "", action, sources, executionId)) }
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
}
