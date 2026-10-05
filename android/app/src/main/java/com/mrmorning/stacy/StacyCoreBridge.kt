package com.mrmorning.stacy

import android.app.PendingIntent
import android.content.Context
import android.content.pm.PackageManager
import android.content.Intent
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

class StacyCoreBridge(private val context: Context) {
    fun process(message: String, onQueued: () -> Unit = {}, onError: (String) -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return
        if (context.packageManager.getPackageInfoOrNull("com.termux") == null) {
            onError("O núcleo STACY precisa do Termux instalado para executar o CORE Python.")
            return
        }
        val executionId = NEXT_ID.getAndIncrement()
        val callback = Intent(context, StacyCoreResultReceiver::class.java).apply {
            putExtra(StacyCoreResultReceiver.EXTRA_EXECUTION_ID, executionId)
        }
        val flags = PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_UPDATE_CURRENT or
            if (android.os.Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0
        val pendingIntent = PendingIntent.getBroadcast(context, executionId, callback, flags)
        val intent = Intent().apply {
            setClassName("com.termux", "com.termux.app.RunCommandService")
            action = "com.termux.RUN_COMMAND"
            putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
            putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arrayOf(
                "/data/data/com.termux/files/home/stacy/android/termux_widget/stacy-android.sh",
                normalized,
            ))
            putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home/stacy")
            putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
            putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0")
            putExtra("com.termux.RUN_COMMAND_PENDING_INTENT", pendingIntent)
        }
        callbacks[executionId] = onError
        try {
            context.startService(intent)
            onQueued()
        } catch (_: SecurityException) {
            callbacks.remove(executionId)
            onError("Conceda à STACY a permissão para executar comandos no ambiente Termux.")
        } catch (erro: Exception) {
            callbacks.remove(executionId)
            onError("Não foi possível acionar o CORE: ${erro.message ?: "erro desconhecido"}.")
        }
    }

    companion object {
        private val NEXT_ID = AtomicInteger(1000)
        private val callbacks = ConcurrentHashMap<Int, (String) -> Unit>()
        fun fail(executionId: Int, message: String) {
            callbacks.remove(executionId)?.invoke(message)
        }
    }
}

data class CoreResult(
    val tipo: String,
    val response: String,
    val exitCode: Int,
    val stderr: String,
)

object CoreResultStore {
    private var listener: ((CoreResult) -> Unit)? = null
    fun subscribe(listener: (CoreResult) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, result: CoreResult) {
        context.mainExecutor.execute { listener?.invoke(result) }
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
