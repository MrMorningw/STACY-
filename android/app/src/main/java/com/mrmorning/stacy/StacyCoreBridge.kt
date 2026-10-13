package com.mrmorning.stacy

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
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
    private var activeExecutionId: Int? = null

    fun process(message: String, onQueued: () -> Unit = {}, onError: (String) -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return
        if (context.packageManager.getPackageInfoOrNull("com.termux") == null) {
            onError("O núcleo STACY precisa do Termux instalado para executar o CORE Python.")
            return
        }

        synchronized(queue) {
            queue.addLast(Request(normalized, onQueued, onError))
        }
        onQueued()
        startNext()
    }

    private fun startNext() {
        val request: Request
        val executionId: Int
        synchronized(queue) {
            if (activeExecutionId != null || queue.isEmpty()) return
            request = queue.removeFirst()
            executionId = NEXT_ID.getAndIncrement()
            activeExecutionId = executionId
            callbacks[executionId] = request.onError
            activeBridges[executionId] = this
        }

        try {
            val callback = Intent(context, StacyCoreResultReceiver::class.java).apply {
                putExtra(StacyCoreResultReceiver.EXTRA_EXECUTION_ID, executionId)
            }
            val flags = PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_UPDATE_CURRENT or
                if (android.os.Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0
            val pendingIntent = PendingIntent.getBroadcast(context, executionId, callback, flags)
            val command = """
                ROOT="${'$'}HOME/stacy"
                if [ ! -d "${'$'}ROOT" ] || [ ! -f "${'$'}ROOT/android/termux_widget/stacy-android.sh" ]; then
                  printf '%s\n' '{"tipo":"erro","resposta":"O núcleo Python não foi encontrado em ~/stacy. Instale o repositório STACY no Termux e tente novamente."}'
                  exit 0
                fi
                if ! command -v python >/dev/null 2>&1; then
                  printf '%s\n' '{"tipo":"erro","resposta":"O Python não está instalado no Termux. Instale Python e tente novamente."}'
                  exit 0
                fi
                if ! python -c 'import requests' >/dev/null 2>&1; then
                  printf '%s\n' '{"tipo":"erro","resposta":"Falta uma dependência do núcleo. No Termux, execute: python -m pip install -r requirements.txt"}'
                  exit 0
                fi
                cd "${'$'}ROOT"
                exec bash "${'$'}ROOT/android/termux_widget/stacy-android.sh" "${'$'}1"
            """.trimIndent()
            val intent = Intent().apply {
                setClassName("com.termux", "com.termux.app.RunCommandService")
                action = "com.termux.RUN_COMMAND"
                putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
                putExtra(
                    "com.termux.RUN_COMMAND_ARGUMENTS",
                    arrayOf("-lc", command, "stacy-android", request.message),
                )
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
        synchronized(queue) {
            if (activeExecutionId == executionId) activeExecutionId = null
        }
        startNext()
    }

    companion object {
        private val NEXT_ID = AtomicInteger(1000)
        private val callbacks = ConcurrentHashMap<Int, (String) -> Unit>()
        private val activeBridges = ConcurrentHashMap<Int, StacyCoreBridge>()

        fun fail(executionId: Int, message: String) {
            val bridge = activeBridges.remove(executionId)
            callbacks.remove(executionId)?.invoke(message)
            bridge?.finish(executionId)
        }

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
)

object CoreResultStore {
    @Volatile private var listener: ((CoreResult) -> Unit)? = null
    fun subscribe(listener: (CoreResult) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, result: CoreResult, afterPublish: () -> Unit = {}) {
        context.mainExecutor.execute {
            try {
                listener?.invoke(result)
            } finally {
                afterPublish()
            }
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
