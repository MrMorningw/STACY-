package com.mrmorning.stacy

import android.Manifest
import android.annotation.SuppressLint
import android.os.Bundle
import android.content.Intent
import android.net.Uri
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.ViewModelProvider
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    private lateinit var voiceInput: AndroidVoiceInput
    private lateinit var coreBridge: StacyCoreBridge
    private lateinit var textToSpeech: AndroidTextToSpeech
    private lateinit var webView: WebView
    private lateinit var vm: StacyViewModel
    private var voiceEnabled = true
    private lateinit var updater: StacyUpdater

    private val requestMicrophone =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) voiceInput.startListening()
            else webState("erro")
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        vm = ViewModelProvider(this)[StacyViewModel::class.java]
        coreBridge = StacyCoreBridge(this)
        textToSpeech = AndroidTextToSpeech(this)
        updater = StacyUpdater(this) { status ->
            runOnUiThread { webUpdateStatus(status) }
        }

        voiceInput = AndroidVoiceInput(
            context = this,
            onResult = { result ->
                runOnUiThread {
                    when (result) {
                        is VoiceResult.Success -> {
                            webState("pensando")
                            vm.onVoiceResult(result)
                        }
                        is VoiceResult.Failure -> {
                            webState("offline")
                            vm.onVoiceResult(result)
                        }
                    }
                }
            },
            onStateChanged = { listening ->
                runOnUiThread { webState(if (listening) "ouvindo" else "online") }
            },
        )

        vm.bindCore { message ->
            coreBridge.process(
                message = message,
                onQueued = { runOnUiThread { webState("pensando") } },
                onError = { error ->
                    runOnUiThread {
                        vm.onCoreError(error)
                        webResponse(error, "erro")
                    }
                },
            )
        }

        CoreResultStore.subscribe { result ->
            runOnUiThread {
                if (result.response.isNotBlank()) {
                    // Keep the ViewModel and the visible WebView in sync with the same CORE result.
                    vm.onCoreResponse(result)
                    if (voiceEnabled) textToSpeech.speak(result.response)
                    webResponse(result.response, result.tipo)
                } else if (result.exitCode != 0) {
                    val error = result.stderr.ifBlank {
                        "O CORE encerrou a execução com erro."
                    }
                    vm.onCoreError(error)
                    webResponse(error, "erro")
                }
            }
        }

        webView = WebView(this).apply {
            setBackgroundColor(android.graphics.Color.BLACK)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            webViewClient = WebViewClient()
            addJavascriptInterface(StacyJsBridge(), "Android")
            loadUrl("file:///android_asset/stacy_prototipo36.html")
        }
        setContentView(webView)
    }

    inner class StacyJsBridge {
        @JavascriptInterface
        fun stacySend(message: String) {
            runOnUiThread { vm.onInputChanged(message); vm.onSend() }
        }

        @JavascriptInterface
        fun stacyVoice() {
            runOnUiThread {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                    android.content.pm.PackageManager.PERMISSION_GRANTED
                ) {
                    webState("ouvindo")
                    voiceInput.startListening()
                } else {
                    requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
                }
            }
        }

        @JavascriptInterface
        fun stacySetVoiceEnabled(enabled: Boolean) {
            voiceEnabled = enabled
        }

        @JavascriptInterface
        fun stacyCheckUpdate() {
            updater.checkAndUpdate()
        }

        @JavascriptInterface
        fun stacyOpenAppSettings() {
            runOnUiThread {
                startActivity(
                    Intent(
                        android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        Uri.parse("package:$packageName"),
                    ),
                )
            }
        }
    }

    private fun webState(state: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript(
            "window.stacyNativeState && window.stacyNativeState(" + JSONObject.quote(state) + ")",
            null,
        )
    }

    private fun webUpdateStatus(status: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript(
            "window.stacyNativeUpdateStatus && window.stacyNativeUpdateStatus(" +
                JSONObject.quote(status) + ")",
            null,
        )
    }

    private fun webResponse(response: String, tipo: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript(
            "window.stacyNativeResponse && window.stacyNativeResponse(" +
                JSONObject.quote(response) + "," + JSONObject.quote(tipo) + ")",
            null,
        )
    }

    override fun onDestroy() {
        CoreResultStore.clear()
        if (::voiceInput.isInitialized) voiceInput.destroy()
        if (::textToSpeech.isInitialized) textToSpeech.shutdown()
        if (::webView.isInitialized) {
            webView.removeJavascriptInterface("Android")
            webView.destroy()
        }
        super.onDestroy()
    }
}
