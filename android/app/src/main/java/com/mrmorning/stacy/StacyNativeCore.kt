package com.mrmorning.stacy

import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

/**
 * Lightweight, deterministic Android-side fast path.
 *
 * It handles greetings, runtime probes, and an allow-listed set of Android
 * actions locally. Unknown requests are sent to the native HTTPS AI transport.
 */
internal class StacyNativeCore(private val localStore: StacyLocalStore? = null) {

    fun process(message: String): CoreResult? {
        val normalized = normalize(message).removePrefix("stacy ").trim()
        if (normalized.isBlank()) return null

        if (isResponseProbe(normalized)) {
            return response("Estou funcionando, senhor.")
        }

        if (isDiagnosticProbe(normalized)) {
            return response(
                listOf(
                    "CORE NATIVO: ONLINE",
                    "Runtime: Kotlin / Android",
                    "Caminho: interface → ponte Android → Core Native → interface",
                    "Termux para este teste: não utilizado",
                    "IA generativa/API: não testada neste diagnóstico.",
                ).joinToString("\n"),
            )
        }

        if (normalized in GREETINGS) {
            return response("Olá, senhor. Estou funcionando pelo CORE nativo.")
        }

        routeLocalData(message, normalized)?.let { return it }

        actionFor(message, normalized)?.let { return it }

        return null
    }

    private fun routeLocalData(original: String, normalized: String): CoreResult? {
        val store = localStore
        val rawText = original.trim().replace(Regex("(?i)^stacy[,:\\s]+"), "").trim()

        val createMatch = CREATE_TASK_PATTERN.matchEntire(rawText)
        if (createMatch != null) {
            val split = splitTaskDetails(createMatch.groupValues[1].trim())
            if (split.first.isBlank()) {
                return localResponse("Diga também o nome da tarefa. Exemplo: “Crie uma tarefa: estudar contratos para amanhã às 8.”", "erro")
            }
            if (store == null) return localResponse("O armazenamento local de tarefas não está conectado.", "erro")
            val task = try { store.addTask(split.first, split.second) } catch (error: Exception) {
                return localResponse("Não consegui salvar a tarefa: " + (error.message ?: "erro local"), "erro")
            }
            val dueText = task.dueHint?.let { " Prazo anotado: $it." }.orEmpty()
            return localResponse("Tarefa \${task.id} salva no armazenamento local: “\${task.title}”.$dueText")
        }

        if (isListTasksRequest(normalized)) {
            if (store == null) return localResponse("O armazenamento local de tarefas não está conectado.", "erro")
            val tasks = store.listOpenTasks()
            return if (tasks.isEmpty()) localResponse("Não há tarefas pendentes salvas neste aparelho.")
            else localResponse("Tarefas pendentes salvas neste aparelho:\n" + tasks.joinToString("\n") { task ->
                val due = task.dueHint?.let { " — prazo: $it" }.orEmpty()
                "• [\${task.id}] \${task.title}$due"
            })
        }

        val completeMatch = COMPLETE_TASK_PATTERN.matchEntire(rawText)
        if (completeMatch != null) {
            if (store == null) return localResponse("O armazenamento local de tarefas não está conectado.", "erro")
            val query = completeMatch.groupValues[1].trim()
            val completed = try { store.completeTask(query) } catch (_: Exception) { null }
            return if (completed == null) localResponse("Não encontrei uma tarefa pendente correspondente a “$query”. Peça para listar as tarefas e use o título ou número.", "erro")
            else localResponse("Tarefa \${completed.id} marcada como concluída: “\${completed.title}”.")
        }

        val rememberMatch = REMEMBER_PATTERN.matchEntire(rawText)
        if (rememberMatch != null) {
            if (store == null) return localResponse("O armazenamento local de memória não está conectado.", "erro")
            val content = rememberMatch.groupValues[1].trim().trimEnd('.', ' ')
            if (content.isBlank()) return localResponse("Diga qual informação devo guardar na memória local.", "erro")
            return try {
                store.saveMemory(content)
                localResponse("Anotação guardada na memória local da STACY neste aparelho.")
            } catch (error: Exception) {
                localResponse("Não consegui guardar a anotação: " + (error.message ?: "erro local"), "erro")
            }
        }

        if (isListMemoryRequest(normalized)) {
            if (store == null) return localResponse("O armazenamento local de memória não está conectado.", "erro")
            val memories = store.listMemories()
            return if (memories.isEmpty()) localResponse("A memória local ainda não tem anotações explícitas.")
            else localResponse("Anotações guardadas localmente:\n" + memories.mapIndexed { index, value -> "\${index + 1}. $value" }.joinToString("\n"))
        }
        return null
    }

