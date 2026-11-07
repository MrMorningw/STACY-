package com.mrmorning.stacy

import android.database.sqlite.SQLiteDatabase
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.UUID

class StacyConversationStoreTest {

    @Test
    fun conversationsAndMessagesSurviveReopenAndDeleteOnlySelectedSession() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val name = "stacy_history_test_${UUID.randomUUID()}.db"
        try {
            val store = StacyLocalStore(context, name)
            store.addTask("Tarefa preservada")
            store.saveMemory("Memória preservada")
            val first = store.createConversation()
            val second = store.createConversation()
            store.addConversationMessage(first.id, "user", "Primeira conversa", "request-1", "completed")
            store.addConversationMessage(first.id, "assistant", "Resposta da primeira conversa", "request-1", "completed")
            store.addConversationMessage(second.id, "user", "Segunda conversa", "request-2", "pending")
            store.savePreviousInteractionId(first.id, "gemini-context-first")
            store.savePreviousInteractionId(second.id, "gemini-context-second")
            store.close()

            val reopened = StacyLocalStore(context, name)
            assertEquals(2, reopened.listConversations().size)
            assertEquals("Primeira conversa", reopened.getConversation(first.id)?.title)
            assertEquals(2, reopened.listConversationMessages(first.id).size)
            assertEquals("gemini-context-first", reopened.getPreviousInteractionId(first.id))
            assertEquals("gemini-context-second", reopened.getPreviousInteractionId(second.id))

            assertTrue("Only the selected conversation should be deleted", reopened.deleteConversation(first.id))
            assertNull(reopened.getConversation(first.id))
            assertTrue(reopened.listConversationMessages(first.id).isEmpty())
            assertNotNull(reopened.getConversation(second.id))
            assertEquals("gemini-context-second", reopened.getPreviousInteractionId(second.id))

            reopened.clearConversationHistory()
            assertTrue(reopened.listConversations().isEmpty())
            assertEquals("Tarefa preservada", reopened.listOpenTasks().single().title)
            assertEquals("Memória preservada", reopened.listMemories().single())
            reopened.close()
        } finally {
            context.deleteDatabase(name)
        }
    }

    @Test
    fun contextsCanBeInvalidatedAndConversationListLoadsInPages() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val name = "stacy_paging_test_\${UUID.randomUUID()}.db"
        try {
            val store = StacyLocalStore(context, name)
            val sessions = (1..105).map { store.createConversation() }
            sessions.forEachIndexed { index, item ->
                store.addConversationMessage(item.id, "user", "Mensagem \${index + 1}")
                store.savePreviousInteractionId(item.id, "context-\${index + 1}")
            }
            val firstPage = store.listConversations(limit = 100, offset = 0)
            val secondPage = store.listConversations(limit = 100, offset = 100)
            assertEquals(100, firstPage.size)
            assertEquals(5, secondPage.size)
            assertEquals(105, (firstPage + secondPage).map { it.id }.toSet().size)
            assertTrue(firstPage.none { candidate -> secondPage.any { it.id == candidate.id } })

            assertEquals(105, store.clearAllPreviousInteractionIds())
            assertTrue((firstPage + secondPage).all { store.getPreviousInteractionId(it.id) == null })
            store.close()
        } finally {
            context.deleteDatabase(name)
        }
    }

    @Test
    fun interruptedPendingMessagesAreMarkedWhenAppRestarts() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val name = "stacy_pending_test_\${UUID.randomUUID()}.db"
        try {
            val store = StacyLocalStore(context, name)
            val session = store.createConversation()
            store.addConversationMessage(session.id, "user", "Solicitação pendente", "pending-request", "pending")
            store.close()

            val reopened = StacyLocalStore(context, name)
            reopened.markPendingMessagesInterrupted()
            assertEquals("interrupted", reopened.listConversationMessages(session.id).single().state)
            reopened.close()
        } finally {
            context.deleteDatabase(name)
        }
    }

    @Test
    fun versionOneDatabaseMigratesWithoutLosingTasksOrMemories() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val name = "stacy_migration_test_${UUID.randomUUID()}.db"
        try {
            val file = context.getDatabasePath(name)
            file.parentFile?.mkdirs()
            SQLiteDatabase.openOrCreateDatabase(file, null).use { db ->
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
                db.execSQL("INSERT INTO tasks(title, due_hint, done, created_at) VALUES('Tarefa antiga', NULL, 0, '2026-01-01T00:00:00Z')")
                db.execSQL("INSERT INTO memories(content, created_at) VALUES('Memória antiga', '2026-01-01T00:00:00Z')")
                db.version = 1
            }

            val migrated = StacyLocalStore(context, name)
            migrated.writableDatabase
            assertEquals("Tarefa antiga", migrated.listOpenTasks().single().title)
            assertEquals("Memória antiga", migrated.listMemories().single())
            val conversation = migrated.createConversation()
            migrated.addConversationMessage(conversation.id, "user", "Mensagem após migração")
            assertEquals("Mensagem após migração", migrated.listConversationMessages(conversation.id).single().text)
            migrated.close()
        } finally {
            context.deleteDatabase(name)
        }
    }
}
