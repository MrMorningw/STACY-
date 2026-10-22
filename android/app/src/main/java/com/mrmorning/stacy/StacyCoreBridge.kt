package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray

/** Android-native request router. No Termux, localhost daemon, or Python runtime is required. */
class StacyCoreBridge(private val context: Context) {
    private val nativeCore = StacyNativeCore()
    private val aiClient = StacyAiClient(context.applicationContext)

    fun process(message: String, onQueued: () -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return
        onQueued()
        val localResult = nativeCore.process(normalized)
        if (localResult != null) {
            CoreResultStore.publish(context, localResult)
            return
        }
        aiClient.chat(normalized) { result -> CoreResultStore.publish(context, result) }
    }

    fun testConnection(callback: (CoreResult) -> Unit) {
        aiClient.chat("Responda somente com: Conexão da STACY validada.") { callback(it) }
    }

    fun shutdown() = aiClient.shutdown()
}

data class CoreResult(
    val tipo: String,
    val response: String,
    val exitCode: Int,
    val stderr: String,
    val androidAction: Map<String, String> = emptyMap(),
    val fontes: JSONArray? = null,
    val executionId: Int = -1,
)

object CoreResultStore {
    @Volatile private var listener: ((CoreResult) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    fun subscribe(listener: (CoreResult) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, result: CoreResult, afterPublish: () -> Unit = {}) {
        mainHandler.post { try { listener?.invoke(result) } finally { afterPublish() } }
    }
}

object CorePhaseStore {
    @Volatile private var listener: ((String) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    fun subscribe(listener: (String) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, state: String) { mainHandler.post { listener?.invoke(state) } }
}
