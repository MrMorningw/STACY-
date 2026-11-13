package com.mrmorning.stacy

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap
import java.util.UUID
import java.util.concurrent.TimeUnit

/** Android-native router. Generative requests carry an explicit conversation ID. */
class StacyCoreBridge(private val context: Context) {
    private val localStore = StacyLocalStore(context.applicationContext)
    private val nativeCore = StacyNativeCore(localStore)
    private val aiClient = StacyAiClient(context.applicationContext)
    private val busyConversations = ConcurrentHashMap.newKeySet<String>()

    fun process(message: String, conversationId: String? = null, onQueued: () -> Unit = {}) {
        val requestStartedNanos = System.nanoTime()
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
        var requestProfile = "local"
        var useWebSearch = false
        fun deliver(raw: CoreResult, state: String) {
            val verdict = StacyGrillSupervisor.review(
                request = normalized,
                candidate = raw,
                requiresExternalEvidence = useWebSearch,
            )
            val reviewedRaw = if (verdict.approved) {
                raw
            } else {
                Log.w(
                    "StacyGrill",
                    "decision=VETO risk=${verdict.risk} findings=${verdict.findings.joinToString("|")}",
                )
                CoreResult(
                    tipo = "erro",
                    response = "A GRILL interrompeu a entrega porque não foi possível validar a integridade ou a segurança do resultado. Nenhuma ação bloqueada foi executada.",
                    exitCode = 1,
                    stderr = verdict.findings.joinToString("; "),
                )
            }
            if (verdict.approved) {
                Log.i("StacyGrill", "decision=APPROVE risk=${verdict.risk}")
            }
            val effectiveState = if (verdict.approved) state else "failed"
            val result = reviewedRaw.copy(conversationId = conversation.id, requestId = requestId)
            val persistenceStartedNanos = System.nanoTime()
            try {
                localStore.updateMessageState(requestId, "user", if (effectiveState == "failed") "failed" else "completed")
                if (result.response.isNotBlank()) {
                    val historyText = buildString {
                        append(result.response)
                        result.fontes?.let { sources ->
                            val sourceLines = (0 until sources.length()).mapNotNull { index ->
                                val item = sources.optJSONObject(index) ?: return@mapNotNull null
                                val url = item.optString("url")
                                if (!url.startsWith("https://")) null
                                else "${item.optString("titulo", "Fonte")}\n$url"
                            }
                            if (sourceLines.isNotEmpty()) append("\n\nFontes consultadas:\n").append(sourceLines.joinToString("\n\n"))
                        }
                    }
                    localStore.addConversationMessage(
                        conversation.id, "assistant", historyText, requestId,
                        state = if (effectiveState == "failed") "failed" else "completed",
                    )
                }
            } catch (persistenceError: Exception) {
                runCatching { localStore.updateMessageState(requestId, "user", "failed") }
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
            val persistMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - persistenceStartedNanos)
            val totalMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - requestStartedNanos)
            CoreResultStore.publish(context, result) {
                Log.i(
                    "StacyCoreMetrics",
                    "profile=$requestProfile total_ms=$totalMs history_persist_ms=$persistMs outcome=${if (effectiveState == "failed") "error" else "success"}",
                )
            }
            CorePhaseStore.publish(context, if (effectiveState == "failed") "erro" else "respondendo")
        }

        val localResult = nativeCore.process(normalized)
        if (localResult != null) {
            deliver(localResult, if (localResult.tipo.equals("erro", true)) "failed" else "completed")
            return
        }

        useWebSearch = StacyRequestClassifier.requiresWebSearch(normalized)
        requestProfile = if (useWebSearch) "research" else "chat"
        val budgetMs = if (useWebSearch) SEARCH_DEADLINE_MS else CHAT_DEADLINE_MS
        val absoluteDeadlineNanos = requestStartedNanos + TimeUnit.MILLISECONDS.toNanos(budgetMs)
        CorePhaseStore.publish(context, if (useWebSearch) "pesquisando" else "pensando")
        aiClient.chat(
            message = normalized,
            conversationId = conversation.id,
            useWebSearch = useWebSearch,
            onRetry = ::publishRetryStatus,
            absoluteDeadlineNanos = absoluteDeadlineNanos,
        ) { result ->
            deliver(result, if (result.tipo.equals("erro", true) || result.tipo.equals("error", true)) "failed" else "completed")
        }
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

    private companion object {
        const val CHAT_DEADLINE_MS = 10_000L
        const val SEARCH_DEADLINE_MS = 60_000L
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

internal object StacyRequestClassifier {
    private val explicitResearchIntents = listOf(
        "pesquise na web", "pesquise na internet", "pesquisa na web", "pesquisa na internet",
        "pesquise sobre", "pesquise fontes", "busque na web", "busque na internet",
        "procure na web", "procure na internet", "fontes externas", "referencias atuais",
        "noticias de hoje", "ultimas noticias", "onde assistir",
    )
    private val currentSignals = listOf(
        "hoje", "agora", "atualmente", "atual", "mais recente", "mais recentes",
        "ultima versao", "ultimo lancamento", "ultimas", "neste momento",
        "este ano", "em 2026",
    )
    private val currentTopics = listOf(
        "noticia", "preco", "cotacao", "taxa", "clima", "tempo", "placar",
        "resultado", "evento", "lancamento", "versao", "atualizacao",
        "presidente", "governador", "prefeito", "legislacao", "lei",
        "horario", "disponibilidade", "estoque", "mercado", "jogo",
        "partida", "eleicao", "pesquisa eleitoral",
    )

    fun requiresWebSearch(message: String): Boolean {
        val normalized = Normalizer.normalize(message, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
        if (explicitResearchIntents.any(normalized::contains)) return true
        return currentSignals.any(normalized::contains) &&
            currentTopics.any(normalized::contains)
    }
}
