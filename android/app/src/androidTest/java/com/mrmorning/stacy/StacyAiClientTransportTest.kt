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
            assertTrue(firstBody.contains("\"previous_interaction_id\":\"expired-interaction\""))
            assertFalse(secondBody.contains("previous_interaction_id"))
            assertTrue(firstBody.contains("\"max_output_tokens\":32768"))
            assertTrue(secondBody.contains("\"max_output_tokens\":32768"))
            assertEquals("fresh-interaction", secrets.getPreviousInteractionId())
            assertEquals(null, server.failure.get())
        } finally {
            client.shutdown()
            secrets.clearGeminiApiKey()
            server.close()
        }
    }

    private data class FakeResponse(val status: Int, val body: String)

    private class FakeInteractionsServer(
        private val responses: List<FakeResponse>,
    ) : AutoCloseable {
        private val socket = ServerSocket(0, responses.size, InetAddress.getByName("127.0.0.1"))
        val url: String = "http://127.0.0.1:${socket.localPort}/v1beta/interactions"
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

                            val responseBytes = response.body.toByteArray(StandardCharsets.UTF_8)
                            val reason = if (response.status in 200..299) "OK" else "Bad Request"
                            val responseHeaders = (
                                "HTTP/1.1 ${response.status} ${reason}\r\n" +
                                    "Content-Type: application/json; charset=UTF-8\r\n" +
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
