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

            // Pause the test scene before asserting the bridge. If bridge
            // initialization fails, ActivityScenario must still be able to close
            // the production Activity without a perpetual requestAnimationFrame loop.
            assertTrue(
                "STACY scene did not expose animation control",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(webView, "typeof window.stacySetAnimationsEnabled === 'function'") == "true"
                },
            )
            evaluate(webView, "window.stacySetAnimationsEnabled(false)")
            evaluate(webView, "window.stacyNativeCoreStatus('Gemini indisponível. Tentativa automática 1/4.')")
            assertTrue(
                "Retry status must be visible in the existing STACY information line",
                evaluate(
                    webView,
                    "document.getElementById('infoText').innerText.includes('Tentativa automática 1/4')",
                ) == "true",
            )
            evaluate(webView, "window.stacyNativeCoreStatus('')")


            assertTrue(
                "STACY WebView did not finish exposing its native bridge",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacyNativeResponse === 'function' && " +
                            "typeof window.stacyNativeCoreStatus === 'function' && " +
                            "typeof window.Android === 'object' && typeof window.Android.stacySend === 'function'",
                    ) == "true"
                },
            )

            armJavascriptDiagnostics(webView)
            val submitSnapshot = evaluate(
                webView,
                "(function(){ " +
                    "var input=document.getElementById('message'); " +
                    "var send=document.getElementById('send'); " +
                    "if(!input || !send) return 'missing-composer'; " +
                    "input.value='diagnóstico do CORE nativo'; " +
                    "send.click(); " +
                    "return JSON.stringify({value:input.value,pending:!!document.getElementById('stacyPendingReply')," +
                    "chat:document.getElementById('stacyChatLog') ? document.getElementById('stacyChatLog').innerText : ''}); " +
                "})()",
            )
            val returned = awaitCondition(webView, timeoutMs = 8_000) {
                evaluate(
                    webView,
                    "(function(){ var log=document.getElementById('stacyChatLog'); " +
                        "return !!log && log.innerText.includes('CORE NATIVO: ONLINE'); })()",
                ) == "true"
            }
            val diagnostics = if (returned) "" else webViewSnapshot(webView)
            assertTrue(
                "The diagnostic request did not return to the production chat UI. " +
                    "Submit=$submitSnapshot; DOM=$diagnostics",
                returned,
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
                "STACY scene did not expose animation control",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(webView, "typeof window.stacySetAnimationsEnabled === 'function'") == "true"
                },
            )
            evaluate(webView, "window.stacySetAnimationsEnabled(false)")

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

            armJavascriptDiagnostics(webView)
            val submitSnapshot = evaluate(
                webView,
                "(function(){ " +
                    "var input=document.getElementById('message'); " +
                    "var send=document.getElementById('send'); " +
                    "if(!input || !send) return 'missing-composer'; " +
                    "input.value='Explique a teoria geral dos contratos'; " +
                    "send.click(); " +
                    "return JSON.stringify({value:input.value,pending:!!document.getElementById('stacyPendingReply')," +
                    "chat:document.getElementById('stacyChatLog') ? document.getElementById('stacyChatLog').innerText : ''}); " +
                "})()",
            )
            val returned = awaitCondition(webView, timeoutMs = 8_000) {
                evaluate(
                    webView,
                    "(function(){ " +
                        "var log=document.getElementById('stacyChatLog'); " +
                        "var replies=log ? log.querySelectorAll('.stacy-chat-row.assistant .stacy-chat-bubble') : []; " +
                        "return replies.length === 1 && " +
                        "replies[0].innerText.includes('IA generativa ainda não está conectada') && " +
                        "!log.innerText.includes('Não foi possível concluir. Verifique a conexão da IA ou tente novamente.'); " +
                    "})()",
                ) == "true"
            }
            val diagnostics = if (returned) "" else webViewSnapshot(webView)
            assertTrue(
                "A missing API key must produce one real diagnostic bubble. " +
                    "Submit=$submitSnapshot; DOM=$diagnostics",
                returned,
            )
        }
    }

    private fun armJavascriptDiagnostics(webView: WebView) {
        evaluate(
            webView,
            "(function(){ " +
                "window.__stacyTestErrors=[];window.__stacyTestClickObserved=0; " +
                "window.addEventListener('error',function(e){window.__stacyTestErrors.push(String(e.message||e.error||'unknown JS error'));}); " +
                "window.addEventListener('unhandledrejection',function(e){window.__stacyTestErrors.push(String(e.reason||'unhandled rejection'));}); " +
                "var send=document.getElementById('send'); " +
                "if(send)send.addEventListener('click',function(){window.__stacyTestClickObserved++;},true); " +
                "return 'armed'; " +
            "})()",
        )
    }

    private fun webViewSnapshot(webView: WebView): String =
        evaluate(
            webView,
            "(function(){ " +
                "var log=document.getElementById('stacyChatLog'); " +
                "var input=document.getElementById('message'); " +
                "var status=document.getElementById('status'); " +
                "var bubble=document.getElementById('responseBubble'); " +
                "return JSON.stringify({bridge:window.Android ? typeof window.Android.stacySend : 'missing'," +
                "nativeResponse:typeof window.stacyNativeResponse,clicks:window.__stacyTestClickObserved||0," +
                "input:input ? input.value : null,pending:!!document.getElementById('stacyPendingReply')," +
                "chat:log ? log.innerText : '',status:status ? status.innerText : null," +
                "response:bubble ? bubble.innerText : null,appClass:document.getElementById('app') ? document.getElementById('app').className : null," +
                "errors:window.__stacyTestErrors||[]});" +
            "})()",
        ) ?: "<WebView did not return a diagnostic snapshot>"

    private fun awaitCondition(
        webView: WebView,
        timeoutMs: Long,
        condition: () -> Boolean,
    ): Boolean {
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
        while (System.nanoTime() < deadline) {
            if (condition()) return true
            // The production scene continuously uses requestAnimationFrame; waiting
            // for a completely idle main queue can block this test forever.
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
