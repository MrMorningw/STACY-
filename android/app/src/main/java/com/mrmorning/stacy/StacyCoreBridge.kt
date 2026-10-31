package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject

/**
 * Application-facing facade. It knows only the provider contract, never a
 * specific intelligence engine, API vendor, Python runtime, or local daemon.
 */
class StacyCoreBridge(
    private val context: Context,
    private val provider: StacyCoreProvider = StacyCoreProviderFactory.create(context.applicationContext),
) {
    fun process(message: String, onQueued: () -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return

        onQueued()
        CorePhaseStore.publish(context, "pensando")
        try {
            provider.process(normalized) { result ->
                CoreResultStore.publish(context, result)
                CorePhaseStore.publish(
                    context,
                    if (result.tipo.equals("erro", ignoreCase = true) || result.tipo.equals("error", ignoreCase = true)) "erro" else "respondendo",
                )
            }
        } catch (error: Exception) {
            publishProviderFailure(error)
        }
    }

    fun testConnection(callback: (CoreResult) -> Unit) {
        try {
            provider.testConnection(callback)
        } catch (error: Exception) {
            callback(
                CoreResult(
                    tipo = "erro",
                    response = "Falha ao testar o núcleo conectado: ${error.message ?: "erro inesperado"}",
                    exitCode = 1,
                    stderr = error.message.orEmpty(),
                ),
            )
        }
    }

    private fun publishProviderFailure(error: Exception) {
        val result = CoreResult(
            tipo = "erro",
            response = "O núcleo conectado falhou ao processar a solicitação: ${error.message ?: "erro inesperado"}",
            exitCode = 1,
            stderr = error.message.orEmpty(),
        )
        CoreResultStore.publish(context, result)
        CorePhaseStore.publish(context, "erro")
    }

    fun shutdown() {
        provider.shutdown()
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
    private val mainHandler = Handler(Looper.getMainLooper())

    fun subscribe(listener: (CoreResult) -> Unit) {
        this.listener = listener
    }

    fun clear() {
        listener = null
    }

    fun publish(context: Context, result: CoreResult, afterPublish: () -> Unit = {}) {
        mainHandler.post {
            try {
                listener?.invoke(result)
            } finally {
                afterPublish()
            }
        }
    }
}

object CorePhaseStore {
    @Volatile private var listener: ((String) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    fun subscribe(listener: (String) -> Unit) {
        this.listener = listener
    }

    fun clear() {
        listener = null
    }

    fun publish(context: Context, state: String) {
        mainHandler.post { listener?.invoke(state) }
    }
}
