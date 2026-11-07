package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap
import java.util.UUID

/** Android-native router. Generative requests carry an explicit conversation ID. */
class StacyCoreBridge(private val context: Context) {
    private val localStore = StacyLocalStore(context.applicationContext)
    private val nativeCore = StacyNativeCore(localStore)
    private val aiClient = StacyAiClient(context.applicationContext)
    private val busyConversations = ConcurrentHashMap.newKeySet<String>()

    fun process(message: String, conversationId: String? = null, onQueued: () -> Unit = {}) {
        val normalized = message.trim()
        if (normalized.isEmpty()) return
        val conversation = runCatching { localStore.getOrCreateConversation(conversationId) }.getOrElse {
            CoreResultStore.publish(
                context,
                CoreResult("erro", "Não foi possível abrir o histórico desta conversa: ${it.message ?: "falha no banco local"}.", 1, "Falha de persistência."),
            )
            return
        }
        if (!busyConversations.add(conversation.id)) {
            CoreResultStore.publish(
                context,
                CoreResult(
                    "erro",
                    "Já existe uma resposta em andamento nesta conversa. Aguarde a conclusão antes de enviar outra mensagem.",
                    1,
                    "Solicitação duplicada bloqueada.",
                    conversationId = conversation.id,
                ),
            )
            return
        }
        val requestId = UUID.randomUUID().toString()
        try {
            localStore.addConversationMessage(conversation.id, "user", normalized, requestId, state = "pending")
        } catch (error: Exception) {
            busyConversations.remove(conversation.id)
            CoreResultStore.publish(
                context,
                CoreResult("erro", "Não foi possível salvar sua mensagem antes do envio. A solicitação não foi enviada.", 1, error.message ?: "Falha ao persistir mensagem.", conversationId = conversation.id),
            )
            return
        }

        onQueued()
        fun deliver(raw: CoreResult, state: String) {
            val result = raw.copy(conversationId = conversation.id, requestId = requestId)
            try {
                localStore.updateMessageState(requestId, "user", if (state == "failed") "failed" else "completed")
                if (result.response.isNotBlank()) {
                    val historyText = buildString {
                        append(result.response)
                        result.fontes?.let { sources ->
                            val sourceLines = (0 until sources.length()).mapNotNull { index ->
                                val item = sources.optJSONObject(index) ?: return@mapNotNull null
                                val url = item.optString("url")
                                if (!url.startsWith("https://")) null
                                else "${item.optString("titulo", "Fonte")}
$url"
                            }
                            if (sourceLines.isNotEmpty()) append("

Fontes consultadas:
").append(sourceLines.joinToString("

"))
                        }
                    }
                    localStore.addConversationMessage(
                        conversation.id, "assistant", historyText, requestId,
                        state = if (state == "failed") "failed" else "completed",
                    )
                }
            } catch (persistenceError: Exception) {
                CoreResultStore.publish(
                    context,
                    result.copy(
                        tipo = "erro",
                        response = "A resposta chegou, mas não foi possível confirmar sua gravação no histórico local. ${persistenceError.message ?: "Falha de persistência."}",
                        exitCode = 1,
                        stderr = "Falha ao persistir a resposta.",
                    ),
                )
                busyConversations.remove(conversation.id)
                return
            }
            busyConversations.remove(conversation.id)
            CoreStatusStore.publish(context, "")
            CoreResultStore.publish(context, result)
            CorePhaseStore.publish(context, if (state == "failed") "erro" else "respondendo")
        }

        val localResult = nativeCore.process(normalized)
        if (localResult != null) {
            deliver(localResult, if (localResult.tipo.equals("erro", true)) "failed" else "completed")
            return
        }

        val useWebSearch = shouldUseWebSearch(normalized)
        CorePhaseStore.publish(context, if (useWebSearch) "pesquisando" else "pensando")
        aiClient.chat(
            message = normalized,
            conversationId = conversation.id,
            useWebSearch = useWebSearch,
            onRetry = ::publishRetryStatus,
        ) { result ->
            deliver(result, if (result.tipo.equals("erro", true) || result.tipo.equals("error", true)) "failed" else "completed")
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

    /** Health check never reads or updates a conversation's remote context. */
    fun testConnection(callback: (CoreResult) -> Unit) {
        aiClient.testConnection(callback)
    }

    fun cancelConversation(conversationId: String) {
        aiClient.cancelConversation(conversationId)
    }

    private fun publishRetryStatus(attempt: Int, delayMs: Long, statusCode: Int) {
        CoreStatusStore.publish(
            context,
            "Gemini temporariamente indisponível (HTTP $statusCode). Nova tentativa $attempt/4 em ${delayMs} ms.",
        )
    }

    fun shutdown() {
        busyConversations.clear()
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
    val conversationId: String? = null,
    val requestId: String? = null,
)

object CoreResultStore {
    @Volatile private var listener: ((CoreResult) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    fun subscribe(listener: (CoreResult) -> Unit) { this.listener = listener }
    fun clear() { listener = null }

    fun publish(context: Context, result: CoreResult, afterPublish: () -> Unit = {}) {
        mainHandler.post {
            try { listener?.invoke(result) } finally { afterPublish() }
        }
    }
}

object CorePhaseStore {
    @Volatile private var listener: ((String) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    fun subscribe(listener: (String) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, state: String) { mainHandler.post { listener?.invoke(state) } }
}

object CoreStatusStore {
    @Volatile private var listener: ((String) -> Unit)? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    fun subscribe(listener: (String) -> Unit) { this.listener = listener }
    fun clear() { listener = null }
    fun publish(context: Context, status: String) { mainHandler.post { listener?.invoke(status) } }
}