    private fun splitTaskDetails(value: String): Pair<String, String?> {
        val raw = value.trim().trimEnd('.', ' ')
        val dueAtStart = DUE_AT_START_PATTERN.matchEntire(raw)
        if (dueAtStart != null) return dueAtStart.groupValues[2].trim() to dueAtStart.groupValues[1].trim()
        val dueAtEnd = DUE_AT_END_PATTERN.matchEntire(raw)
        if (dueAtEnd != null) return dueAtEnd.groupValues[1].trim() to dueAtEnd.groupValues[2].trim()
        return raw to null
    }

    private fun isListTasksRequest(text: String): Boolean =
        text in LIST_TASKS_PHRASES || text.startsWith("liste minhas tarefas") ||
            text.startsWith("mostre minhas tarefas") || text.startsWith("listar tarefas") ||
            text.startsWith("mostrar tarefas") || text.startsWith("tarefas pendentes")

    private fun isListMemoryRequest(text: String): Boolean =
        text in LIST_MEMORY_PHRASES || text.startsWith("mostre minha memoria") ||
            text.startsWith("consulte a memoria local") || text.startsWith("o que voce lembra")

    private fun localResponse(text: String, type: String = "resposta") = CoreResult(
        tipo = type, response = text, exitCode = if (type == "erro") 1 else 0,
        stderr = if (type == "erro") text else "",
    )

    private fun actionFor(original: String, normalized: String): CoreResult? {
        if (normalized in OPEN_SETTINGS_PHRASES) {
            return androidAction("abrir_configuracoes")
        }

        if (normalized in OPEN_CALENDAR_PHRASES) {
            return androidAction("abrir_calendario")
        }

        if (normalized in SELECT_FILE_PHRASES) {
            return androidAction("selecionar_arquivo", mimeType = "*/*")
        }

        val openMatch = OPEN_APP_PATTERN.matchEntire(normalized)
        if (openMatch != null) {
            val target = openMatch.groupValues[1].trim()
            val app = ALLOWED_APPS[target]
            if (app != null) {
                return androidAction(
                    operation = "abrir_aplicativo",
                    packageName = app.first,
                    appName = app.second,
                )
            }
        }

        val shareMatch = SHARE_PATTERN.matchEntire(original.trim().replace(Regex("(?i)^stacy[,:\\s]+"), ""))
        if (shareMatch != null) {
            val text = shareMatch.groupValues[1].trim()
            if (text.isNotEmpty()) {
                return androidAction("compartilhar_texto", shareText = text)
            }
        }

        return null
    }

    private fun androidAction(
        operation: String,
        packageName: String? = null,
        appName: String? = null,
        shareText: String? = null,
        mimeType: String? = null,
    ): CoreResult {
        val action = JSONObject().put("acao", operation)
        if (packageName != null) action.put("pacote", packageName)
        if (appName != null) action.put("nome", appName)
        if (shareText != null) action.put("texto", shareText)
        if (mimeType != null) action.put("mime_type", mimeType)
        return CoreResult(
            tipo = "execucao",
            response = "",
            exitCode = 0,
            stderr = "",
            androidAction = action,
        )
    }

    private fun response(text: String) = CoreResult(
        tipo = "resposta",
        response = text,
        exitCode = 0,
        stderr = "",
    )

    private fun isResponseProbe(text: String): Boolean =
        text == "teste de resposta nativa" ||
            text == "teste nativo de resposta" ||
            text.contains("responda apenas estou funcionando senhor") ||
            text.contains("responda somente estou funcionando senhor")

    private fun isDiagnosticProbe(text: String): Boolean {
        val probes = listOf(
            "teste nativo",
            "teste do nucleo nativo",
            "teste de comunicacao",
            "teste de comunicacao sem termux",
            "diagnostico nativo",
            "diagnostico do core",
            "status do core nativo",
        )
        return probes.any(text::contains)
    }

