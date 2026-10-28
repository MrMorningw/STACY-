package com.mrmorning.stacy

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.Normalizer
import java.time.Instant
import java.util.Locale

internal data class StacyTask(val id: Long, val title: String, val dueHint: String?, val done: Boolean)

internal class StacyLocalStore(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "stacy_local.db", null, 1) {

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
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Keep user data; future schema changes must use explicit additive migrations.
    }

    @Synchronized
    fun healthCheck(): Boolean = try {
        readableDatabase.rawQuery("SELECT 1", null).use { cursor ->
            cursor.moveToFirst() && cursor.getInt(0) == 1
        }
    } catch (_: Exception) {
        false
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
}
