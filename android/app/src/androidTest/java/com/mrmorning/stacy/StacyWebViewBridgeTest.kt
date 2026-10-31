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

/** Verifies that the production WebView reports the detached CORE state honestly. */
@RunWith(AndroidJUnit4::class)
class StacyWebViewBridgeTest {

    @Test
    fun unconfiguredCoreReturnsVisibleDiagnosticInsteadOfCallingLegacyCore() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "STACY scene did not expose animation control",
                awaitCondition(webView, 12_000) {
                    evaluate(webView, "typeof window.stacySetAnimationsEnabled === 'function'") == "true"
                },
            )
            evaluate(webView, "window.stacySetAnimationsEnabled(false)")

            assertTrue(
                "STACY WebView or native bridge did not become ready",
                awaitCondition(webView, 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacyNativeResponse === 'function' && " +
                            "typeof window.Android === 'object' && typeof window.Android.stacySend === 'function'",
                    ) == "true"
                },
            )

            evaluate(
                webView,
                "(function(){ " +
                    "var input=document.getElementById('message'); " +
                    "var send=document.getElementById('send'); " +
                    "if(!input || !send) return 'missing-composer'; " +
                    "input.value='Olá, STACY'; send.click(); return 'sent'; " +
                "})()",
            )

            assertTrue(
                "The detached provider must return an explicit diagnostic in the production chat",
                awaitCondition(webView, 8_000) {
                    evaluate(
                        webView,
                        "(function(){ var log=document.getElementById('stacyChatLog'); " +
                            "return !!log && log.innerText.includes('Nenhum núcleo de inteligência está conectado'); })()",
                    ) == "true"
                },
            )
        }
    }

    private fun awaitCondition(webView: WebView, timeoutMs: Long, condition: () -> Boolean): Boolean {
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
        while (System.nanoTime() < deadline) {
            if (condition()) return true
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
