package com.mrmorning.stacy

import android.view.ViewGroup
import android.webkit.WebView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * Exercises the same WebView + JavaScript bridge that MainActivity uses in production.
 * It deliberately uses local CORE commands so the test does not need a network or API key.
 */
@RunWith(AndroidJUnit4::class)
class StacyWebViewBridgeTest {

    @Test
    fun nativeDiagnosticReturnsThroughProductionWebView() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "STACY WebView did not finish exposing its native bridge",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacyNativeResponse === 'function' && " +
                            "typeof window.Android === 'object' && typeof window.Android.stacySend === 'function'",
                    ) == "true"
                },
            )

            evaluate(
                webView,
                "(function(){ Android.stacySend('diagnóstico do CORE nativo'); return 'sent'; })()",
            )

            assertTrue(
                "The diagnostic request did not return to the production chat UI",
                awaitCondition(webView, timeoutMs = 8_000) {
                    evaluate(
                        webView,
                        "(function(){ var log=document.getElementById('stacyChatLog'); " +
                            "return !!log && log.innerText.includes('CORE NATIVO: ONLINE'); })()",
                    ) == "true"
                },
            )
        }
    }

    @Test
    fun missingGeminiKeyProducesVisibleAssistantErrorInsteadOfAnEmptyBubble() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                StacySecretStore(activity).clearGeminiApiKey()
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "STACY WebView or native bridge did not become ready",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacyNativeResponse === 'function' && " +
                            "typeof window.Android === 'object' && typeof window.Android.stacySend === 'function'",
                    ) == "true"
                },
            )

            evaluate(
                webView,
                "(function(){ Android.stacySend('Explique a teoria geral dos contratos'); return 'sent'; })()",
            )

            assertTrue(
                "A missing API key must produce a visible diagnostic in the chat",
                awaitCondition(webView, timeoutMs = 8_000) {
                    evaluate(
                        webView,
                        "(function(){ var log=document.getElementById('stacyChatLog'); " +
                            "return !!log && log.innerText.includes('IA generativa ainda não foi conectada'); })()",
                    ) == "true"
                },
            )
        }
    }

    private fun awaitCondition(
        webView: WebView,
        timeoutMs: Long,
        condition: () -> Boolean,
    ): Boolean {
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
        while (System.nanoTime() < deadline) {
            if (condition()) return true
            InstrumentationRegistry.getInstrumentation().waitForIdleSync()
            Thread.sleep(100)
        }
        return condition()
    }

    private fun evaluate(webView: WebView, script: String): String? {
        val result = AtomicReference<String?>()
        val latch = CountDownLatch(1)
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            webView.evaluateJavascript(script) {
                result.set(it)
                latch.countDown()
            }
        }
        if (!latch.await(3, TimeUnit.SECONDS)) return null
        return result.get()
    }
}
