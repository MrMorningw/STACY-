package com.mrmorning.stacy

import android.Manifest
import android.annotation.SuppressLint
import android.os.Bundle
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
                    textToSpeech.speak(result.response)
                    webResponse(result.response, result.tipo)
                } else if (result.exitCode != 0) {
                    webResponse(
                        result.stderr.ifBlank { "O CORE encerrou a execução com erro." },
                        "erro",
                    )
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
                    voiceInput.startListening()
                } else {
                    requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
                }
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
