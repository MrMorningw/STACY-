package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

/**
 * Android-native request router.
 * Deterministic commands are answered locally. General conversation uses HTTPS
 * directly from this app; this request path starts no Python daemon or secondary server.
 */
class StacyCoreBridge(private val context: Context) {
    private val localStore = StacyLocalStore(context.applicationContext)
    private val nativeCore = StacyNativeCore(localStore)
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

        val useWebSearch = shouldUseWebSearch(normalized)
        CorePhaseStore.publish(context, if (useWebSearch) "pesquisando" else "pensando")
        aiClient.chat(normalized, useWebSearch) { result ->
            CorePhaseStore.publish(
                context,
                if (result.tipo.equals("erro", ignoreCase = true) || result.tipo.equals("error", ignoreCase = true)) "erro" else "respondendo",
            )
            CoreResultStore.publish(context, result)
        }
    }

    private fun shouldUseWebSearch(message: String): Boolean {
        val normalized = Normalizer.normalize(message, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
        val webIntents = listOf(
            "pesquise", "pesquisar", "pesquisa na web", "pesquisa na internet",
            "busque na web", "procure na internet", "na internet", "na web",
            "noticias", "hoje", "atualmente", "agora", "mais recente", "ultimas",
            "ultimo", "ultima", "preco", "cotacao", "onde assistir", "fontes",
            "referencias", "situacao atual", "quem e o atual", "pesquise sobre",
        )
        return webIntents.any(normalized::contains)
    }

    fun testConnection(callback: (CoreResult) -> Unit) {
        aiClient.chat("Responda somente com: Conexão da STACY validada.") { result ->
            callback(result)
        }
    }

    fun shutdown() {
        aiClient.shutdown()
        localStore.close()
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
