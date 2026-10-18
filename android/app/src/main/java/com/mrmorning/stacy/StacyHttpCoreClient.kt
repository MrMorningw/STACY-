package com.mrmorning.stacy

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/** Local CORE transport with readiness checks; fallback remains owned by StacyCoreBridge. */
class StacyHttpCoreClient(private val context: Context) {
    private val executor = Executors.newCachedThreadPool()
    private val main = Handler(Looper.getMainLooper())
    private val baseUrl = "http://127.0.0.1:8765"

    @Volatile private var daemonLaunchAccepted = false

    fun startDaemon() {
        try {
            @Suppress("DEPRECATION")
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            val appVersionCode = if (Build.VERSION.SDK_INT >= 28) {
                packageInfo.longVersionCode
            } else {
                packageInfo.versionCode.toLong()
            }
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
                        APP_VERSION_CODE=$appVersionCode
                        CURRENT_APP_VERSION="${'$'}(cat "${'$'}ROOT/.stacy-core-app-version" 2>/dev/null || true)"
                        # Fast no-op when the same app version already has a healthy CORE.
                        if [ "${'$'}CURRENT_APP_VERSION" = "${'$'}APP_VERSION_CODE" ] && command -v python >/dev/null 2>&1 && python -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)); raise SystemExit(0 if d.get("ok") is True and d.get("service") == "stacy-core" else 1)' >/dev/null 2>&1; then
                            exit 0
                        fi
                        mkdir -p "${'$'}ROOT/android/termux_widget"
                        TMP="${'$'}SCRIPT.download"
                        URL="https://raw.githubusercontent.com/MrMorningw/STACY-/main/android/termux_widget/stacy-core-daemon.sh?ars=${'$'}(date +%s)"
                        if command -v curl >/dev/null 2>&1 && curl -fsSL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 1 "${'$'}URL" -o "${'$'}TMP" && test -s "${'$'}TMP"; then
                            mv "${'$'}TMP" "${'$'}SCRIPT"
                        else
                            rm -f "${'$'}TMP"
                            test -s "${'$'}SCRIPT" || { echo "STACY CORE: não foi possível obter o daemon atualizado." >&2; exit 1; }
                        fi
                        exec bash "${'$'}SCRIPT" --app-version-code=$appVersionCode
                        """.trimIndent(),
                    ),
                )
                putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home")
                putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
                putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0")
            }
            daemonLaunchAccepted = context.startService(intent) != null
        } catch (_: Exception) {
            // The UI will receive an explicit failure through the legacy bridge.
            daemonLaunchAccepted = false
        }
    }

    fun isCoreOnline(callback: (Boolean) -> Unit) {
        executor.execute {
            val online = try {
                val health = request("GET", "/health", null, 1200)
                health?.optBoolean("ok", false) == true &&
                    health.optString("service") == "stacy-core"
            } catch (_: Exception) {
                false
            }
            main.post { callback(online) }
        }
    }

    fun chat(
        message: String,
        executionId: Int,
        callback: (CoreResult) -> Unit,
        onConnectionError: () -> Unit,
    ) {
        executor.execute {
            try {
                if (!daemonLaunchAccepted) {
                    main.post(onConnectionError)
                    return@execute
                }
                val readiness = awaitCoreReady(CORE_READY_TIMEOUT_MS)
                if (!readiness.ready) {
                    val startupError = readiness.error
                    if (!startupError.isNullOrBlank()) {
                        val detail = startupError.replace('\n', ' ').take(MAX_HEALTH_ERROR_CHARS)
                        val message = "O CORE da STACY iniciou, mas não ficou saudável: $detail"
                        main.post {
                            callback(CoreResult("erro", message, 1, detail, null, null, executionId))
                        }
                    } else {
                        main.post(onConnectionError)
                    }
                    return@execute
                }

                val result = request(
                    "POST",
                    "/chat",
                    JSONObject().apply {
                        put("message", message)
                        put("executionId", executionId)
                    },
                    CORE_CHAT_TIMEOUT_MS,
                )

                if (result == null || (!result.has("tipo") && !result.has("resposta"))) {
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

    private data class CoreReadiness(
        val ready: Boolean,
        val error: String? = null,
    )

    private fun awaitCoreReady(timeoutMs: Long): CoreReadiness {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            val health = try {
                request("GET", "/health", null, HEALTH_CHECK_TIMEOUT_MS)
            } catch (_: Exception) {
                null
            }
            if (health?.optBoolean("ok", false) == true &&
                health.optString("service") == "stacy-core" &&
                health.optInt("port", 8765) == 8765
            ) {
                return CoreReadiness(ready = true)
            }

            // core_server.py exposes initialization exceptions through /health.
            // Return them immediately instead of waiting and masking them as network failure.
            if (health != null && health.optString("service") == "stacy-core") {
                val detail = health.optString("error", "").trim()
                if (!health.optBoolean("ok", false) && detail.isNotBlank() && detail != "null") {
                    return CoreReadiness(ready = false, error = detail)
                }
            }

            try {
                Thread.sleep(HEALTH_RETRY_DELAY_MS)
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                return CoreReadiness(ready = false)
            }
        }
        return CoreReadiness(ready = false)
    }

    private fun request(
        method: String,
        path: String,
        body: JSONObject?,
        timeoutMs: Int,
    ): JSONObject? {
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = timeoutMs.coerceAtMost(MAX_CONNECT_TIMEOUT_MS).coerceAtLeast(MIN_CONNECT_TIMEOUT_MS)
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
            try {
                JSONObject(text)
            } catch (_: Exception) {
                null
            }
        } finally {
            connection.disconnect()
        }
    }

    fun shutdown() {
        executor.shutdownNow()
    }

    companion object {
        private const val CORE_READY_TIMEOUT_MS = 25_000L
        private const val CORE_CHAT_TIMEOUT_MS = 45_000
        private const val HEALTH_CHECK_TIMEOUT_MS = 1000
        private const val HEALTH_RETRY_DELAY_MS = 350L
        private const val MAX_CONNECT_TIMEOUT_MS = 2000
        private const val MIN_CONNECT_TIMEOUT_MS = 500
        private const val MAX_HEALTH_ERROR_CHARS = 700
    }
}
