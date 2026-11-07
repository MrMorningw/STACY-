package com.mrmorning.stacy

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.Normalizer
import java.time.Instant
import java.util.Locale
import java.util.UUID

internal data class StacyTask(val id: Long, val title: String, val dueHint: String?, val done: Boolean)

internal data class StacyConversation(
    val id: String,
    val title: String,
    val createdAt: String,
    val updatedAt: String,
    val preview: String,
)

internal data class StacyConversationMessage(
    val id: String,
    val conversationId: String,
    val role: String,
    val text: String,
    val createdAt: String,
    val requestId: String?,
    val state: String,
)

internal class StacyLocalStore(
    context: Context,
    databaseName: String = "stacy_local.db",
) : SQLiteOpenHelper(context.applicationContext, databaseName, null, DATABASE_VERSION) {

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_hint TEXT,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""".trimIndent())
        db.execSQL("""CREATE TABLE memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""".trimIndent())
        db.execSQL("CREATE INDEX tasks_done_idx ON tasks(done, id DESC)")
        db.execSQL("CREATE INDEX memories_id_idx ON memories(id DESC)")
        createConversationTables(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) createConversationTables(db)
        // Future schema changes must be additive and preserve tasks/memories/history.
    }

    private fun createConversationTables(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_message_preview TEXT NOT NULL DEFAULT '',
            previous_interaction_id TEXT
        )""".trimIndent())
        db.execSQL("""CREATE TABLE IF NOT EXISTS conversation_messages (
            id TEXT PRIMARY KEY NOT NULL,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            request_id TEXT,
            state TEXT NOT NULL DEFAULT 'completed',
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )""".trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS conversations_updated_idx ON conversations(updated_at DESC)")
        db.execSQL("CREATE INDEX IF NOT EXISTS messages_conversation_idx ON conversation_messages(conversation_id, created_at, id)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS messages_request_role_idx ON conversation_messages(request_id, role) WHERE request_id IS NOT NULL")
    }

    @Synchronized
    fun createConversation(): StacyConversation {
        val now = Instant.now().toString()
        val id = UUID.randomUUID().toString()
        writableDatabase.insertOrThrow(
            "conversations", null,
            ContentValues().apply {
                put("id", id)
                put("title", "Nova conversa")
                put("created_at", now)
                put("updated_at", now)
                put("last_message_preview", "")
            },
        )
        return StacyConversation(id, "Nova conversa", now, now, "")
    }

    @Synchronized
    fun getOrCreateConversation(id: String? = null): StacyConversation {
        val candidate = id?.takeIf { it.isNotBlank() }
        if (candidate != null) getConversation(candidate)?.let { return it }
        return createConversation()
    }

    @Synchronized
    fun getConversation(id: String): StacyConversation? {
        readableDatabase.query(
            "conversations",
            arrayOf("id", "title", "created_at", "updated_at", "last_message_preview"),
            "id = ?", arrayOf(id), null, null, null, "1",
        ).use { cursor ->
            if (!cursor.moveToFirst()) return null
            return StacyConversation(
                cursor.getString(0), cursor.getString(1), cursor.getString(2),
                cursor.getString(3), cursor.getString(4),
            )
        }
    }

    @Synchronized
    fun listConversations(limit: Int = 100): List<StacyConversation> {
        val output = ArrayList<StacyConversation>()
        readableDatabase.query(
            "conversations",
            arrayOf("id", "title", "created_at", "updated_at", "last_message_preview"),
            null, null, null, null, "julianday(updated_at) DESC, id DESC",
            limit.coerceIn(1, 500).toString(),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                output.add(
                    StacyConversation(
                        cursor.getString(0), cursor.getString(1), cursor.getString(2),
                        cursor.getString(3), cursor.getString(4),
                    ),
                )
            }
        }
        return output
    }

    @Synchronized
    fun addConversationMessage(
        conversationId: String,
        role: String,
        text: String,
        requestId: String? = null,
        state: String = "completed",
    ): StacyConversationMessage {
        require(role in setOf("user", "assistant", "system")) { "Papel de mensagem inválido." }
        val cleaned = text.trim()
        require(cleaned.isNotEmpty()) { "A mensagem não pode ficar vazia." }
        require(cleaned.length <= MAX_MESSAGE_CHARS) { "A mensagem excede o limite local de armazenamento." }
        require(getConversation(conversationId) != null) { "A conversa selecionada não existe mais." }
        val id = UUID.randomUUID().toString()
        val now = Instant.now().toString()
        val database = writableDatabase
        database.beginTransaction()
        try {
            val values = ContentValues().apply {
                put("id", id)
                put("conversation_id", conversationId)
                put("role", role)
                put("text", cleaned)
                put("created_at", now)
                put("request_id", requestId)
                put("state", state)
            }
            database.insertOrThrow("conversation_messages", null, values)
            val current = getConversation(conversationId)
            val title = if (role == "user" && current?.title == "Nova conversa") {
                cleaned.replace(Regex("\\s+"), " ").take(TITLE_MAX_CHARS)
            } else current?.title ?: "Conversa"
            database.update(
                "conversations",
                ContentValues().apply {
                    put("title", title)
                    put("updated_at", now)
                    put("last_message_preview", cleaned.replace(Regex("\\s+"), " ").take(PREVIEW_MAX_CHARS))
                },
                "id = ?", arrayOf(conversationId),
            )
            database.setTransactionSuccessful()
        } finally {
            database.endTransaction()
        }
        return StacyConversationMessage(id, conversationId, role, cleaned, now, requestId, state)
    }

    @Synchronized
    fun updateMessageState(requestId: String, role: String, state: String) {
        if (requestId.isBlank() || role !in setOf("user", "assistant", "system")) return
        writableDatabase.update(
            "conversation_messages",
            ContentValues().apply { put("state", state) },
            "request_id = ? AND role = ?", arrayOf(requestId, role),
        )
    }

    @Synchronized
    fun listConversationMessages(conversationId: String, limit: Int = 500): List<StacyConversationMessage> {
        val output = ArrayList<StacyConversationMessage>()
        readableDatabase.query(
            "conversation_messages",
            arrayOf("id", "conversation_id", "role", "text", "created_at", "request_id", "state"),
            "conversation_id = ?", arrayOf(conversationId), null, null,
            "rowid DESC", limit.coerceIn(1, 2000).toString(),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                output.add(
                    StacyConversationMessage(
                        cursor.getString(0), cursor.getString(1), cursor.getString(2),
                        cursor.getString(3), cursor.getString(4),
                        cursor.getString(5), cursor.getString(6),
                    ),
                )
            }
        }
        output.reverse()
        return output
    }

    @Synchronized
    fun getPreviousInteractionId(conversationId: String): String? =
        readableDatabase.query(
            "conversations", arrayOf("previous_interaction_id"),
            "id = ?", arrayOf(conversationId), null, null, null, "1",
        ).use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0)?.takeIf { it.isNotBlank() } else null
        }

    @Synchronized
    fun savePreviousInteractionId(conversationId: String, interactionId: String?) {
        val cleaned = interactionId?.trim()?.takeIf { it.isNotEmpty() }
        writableDatabase.update(
            "conversations",
            ContentValues().apply { put("previous_interaction_id", cleaned) },
            "id = ?", arrayOf(conversationId),
        )
    }

    @Synchronized
    fun clearAllPreviousInteractionIds(): Int =
        writableDatabase.update(
            "conversations",
            ContentValues().apply { putNull("previous_interaction_id") },
            "previous_interaction_id IS NOT NULL",
            null,
        )

    @Synchronized
    fun deleteConversation(conversationId: String): Boolean =
        writableDatabase.delete("conversations", "id = ?", arrayOf(conversationId)) == 1

    @Synchronized
    fun clearConversationHistory(): Int =
        writableDatabase.delete("conversations", null, null)

    @Synchronized
    fun markPendingMessagesInterrupted() {
        writableDatabase.execSQL(
            "UPDATE conversation_messages SET state = 'interrupted' WHERE state = 'pending'",
        )
    }

    @Synchronized
    fun addTask(title: String, dueHint: String? = null): StacyTask {
        val cleanedTitle = title.trim()
        require(cleanedTitle.isNotEmpty()) { "A tarefa precisa ter um título." }
        val cleanedDue = dueHint?.trim()?.takeIf { it.isNotEmpty() }
        val values = ContentValues().apply {
            put("title", cleanedTitle)
            put("due_hint", cleanedDue)
            put("done", 0)
            put("created_at", Instant.now().toString())
        }
        val id = writableDatabase.insertOrThrow("tasks", null, values)
        return StacyTask(id, cleanedTitle, cleanedDue, false)
    }

    @Synchronized
    fun listOpenTasks(limit: Int = 30): List<StacyTask> {
        val output = ArrayList<StacyTask>()
        readableDatabase.query(
            "tasks", arrayOf("id", "title", "due_hint", "done"), "done = 0",
            null, null, null, "id DESC", limit.coerceIn(1, 100).toString(),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                output.add(StacyTask(cursor.getLong(0), cursor.getString(1), cursor.getString(2), cursor.getInt(3) != 0))
            }
        }
        return output
    }

    @Synchronized
    fun completeTask(query: String): StacyTask? {
        val sought = query.trim()
        if (sought.isEmpty()) return null
        val openTasks = listOpenTasks(100)
        val target = sought.toLongOrNull()?.let { id -> openTasks.firstOrNull { it.id == id } }
            ?: openTasks.firstOrNull { normalize(it.title) == normalize(sought) }
            ?: openTasks.firstOrNull { normalize(it.title).contains(normalize(sought)) }
            ?: return null
        val values = ContentValues().apply { put("done", 1) }
        val count = writableDatabase.update("tasks", values, "id = ? AND done = 0", arrayOf(target.id.toString()))
        return if (count == 1) target.copy(done = true) else null
    }

    @Synchronized
    fun saveMemory(content: String) {
        val cleaned = content.trim()
        require(cleaned.isNotEmpty()) { "A anotação de memória não pode ficar vazia." }
        writableDatabase.insertOrThrow(
            "memories", null,
            ContentValues().apply {
                put("content", cleaned)
                put("created_at", Instant.now().toString())
            },
        )
    }

    @Synchronized
    fun listMemories(limit: Int = 20): List<String> {
        val output = ArrayList<String>()
        readableDatabase.query(
            "memories", arrayOf("content"), null, null, null, null, "id DESC", limit.coerceIn(1, 100).toString(),
        ).use { cursor ->
            while (cursor.moveToNext()) output.add(cursor.getString(0))
        }
        return output
    }

    private fun normalize(value: String): String =
        Normalizer.normalize(value, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
            .replace(Regex("\\s+"), " ")
            .trim()

    private companion object {
        const val DATABASE_VERSION = 2
        const val MAX_MESSAGE_CHARS = 100_000
        const val TITLE_MAX_CHARS = 64
        const val PREVIEW_MAX_CHARS = 120
    }
}
