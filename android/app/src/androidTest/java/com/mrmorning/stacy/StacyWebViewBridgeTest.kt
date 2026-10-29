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
                "(function(){ " +
                    "var input=document.getElementById('message'); " +
                    "var send=document.getElementById('send'); " +
                    "if(!input || !send) return 'missing-composer'; " +
                    "input.value='diagnóstico do CORE nativo'; " +
                    "send.click(); " +
                    "return 'sent'; " +
                "})()",
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

            evaluate(
                webView,
                "(function(){ " +
                    "var input=document.getElementById('message'); " +
                    "var send=document.getElementById('send'); " +
                    "if(!input || !send) return 'missing-composer'; " +
                    "input.value='Explique a teoria geral dos contratos'; " +
                    "send.click(); " +
                    "return 'sent'; " +
                "})()",
            )

            assertTrue(
                "A missing API key must produce one real diagnostic bubble, not a generic placeholder plus a duplicate",
                awaitCondition(webView, timeoutMs = 8_000) {
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
                },
            )
        }
    }

    @Test
    fun rapidSecondSubmitKeepsDraftAndDoesNotReplacePendingReply() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                StacySecretStore(activity).clearGeminiApiKey()
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "Composer or native response callbacks did not become ready",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacySetAnimationsEnabled === 'function' && " +
                            "typeof window.stacyNativeResponse === 'function' && " +
                            "typeof window.stacyComposerIsBusy === 'function' && " +
                            "typeof window.Android === 'object' && typeof window.Android.stacySend === 'function'",
                    ) == "true"
                },
            )
            evaluate(webView, "window.stacySetAnimationsEnabled(false)")

            assertTrue(
                "A second submit must be blocked without replacing the active pending response",
                evaluate(
                    webView,
                    "(function(){ " +
                        "var input=document.getElementById('message'); " +
                        "var send=document.getElementById('send'); " +
                        "var log=document.getElementById('stacyChatLog'); " +
                        "if(!input||!send||!log)return false; " +
                        "input.value='Primeira solicitação sem chave'; send.click(); " +
                        "input.value='RASCUNHO_PRESERVADO'; " +
                        "input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); " +
                        "return log.querySelectorAll('.stacy-chat-row.user').length===1 && " +
                            "input.value==='RASCUNHO_PRESERVADO' && send.disabled===true && " +
                            "window.stacyComposerIsBusy()===true; " +
                    "})()",
                ) == "true",
            )

            assertTrue(
                "The first reply should complete normally and leave the second draft available",
                awaitCondition(webView, timeoutMs = 8_000) {
                    evaluate(
                        webView,
                        "(function(){ " +
                            "var input=document.getElementById('message'); " +
                            "var send=document.getElementById('send'); " +
                            "var log=document.getElementById('stacyChatLog'); " +
                            "var replies=log?log.querySelectorAll('.stacy-chat-row.assistant .stacy-chat-bubble'):[]; " +
                            "return !!input && !!send && !!log && " +
                                "log.querySelectorAll('.stacy-chat-row.user').length===1 && replies.length===1 && " +
                                "replies[0].innerText.includes('IA generativa ainda não está conectada') && " +
                                "input.value==='RASCUNHO_PRESERVADO' && send.disabled===false && " +
                                "window.stacyComposerIsBusy()===false; " +
                        "})()",
                    ) == "true"
                },
            )
        }
    }

    @Test
    fun coreDiagnosticsShowIndependentLocalAndGeminiResults() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                StacySecretStore(activity).clearGeminiApiKey()
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "STACY page or diagnostic bridge did not become ready",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacySetAnimationsEnabled === 'function' && " +
                            "typeof window.stacyOpenPage === 'function' && " +
                            "typeof window.stacyDiagnosticUpdate === 'function' && " +
                            "typeof window.Android === 'object' && " +
                            "typeof window.Android.stacyRunDiagnostics === 'function'",
                    ) == "true"
                },
            )
            evaluate(webView, "window.stacySetAnimationsEnabled(false)")
            evaluate(webView, "window.stacyOpenPage('nucleo')")

            assertTrue(
                "The diagnostic action is missing from the CORE page",
                awaitCondition(webView, timeoutMs = 5_000) {
                    evaluate(
                        webView,
                        "!!document.querySelector('[data-stacy-action=diagnosticoCore]')",
                    ) == "true"
                },
            )

            evaluate(
                webView,
                "document.querySelector('[data-stacy-action=diagnosticoCore]').click()",
            )

            assertTrue(
                "The panel did not report local CORE success separately from a missing Gemini key",
                awaitCondition(webView, timeoutMs = 10_000) {
                    evaluate(
                        webView,
                        "(function(){ " +
                            "var summary=document.getElementById('stacyDiagnosticSummary'); " +
                            "var core=document.querySelector('[data-diagnostic-row=core] [data-diagnostic-status]'); " +
                            "var storage=document.querySelector('[data-diagnostic-row=sqlite] [data-diagnostic-status]'); " +
                            "var gemini=document.querySelector('[data-diagnostic-row=gemini] [data-diagnostic-status]'); " +
                            "var termux=document.querySelector('[data-diagnostic-row=termux] [data-diagnostic-status]'); " +
                            "return !!summary && summary.innerText.includes('Falha localizada em: Gemini / API generativa.') && " +
                            "!!core && core.innerText === 'OK' && " +
                            "!!storage && storage.innerText === 'OK' && " +
                            "!!gemini && gemini.innerText === 'FALHA' && " +
                            "!!termux && termux.innerText === 'NÃO UTILIZADO'; " +
                        "})()",
                    ) == "true"
                },
            )
        }
    }

    @Test
    fun arsPageExposesSelfConsultAndSafeUpdateControls() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            lateinit var webView: WebView
            scenario.onActivity { activity ->
                val content = activity.findViewById<ViewGroup>(android.R.id.content)
                webView = content.getChildAt(0) as? WebView
                    ?: throw AssertionError("MainActivity is not displaying its production WebView")
            }

            assertTrue(
                "ARS JavaScript or native methods did not become ready",
                awaitCondition(webView, timeoutMs = 12_000) {
                    evaluate(
                        webView,
                        "typeof window.stacyOpenPage === 'function' && " +
                            "typeof window.stacyArsReport === 'function' && " +
                            "typeof window.Android === 'object' && " +
                            "typeof window.Android.stacyArsConsult === 'function' && " +
                            "typeof window.Android.stacyArsUpdate === 'function' && " +
                            "typeof window.Android.stacyGetBuildInfo === 'function'",
                    ) == "true"
                },
            )

            evaluate(webView, "window.stacyOpenPage('ars')")

            assertTrue(
                "ARS page did not render the self-consult and update controls",
                awaitCondition(webView, timeoutMs = 5_000) {
                    evaluate(
                        webView,
                        "!!document.getElementById('stacyArsSummary') && " +
                            "!!document.querySelector('[data-stacy-action=arsConsultar]') && " +
                            "!!document.querySelector('[data-stacy-action=arsAtualizar]') && " +
                            "!!document.getElementById('stacyArsInstalled') && " +
                            "!!document.getElementById('stacyArsPublished')",
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