    private fun normalize(value: String): String =
        Normalizer.normalize(value, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
            .replace(Regex("[^a-z0-9\\s]"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()

    private companion object {
        val GREETINGS = setOf(
            "oi",
            "ola",
            "ola stacy",
            "oi stacy",
            "bom dia",
            "bom dia stacy",
            "boa tarde",
            "boa tarde stacy",
            "boa noite",
            "boa noite stacy",
            "tudo bem",
            "como vai",
            "como esta",
        )

        val OPEN_SETTINGS_PHRASES = setOf(
            "abrir configuracoes",
            "abre configuracoes",
            "abra configuracoes",
            "abrir ajustes",
            "abre ajustes",
            "abra ajustes",
            "configuracoes do android",
            "ajustes do android",
        )

        val OPEN_CALENDAR_PHRASES = setOf(
            "abrir calendario",
            "abre calendario",
            "abra calendario",
            "abrir agenda",
            "abre agenda",
            "abra agenda",
        )

        val SELECT_FILE_PHRASES = setOf(
            "selecionar arquivo",
            "selecione arquivo",
            "escolher arquivo",
            "escolha arquivo",
            "abrir seletor de arquivos",
        )

        val CREATE_TASK_PATTERN = Regex(
            "^(?:crie|criar|adicione|adicionar|registre|registrar|lembre-me de|lembre me de)\\s+(?:(?:uma|a)\\s+)?tarefa\\s*(?::|,|-)?\\s*(.+)$",
            RegexOption.IGNORE_CASE,
        )
        val COMPLETE_TASK_PATTERN = Regex(
            "^(?:conclua|concluir|finalize|finalizar|marque como concluida|marcar como concluida)\\s+(?:a\\s+)?tarefa\\s+(.+)$",
            RegexOption.IGNORE_CASE,
        )
        val REMEMBER_PATTERN = Regex(
            "^(?:lembre(?:-se)? que|guarde na memoria(?: que)?|memorize(?: que)?|anote(?: que)?)\\s+(.+)$",
            RegexOption.IGNORE_CASE,
        )
        val DUE_AT_START_PATTERN = Regex(
            "^(?:para|até|ate)\\s+(.+?)\\s*[:,-]\\s*(.+)$",
            RegexOption.IGNORE_CASE,
        )
        val DUE_AT_END_PATTERN = Regex(
            "^(.+?)\\s+((?:para|até|ate)\\s+(?:hoje|amanhã|amanha|segunda(?:-feira)?|terça(?:-feira)?|terca(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sábado|sabado|domingo|\\d{1,2}/\\d{1,2}(?:/\\d{2,4})?)(?:\\s+(?:às|as)\\s+\\d{1,2}(?::\\d{2})?)?)\\s*$",
            RegexOption.IGNORE_CASE,
        )
        val LIST_TASKS_PHRASES = setOf(
            "liste minhas tarefas", "listar minhas tarefas", "listar tarefas",
            "mostrar minhas tarefas", "mostrar tarefas", "minhas tarefas", "tarefas pendentes",
        )
        val LIST_MEMORY_PHRASES = setOf(
            "mostre minha memoria", "mostrar memoria", "consultar memoria",
            "consulte a memoria local", "memoria da stacy", "minha memoria", "o que voce lembra sobre mim",
        )
        val OPEN_APP_PATTERN = Regex(
            "^(?:abra|abrir|abre|inicie|iniciar|execute|executar)\\s+(?:(?:o|a|os|as)\\s+)?(.+)$",
        )

        val SHARE_PATTERN = Regex(
            "^(?:compartilhar|compartilhe|compartilha)\\s*(?::|-)?\\s*(.+)$",
            RegexOption.IGNORE_CASE,
        )

        val ALLOWED_APPS = mapOf(
            "whatsapp" to ("com.whatsapp" to "WhatsApp"),
            "youtube" to ("com.google.android.youtube" to "YouTube"),
            "chrome" to ("com.android.chrome" to "Chrome"),
            "gmail" to ("com.google.android.gm" to "Gmail"),
            "spotify" to ("com.spotify.music" to "Spotify"),
            "google maps" to ("com.google.android.apps.maps" to "Google Maps"),
            "maps" to ("com.google.android.apps.maps" to "Google Maps"),
        )
    }
}
