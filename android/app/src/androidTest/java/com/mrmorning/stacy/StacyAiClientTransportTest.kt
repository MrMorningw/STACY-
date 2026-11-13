package com.mrmorning.stacy

import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.charset.StandardCharsets
import java.util.concurrent.CountDownLatch
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Verifies the real HTTP client against a deterministic local Interactions API stub. */
class StacyAiClientTransportTest {

    @Test
    fun expiredPreviousInteractionRetriesWithoutContextAndReturnsText() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)
        secrets.savePreviousInteractionId("expired-interaction")

        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 400,
                    body = """{"error":{"message":"previous_interaction_id not found"}}""",
                ),
                FakeResponse(
                    status = 200,
                    body = """{"id":"fresh-interaction","status":"completed","steps":[{"type":"model_output","content":[{"type":"text","text":"Resposta de teste da API."}]}]}""",
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()

        try {
            server.start()
            client.chat("Teste de transporte", useWebSearch = false) {
                result.set(it)
                latch.countDown()
            }

            assertTrue("The client did not finish the two HTTP exchanges", latch.await(10, TimeUnit.SECONDS))
            assertEquals("resposta", result.get()?.tipo)
            assertEquals("Resposta de teste da API.", result.get()?.response)

            assertEquals("A stale interaction should cause exactly one clean retry", 2, server.requests.size)
            val firstBody = server.requests[0]
            val secondBody = server.requests[1]
            assertTrue("Request must use the Interactions endpoint", firstBody.startsWith("POST /v1/interactions "))
            assertTrue("API key must be sent in the documented header", firstBody.contains("x-goog-api-key: test-only-key"))
            assertTrue("Request must declare JSON content", firstBody.contains("Content-Type: application/json"))
            assertTrue(firstBody.contains("\"previous_interaction_id\":\"expired-interaction\""))
            assertFalse(secondBody.contains("previous_interaction_id"))
            assertTrue(firstBody.contains("\"max_output_tokens\":4096"))
            assertTrue(secondBody.contains("\"max_output_tokens\":4096"))
            assertEquals("fresh-interaction", secrets.getPreviousInteractionId())
            assertEquals(null, server.failure.get())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    @Test
    fun serviceUnavailableRetriesWithRetryAfterAndReturnsOriginalResponse() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)

        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 503,
                    body = """{"error":{"message":"The model is currently experiencing high demand."}}""",
                    headers = mapOf("Retry-After" to "0"),
                ),
                FakeResponse(
                    status = 200,
                    body = """{"id":"recovered-interaction","status":"completed","output_text":"A STACY recuperou a conexão."}""",
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()
        val retryAttempts = CopyOnWriteArrayList<Int>()
        val retryStatuses = CopyOnWriteArrayList<Int>()

        try {
            server.start()
            client.chat(
                message = "Mantenha esta solicitação sem alterações.",
                useWebSearch = false,
                onRetry = { attempt, _, status ->
                    retryAttempts.add(attempt)
                    retryStatuses.add(status)
                },
            ) {
                result.set(it)
                latch.countDown()
            }

            assertTrue("The client did not recover after HTTP 503", latch.await(10, TimeUnit.SECONDS))
            assertEquals("resposta", result.get()?.tipo)
            assertEquals("A STACY recuperou a conexão.", result.get()?.response)
            assertEquals(2, server.requests.size)
            assertEquals(listOf(1), retryAttempts.toList())
            assertEquals(listOf(503), retryStatuses.toList())
            assertTrue(server.requests.all { it.contains("Mantenha esta solicitação sem alterações.") })
            assertEquals("recovered-interaction", secrets.getPreviousInteractionId())
            assertEquals(null, server.failure.get())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    @Test
    fun serviceUnavailableStopsAfterFourTotalAttempts() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)

        val server = FakeInteractionsServer(
            List(4) {
                FakeResponse(
                    status = 503,
                    body = """{"error":{"message":"The service is temporarily overloaded."}}""",
                )
            },
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()
        val retryAttempts = CopyOnWriteArrayList<Int>()

        try {
            val startedAt = System.nanoTime()
            server.start()
            client.chat(
                message = "Teste de limite de tentativas.",
                onRetry = { attempt, _, _ -> retryAttempts.add(attempt) },
            ) {
                result.set(it)
                latch.countDown()
            }

            assertTrue("The client did not stop after the retry limit", latch.await(15, TimeUnit.SECONDS))
            val elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startedAt)
            assertTrue("Retries must use bounded backoff and stay within the total 10-second deadline", elapsedMs in 2_000L..9_999L)
            assertEquals("erro", result.get()?.tipo)
            assertTrue(result.get()?.response.orEmpty().contains("4 tentativas totais"))
            assertEquals(4, server.requests.size)
            assertEquals(listOf(1, 2, 3), retryAttempts.toList())
            assertEquals(null, server.failure.get())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    @Test
    fun quotaExhausted429DoesNotRetry() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)

        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 429,
                    body = """{"error":{"message":"Quota exceeded for this API key."}}""",
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()

        try {
            server.start()
            client.chat("Teste de cota esgotada.") {
                result.set(it)
                latch.countDown()
            }

            assertTrue("The client did not return the quota error", latch.await(5, TimeUnit.SECONDS))
            assertEquals("erro", result.get()?.tipo)
            assertTrue(result.get()?.response.orEmpty().contains("HTTP 429"))
            assertEquals("Quota errors must not trigger repeated requests", 1, server.requests.size)
            assertEquals(null, server.failure.get())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    @Test
    fun connectionTestDoesNotUseOrReplaceConversationContext() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)
        secrets.savePreviousInteractionId("user-conversation-context")

        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 200,
                    body = """{"id":"health-check-context","status":"completed","output_text":"Conexão da STACY validada."}""",
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()
        try {
            server.start()
            client.testConnection {
                result.set(it)
                latch.countDown()
            }
            assertTrue("The isolated connection test did not finish", latch.await(5, TimeUnit.SECONDS))
            assertEquals("resposta", result.get()?.tipo)
            assertFalse("A health check must not carry the user's previous interaction ID", server.requests.single().contains("previous_interaction_id"))
            assertEquals("user-conversation-context", secrets.getPreviousInteractionId())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            secrets.clearPreviousInteractionId()
            server.close()
        }
    }

    @Test
    fun chatDeadlineEndsSlowResponseAndReturnsControlToTheUi() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        secrets.setGeminiFreeTierConfirmed(true)
        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 200,
                    body = """{"id":"late-interaction","status":"completed","output_text":"Resposta atrasada."}""",
                    delayBeforeResponseMs = 9_500L,
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()
        try {
            server.start()
            val startedAt = System.nanoTime()
            client.chat("Teste de limite total de espera.") {
                result.set(it)
                latch.countDown()
            }
            assertTrue("A request must return when its absolute deadline expires", latch.await(12, TimeUnit.SECONDS))
            val elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startedAt)
            assertTrue("The chat deadline should include network wait and retries (elapsed=$elapsedMs ms)", elapsedMs in 9_000L..11_500L)
            assertEquals("erro", result.get()?.tipo)
            assertTrue(result.get()?.response.orEmpty().contains("limite de 10 segundos") ||
                result.get()?.response.orEmpty().contains("prazo total"))
            assertEquals("A response received after the deadline must not replace the stored session context", null, secrets.getPreviousInteractionId())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            secrets.clearPreviousInteractionId()
            server.close()
        }
    }

    @Test
    fun externalCallsAreBlockedUntilFreeTierIsExplicitlyConfirmed() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val secrets = StacySecretStore(context)
        secrets.clearGeminiApiKey()
        secrets.saveGeminiApiKey("test-only-key")
        // Saving a new key must not implicitly authorize billable remote calls.
        assertFalse(secrets.isGeminiFreeTierConfirmed())

        val server = FakeInteractionsServer(
            listOf(
                FakeResponse(
                    status = 200,
                    body = """{"id":"must-not-be-requested","status":"completed","output_text":"Não deveria ser chamado."}""",
                ),
            ),
        )
        val client = StacyAiClient(context, server.url)
        val latch = CountDownLatch(1)
        val result = AtomicReference<CoreResult?>()
        try {
            server.start()
            client.chat("Não deve enviar requisição sem confirmação.") {
                result.set(it)
                latch.countDown()
            }
            assertTrue("The blocked request did not return", latch.await(5, TimeUnit.SECONDS))
            assertEquals("erro", result.get()?.tipo)
            assertTrue(result.get()?.response.orEmpty().contains("Modo sem custos ativos"))
            assertTrue("No HTTP request may be sent without explicit Free-tier acknowledgement", server.requests.isEmpty())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    private data class FakeResponse(
        val status: Int,
        val body: String,
        val headers: Map<String, String> = emptyMap(),
        val delayBeforeResponseMs: Long = 0L,
    )

    private class FakeInteractionsServer(
        private val responses: List<FakeResponse>,
    ) : AutoCloseable {
        private val socket = ServerSocket(0, responses.size, InetAddress.getByName("127.0.0.1"))
        val url: String = "http://127.0.0.1:${socket.localPort}/v1/interactions"
        val requests = CopyOnWriteArrayList<String>()
        val failure = AtomicReference<Throwable?>()
        private var thread: Thread? = null

        fun start() {
            thread = Thread({
                try {
                    responses.forEach { response ->
                        socket.accept().use { client ->
                            client.soTimeout = 5000
                            val input = client.getInputStream()
                            val headers = ArrayList<String>()
                            var line = readLine(input)
                            while (line.isNotEmpty()) {
                                headers.add(line)
                                line = readLine(input)
                            }

                            val contentLength = headers.firstNotNullOfOrNull { header ->
                                if (header.startsWith("Content-Length:", ignoreCase = true)) {
                                    header.substringAfter(':').trim().toIntOrNull()
                                } else null
                            } ?: 0
                            val transferChunked = headers.any {
                                it.startsWith("Transfer-Encoding:", ignoreCase = true) &&
                                    it.contains("chunked", ignoreCase = true)
                            }
                            val requestBody = if (transferChunked) {
                                readChunkedBody(input)
                            } else {
                                String(readExactly(input, contentLength), StandardCharsets.UTF_8)
                            }
                            requests.add(headers.joinToString("\n") + "\n\n" + requestBody)

                            if (response.delayBeforeResponseMs > 0L) Thread.sleep(response.delayBeforeResponseMs)
                            val responseBytes = response.body.toByteArray(StandardCharsets.UTF_8)
                            val reason = when (response.status) {
                                200 -> "OK"
                                429 -> "Too Many Requests"
                                503 -> "Service Unavailable"
                                else -> "Error"
                            }
                            val extraHeaders = response.headers.entries.joinToString(separator = "") {
                                "${it.key}: ${it.value}\r\n"
                            }
                            val responseHeaders = (
                                "HTTP/1.1 ${response.status} ${reason}\r\n" +
                                    "Content-Type: application/json; charset=UTF-8\r\n" +
                                    extraHeaders +
                                    "Content-Length: ${responseBytes.size}\r\n" +
                                    "Connection: close\r\n\r\n"
                                ).toByteArray(StandardCharsets.US_ASCII)
                            client.getOutputStream().apply {
                                write(responseHeaders)
                                write(responseBytes)
                                flush()
                            }
                        }
                    }
                } catch (error: Throwable) {
                    if (!socket.isClosed) failure.set(error)
                }
            }, "stacy-fake-interactions-api").apply { isDaemon = true }
            thread?.start()
        }

        override fun close() {
            socket.close()
            thread?.join(1000)
        }

        private fun readLine(input: InputStream): String {
            val bytes = ByteArrayOutputStream()
            while (true) {
                val value = input.read()
                if (value == -1 || value == 10) break
                if (value != 13) bytes.write(value)
            }
            return bytes.toString(StandardCharsets.UTF_8.name())
        }

        private fun readExactly(input: InputStream, size: Int): ByteArray {
            val bytes = ByteArray(size)
            var offset = 0
            while (offset < size) {
                val count = input.read(bytes, offset, size - offset)
                if (count < 0) throw IllegalStateException("Request body ended early")
                offset += count
            }
            return bytes
        }

        private fun readChunkedBody(input: InputStream): String {
            val bytes = ByteArrayOutputStream()
            while (true) {
                val sizeText = readLine(input).substringBefore(';').trim()
                val size = sizeText.toInt(16)
                if (size == 0) {
                    while (readLine(input).isNotEmpty()) Unit
                    break
                }
                bytes.write(readExactly(input, size))
                readLine(input) // chunk-ending CRLF
            }
            return bytes.toString(StandardCharsets.UTF_8.name())
        }
    }
}
