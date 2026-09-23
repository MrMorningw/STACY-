package com.mrmorning.stacy

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class StacyApiResponse(
    val text: String,
    val topic: StacyTopic? = null,
)

enum class StacyTopic(
    val title: String,
    val icon: String,
) {
    ATIVIDADE_FACULDADE("Atividade Faculdade", "🎓"),
    ESTUDOS_FACULDADE("Estudos Faculdade", "📚"),
    ESTUDOS_DP("Estudos DP", "🚀"),
    PESQUISAS_EXTERNAS("Pesquisas Externas", "🔎"),
    AGENDA("Compromissos / Agenda", "📅"),
    COMANDOS("Comandos", "⚡"),
    CONFIGURACOES("Configurações", "⚙️"),
}

object StacyApi {
    private const val BASE_URL = "http://127.0.0.1:8765"
    private const val TIMEOUT_MS = 8_000

    fun health(): Boolean =
        try {
            val connection = openConnection("/health", "GET")
            connection.inputStream.bufferedReader().use { it.readText() }
            connection.disconnect()
            true
        } catch (_: Exception) {
            false
        }

    fun send(message: String): StacyApiResponse {
        val connection = openConnection("/chat", "POST")
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")

        val body = JSONObject()
            .put("mensagem", message)
            .toString()

        connection.outputStream.use { output ->
            output.write(body.toByteArray(Charsets.UTF_8))
        }

        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream
        }

        val raw = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
        connection.disconnect()

        if (raw.isBlank()) {
            throw IllegalStateException("STACY CORE não retornou uma resposta.")
        }

        val root = JSONObject(raw)
        if (!root.optBoolean("ok", false)) {
            throw IllegalStateException(
                root.optString("erro", "Erro desconhecido no STACY CORE."),
            )
        }

        val resultado = root.optJSONObject("resultado")
            ?: throw IllegalStateException("Resposta do STACY CORE está incompleta.")

        val resposta = resultado.optString("resposta").trim()
        if (resposta.isEmpty()) {
            throw IllegalStateException("STACY CORE não retornou texto.")
        }

        return StacyApiResponse(
            text = resposta,
            topic = inferTopic(resultado),
        )
    }

    private fun inferTopic(resultado: JSONObject): StacyTopic? {
        return when (resultado.optString("rota")) {
            "pesquisa_externa" -> StacyTopic.PESQUISAS_EXTERNAS
            "interno" -> StacyTopic.COMANDOS
            else -> null
        }
    }

    private fun openConnection(path: String, method: String): HttpURLConnection {
        return (URL(BASE_URL + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            useCaches = false
        }
    }
}
