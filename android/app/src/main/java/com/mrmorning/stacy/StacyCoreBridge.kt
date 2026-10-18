package com.mrmorning.stacy

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject
import java.util.ArrayDeque
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

class StacyCoreBridge(private val context: Context) {
    private data class Request(
        val message: String,
        val onQueued: () -> Unit,
        val onError: (String) -> Unit,
    )

    private val queue = ArrayDeque<Request>()
    private val timeoutHandler = Handler(Looper.getMainLooper())
    private val pendingTimeouts = ConcurrentHashMap<Int, Runnable>()
    private var activeExecutionId: Int? = null
    private val httpCore = StacyHttpCoreClient(context)

    init { httpCore.startDaemon() }

    fun process(message: String, onQueued: () -> Unit = {}, onError: (String) -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return
        synchronized(queue) { queue.addLast(Request(normalized, onQueued, onError)) }
        onQueued()
        startNext()
    }

    private fun startNext() {
        val next = synchronized(queue) {
            if (activeExecutionId != null || queue.isEmpty()) return
            val request = queue.removeFirst()
            val executionId = NEXT_ID.getAndIncrement()
            activeExecutionId = executionId
            callbacks[executionId] = request.onError
            activeBridges[executionId] = this
            request to executionId
        }
        val request = next.first
        val executionId = next.second
        val timeout = Runnable {
            fail(executionId, "O CORE não devolveu resposta em 90 segundos. Verifique o Termux, o repositório ~/stacy e tente novamente.")
        }
        pendingTimeouts[executionId] = timeout
        timeoutHandler.postDelayed(timeout, CORE_TIMEOUT_MS)

        httpCore.chat(
            message = request.message,
            executionId = executionId,
            callback = { result ->
                if (!isExecutionActive(executionId)) return@chat
                CoreResultStore.publish(context, result) { complete(executionId) }
            },
            onConnectionError = {
                if (isExecutionActive(executionId)) startLegacy(request.message, executionId)
            },
        )
    }

    private fun startLegacy(message: String, executionId: Int) {
        try {
            val callback = Intent(context, StacyCoreResultReceiver::class.java).apply {
                putExtra(StacyCoreResultReceiver.EXTRA_EXECUTION_ID, executionId)
            }
            val resultMutability = if (android.os.Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0
            val flags = PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_UPDATE_CURRENT or resultMutability
            val pendingIntent = PendingIntent.getBroadcast(context, executionId, callback, flags)
            val command = """
                ROOT="${'$'}HOME/stacy"
                if [ ! -d "${'$'}ROOT" ] || [ ! -f "${'$'}ROOT/android/termux_widget/stacy-android.sh" ]; then
                  printf '%s\n' '{"tipo":"erro","resposta":"O núcleo Python não foi encontrado em ~/stacy."}'
                  exit 0
                fi
                if ! command -v python >/dev/null 2>&1; then
                  printf '%s\n' '{"tipo":"erro","resposta":"O Python não está instalado no Termux."}'
                  exit 0
                fi
                cd "${'$'}ROOT"
                exec bash "${'$'}ROOT/android/termux_widget/stacy-android.sh" "${'$'}@"
            """.trimIndent()
            val intent = Intent().apply {
                setClassName("com.termux", "com.termux.app.RunCommandService")
                action = "com.termux.RUN_COMMAND"
                putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
                putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arrayOf("-lc", command, "stacy-android", "--execution-id=$executionId", message))
                putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home")
                putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
                putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0")
                putExtra("com.termux.RUN_COMMAND_PENDING_INTENT", pendingIntent)
            }
            context.startService(intent)
        } catch (_: SecurityException) {
            fail(executionId, "Permita que aplicativos externos executem comandos no Termux e tente novamente.")
        } catch (error: Exception) {
            fail(executionId, "Não foi possível acionar o CORE: ${error.message ?: "erro desconhecido"}.")
        }
    }

    private fun finish(executionId: Int) {
        pendingTimeouts.remove(executionId)?.let(timeoutHandler::removeCallbacks)
        synchronized(queue) { if (activeExecutionId == executionId) activeExecutionId = null }
        startNext()
    }

    fun shutdown() { httpCore.shutdown() }

    companion object {
        private const val CORE_TIMEOUT_MS = 90_000L
        private val NEXT_ID = AtomicInteger(1000)
        private val callbacks = ConcurrentHashMap<Int, (String) -> Unit>()
        private val activeBridges = ConcurrentHashMap<Int, StacyCoreBridge>()

        fun fail(executionId: Int, message: String) {
            val bridge = activeBridges.remove(executionId)
            callbacks.remove(executionId)?.invoke(message)
            bridge?.finish(executionId)
        }

        fun isExecutionActive(executionId: Int): Boolean = activeBridges.containsKey(executionId)

        fun complete(executionId: Int) {
            callbacks.remove(executionId)
            activeBridges.remove(executionId)?.finish(executionId)
        }
    }
}

data class CoreResult(
    val tipo: String,
    val response: String,
    val exitCode: Int,
    val stderr: String,
    val androidAction: JSONObject? = null,
    val fontes: JSONArray? = null,
    val executionId: Int = -1,
)

object CoreResultStore {
    @Volatile private var listener: ((CoreResult) -> Unit)? = null
    fun subscribe(listener: (CoreResult) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, result: CoreResult, afterPublish: () -> Unit = {}) {
        context.mainExecutor.execute {
            try { listener?.invoke(result) } finally { afterPublish() }
        }
    }
}

private fun PackageManager.getPackageInfoOrNull(packageName: String): android.content.pm.PackageInfo? =
    try {
        if (android.os.Build.VERSION.SDK_INT >= 33) getPackageInfo(packageName, PackageManager.PackageInfoFlags.of(0))
        else {
            @Suppress("DEPRECATION")
            getPackageInfo(packageName, 0)
        }
    } catch (_: PackageManager.NameNotFoundException) { null }
