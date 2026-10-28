package com.mrmorning.stacy

import android.Manifest
import android.app.AlertDialog
import android.text.InputType
import android.view.WindowManager
import android.widget.EditText
import android.annotation.SuppressLint
import android.os.Bundle
import android.os.SystemClock
import android.content.Intent
import android.net.Uri
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import android.webkit.ValueCallback
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.ViewModelProvider
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    private lateinit var voiceInput: AndroidVoiceInput
    private lateinit var coreBridge: StacyCoreBridge
    private lateinit var textToSpeech: AndroidTextToSpeech
    private lateinit var androidAutomation: AndroidAutomation
    private lateinit var webView: WebView
    private lateinit var vm: StacyViewModel
    private var voiceEnabled = true
    private lateinit var updater: StacyUpdater
    private var pendingFileChooser: ValueCallback<Array<Uri>>? = null
    private val responseHandler = android.os.Handler(android.os.Looper.getMainLooper())
    private val fileChooserResult = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val callback = pendingFileChooser ?: return@registerForActivityResult
        pendingFileChooser = null
        val data = result.data
        val uris = if (result.resultCode == RESULT_OK && data != null) {
            val clip = data.clipData
            when {
                clip != null -> Array(clip.itemCount) { index -> clip.getItemAt(index).uri }
                data.data != null -> arrayOf(data.data!!)
                else -> null
            }
        } else null
        callback.onReceiveValue(uris)
    }

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
        androidAutomation = AndroidAutomation(this)
        textToSpeech = AndroidTextToSpeech(this)
        updater = StacyUpdater(this) { status -> runOnUiThread { webUpdateStatus(status) } }

        voiceInput = AndroidVoiceInput(
            context = this,
            onResult = { result ->
                runOnUiThread {
                    when (result) {
                        is VoiceResult.Success -> { webState("pensando"); vm.onVoiceResult(result) }
                        is VoiceResult.Failure -> { webState("offline"); vm.onVoiceResult(result) }
                    }
                }
            },
            onStateChanged = { listening -> runOnUiThread { webState(if (listening) "ouvindo" else "online") } },
        )

        vm.bindCore { message ->
            coreBridge.process(
                message = message,
                onQueued = { runOnUiThread { webState("pensando") } },
            )
        }

        CorePhaseStore.subscribe { state -> runOnUiThread { webState(state) } }

        CoreResultStore.subscribe { result ->
            runOnUiThread {
                val action = result.androidAction
                if (action != null) {
                    webState("respondendo")
                    handleAndroidAction(action)
                } else if (result.response.isNotBlank()) {
                    val isError = result.tipo.equals("erro", ignoreCase = true) ||
                        result.tipo.equals("error", ignoreCase = true)
                    vm.onCoreResponse(result)
                    webResponse(formatResponseWithSources(result), result.tipo)
                    webState(if (isError) "erro" else "respondendo")
                    if (voiceEnabled) textToSpeech.speak(result.response)
                    if (!isError) {
                        responseHandler.postDelayed({ webState("online") }, 1200L)
                    }
                } else {
                    val error = if (result.exitCode != 0) {
                        result.stderr.ifBlank { "O CORE encerrou a execução com erro." }
                    } else {
                        "O CORE não retornou uma resposta válida, senhor."
                    }
                    vm.onCoreError(error)
                    webResponse(error, "erro")
                    webState("erro")
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
            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(webView: WebView?, filePathCallback: ValueCallback<Array<Uri>>?, fileChooserParams: FileChooserParams?): Boolean {
                    pendingFileChooser?.onReceiveValue(null)
                    pendingFileChooser = filePathCallback ?: return false
                    return try {
                        val intent = fileChooserParams?.createIntent()
                            ?: Intent(Intent.ACTION_GET_CONTENT).apply { type = "*/*"; addCategory(Intent.CATEGORY_OPENABLE) }
                        fileChooserResult.launch(intent)
                        true
                    } catch (_: Exception) {
                        pendingFileChooser?.onReceiveValue(null)
                        pendingFileChooser = null
                        false
                    }
                }
            }
            addJavascriptInterface(StacyJsBridge(), "Android")
            loadUrl("file:///android_asset/stacy_prototipo36.html")
        }
        setContentView(webView)
    }

    private fun formatResponseWithSources(result: CoreResult): String {
        val sources = result.fontes ?: return result.response
        val lines = (0 until sources.length()).mapNotNull { index ->
            val source = sources.optJSONObject(index) ?: return@mapNotNull null
            val title = source.optString("titulo", "Fonte").take(180)
            val url = source.optString("url")
            if (!url.startsWith("https://")) null else "${title}\n$url"
        }
        return if (lines.isEmpty()) result.response else result.response + "\n\nFontes consultadas:\n" + lines.joinToString("\n\n")
    }

    private fun handleAndroidAction(action: JSONObject) {
        val operation = action.optString("acao")
        val outcome = when (operation) {
            "abrir_configuracoes" -> androidAutomation.openSettings()
            "abrir_calendario" -> androidAutomation.openCalendar()
            "abrir_aplicativo" -> {
                val packageName = action.optString("pacote")
                if (packageName !in setOf("com.whatsapp", "com.google.android.youtube", "com.android.chrome", "com.google.android.gm", "com.spotify.music", "com.google.android.apps.maps")) {
                    AutomationResult.Failure("APP_NOT_ALLOWED", "Esse aplicativo não está na lista de ações autorizadas da STACY.")
                } else androidAutomation.openApplication(packageName)
            }
            "selecionar_arquivo" -> androidAutomation.pickFile(action.optString("mime_type", "*/*"))
            "compartilhar_texto" -> androidAutomation.shareText(action.optString("texto"), "Compartilhar pela STACY")
            else -> AutomationResult.Failure("UNKNOWN_ANDROID_ACTION", "A STACY recusou uma ação Android desconhecida.")
        }

        when (outcome) {
            is AutomationResult.Success -> {
                val message = when (operation) {
                    "abrir_configuracoes" -> "Configurações do Android abertas, senhor."
                    "abrir_calendario" -> "Calendário aberto, senhor."
                    "abrir_aplicativo" -> "Solicitei a abertura de ${action.optString("nome", "aplicativo")}, senhor."
                    "selecionar_arquivo" -> "Seletor de arquivos aberto. Escolha o arquivo desejado, senhor."
                    "compartilhar_texto" -> "Menu de compartilhamento aberto. Escolha o aplicativo e confirme o envio, senhor."
                    else -> outcome.message
                }
                vm.addAssistantMessage(message)
                if (voiceEnabled) textToSpeech.speak(message)
                webResponse(message, "resposta")
                webState("respondendo")
                responseHandler.postDelayed({ webState("online") }, 1200L)
            }
            is AutomationResult.Failure -> {
                vm.onCoreError(outcome.message)
                if (voiceEnabled) textToSpeech.speak(outcome.message)
                webResponse(outcome.message, "erro")
                webState("erro")
            }
        }
    }

    private fun configureAiProvider() {
        val store = StacySecretStore(this)
        val hasSavedKey = store.hasGeminiApiKey()
        val entry = EditText(this).apply {
            hint = "Chave da Gemini API"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            maxLines = 1
        }
        val message = if (hasSavedKey) {
            "Uma chave já está salva com criptografia do Android. Informe outra para substituí-la ou deixe vazio para testar a chave atual. As mensagens são enviadas ao Google; a STACY usa o ID de interação armazenado no aparelho para manter o contexto no serviço."
        } else {
            "Configure uma chave Gemini API para ativar a conversa generativa. Crie uma chave em https://aistudio.google.com/apikey. A chave é cifrada no aparelho e não é enviada ao repositório. As mensagens são enviadas ao Google; para manter o contexto, o serviço armazena as interações de acordo com a retenção da conta. Não envie senhas ou segredos."
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("Conectar IA da STACY")
            .setMessage(message)
            .setView(entry)
            .setPositiveButton("Salvar e testar") { _, _ ->
                val key = entry.text?.toString()?.trim().orEmpty()
                if (key.isNotBlank()) {
                    try {
                        store.saveGeminiApiKey(key)
                    } catch (error: Exception) {
                        webResponse("Não foi possível salvar a chave: " + (error.message ?: "erro desconhecido"), "erro")
                        webState("erro")
                        return@setPositiveButton
                    }
                } else if (!store.hasGeminiApiKey()) {
                    webResponse("Cole uma chave Gemini API antes de testar a conexão.", "erro")
                    webState("erro")
                    return@setPositiveButton
                }
                webState("pensando")
                webResponse("Chave configurada. Verificando a conexão segura com a IA...", "resposta")
                coreBridge.testConnection { result ->
                    CoreResultStore.publish(this@MainActivity, result)
                }
            }
            .setNeutralButton("Apagar chave e contexto") { _, _ ->
                store.clearGeminiApiKey()
                webResponse("A chave da IA e o vínculo de contexto foram removidos deste aparelho. Os comandos locais continuam disponíveis.", "resposta")
                webState("online")
            }
            .setNegativeButton("Cancelar", null)
            .create()
        dialog.show()
        dialog.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE)
    }

    inner class StacyJsBridge {
        @JavascriptInterface
        fun stacyGetBuildInfo(): String = try {
            val packageInfo = packageManager.getPackageInfo(packageName, 0)
            val installedCode = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                packageInfo.longVersionCode
            } else {
                @Suppress("DEPRECATION")
                packageInfo.versionCode.toLong()
            }
            JSONObject()
                .put("versionName", packageInfo.versionName ?: "desconhecida")
                .put("versionCode", installedCode)
                .put("applicationId", packageName)
                .put("androidApi", android.os.Build.VERSION.SDK_INT)
                .toString()
        } catch (error: Exception) {
            JSONObject().put("error", error.message ?: "Não foi possível ler a versão instalada.").toString()
        }

        @JavascriptInterface
        fun stacyPingBridge(requestId: String) {
            runOnUiThread {
                publishDiagnosticCallback(
                    "stacyBridgePingResult",
                    JSONObject()
                        .put("requestId", requestId)
                        .put("status", "ok")
                        .put("detail", "A chamada chegou à ponte Kotlin e retornou ao WebView."),
                )
            }
        }

        @JavascriptInterface
        fun stacyRunDiagnostics(requestId: String) {
            Thread({
                val startedAt = SystemClock.elapsedRealtime()
                val checks = org.json.JSONArray()
                val report = JSONObject()
                    .put("requestId", requestId)
                    .put("checks", checks)
                    .put("startedAt", System.currentTimeMillis())

                fun setCheck(
                    id: String,
                    label: String,
                    status: String,
                    detail: String,
                    latencyMs: Long? = null,
                ) {
                    val item = JSONObject()
                        .put("id", id)
                        .put("label", label)
                        .put("status", status)
                        .put("detail", detail)
                    if (latencyMs != null) item.put("latencyMs", latencyMs)
                    var index = -1
                    for (i in 0 until checks.length()) {
                        if (checks.optJSONObject(i)?.optString("id") == id) {
                            index = i
                            break
                        }
                    }
                    if (index >= 0) checks.put(index, item) else checks.put(item)
                }

                fun publish() = publishDiagnosticCallback("stacyDiagnosticUpdate", report)

                // Reaching this method proves that JavaScript can invoke the Android bridge.
                setCheck("html", "HTML / JavaScript", "ok", "JavaScript ativo; a página iniciou o diagnóstico.")
                setCheck("bridge", "Ponte WebView / Android", "ok", "A ponte recebeu a chamada de diagnóstico.")

                val coreStarted = SystemClock.elapsedRealtime()
                try {
                    val result = coreBridge.runNativeDiagnostic()
                    val coreOk = result?.response?.contains("CORE NATIVO: ONLINE", ignoreCase = true) == true
                    setCheck(
                        "core",
                        "CORE Kotlin / Android",
                        if (coreOk) "ok" else "fail",
                        result?.response?.ifBlank { "O núcleo não retornou o diagnóstico local esperado." }
                            ?: "O roteador nativo não reconheceu o comando de diagnóstico.",
                        SystemClock.elapsedRealtime() - coreStarted,
                    )
                } catch (error: Exception) {
                    setCheck("core", "CORE Kotlin / Android", "fail", error.message ?: "Falha ao consultar o núcleo.")
                }

                val storageStarted = SystemClock.elapsedRealtime()
                try {
                    val storageOk = coreBridge.checkLocalStorage()
                    setCheck(
                        "sqlite",
                        "Banco local SQLite",
                        if (storageOk) "ok" else "fail",
                        if (storageOk) "Consulta SELECT 1 concluída no banco local." else "O banco local não passou na verificação.",
                        SystemClock.elapsedRealtime() - storageStarted,
                    )
                } catch (error: Exception) {
                    setCheck("sqlite", "Banco local SQLite", "fail", error.message ?: "Falha ao consultar o banco local.")
                }

                setCheck("termux", "Termux / daemon Python", "not_used", "Não participa do APK; nenhum serviço Termux foi consultado.")
                setCheck("gemini", "Gemini / API generativa", "checking", "Teste HTTPS real em andamento; exige chave válida e internet.")

                runOnUiThread {
                    publish()
                    val apiStarted = SystemClock.elapsedRealtime()
                    coreBridge.testConnection { result ->
                        runOnUiThread {
                            val apiOk = result.exitCode == 0 &&
                                !result.tipo.equals("erro", ignoreCase = true) &&
                                !result.tipo.equals("error", ignoreCase = true) &&
                                result.response.isNotBlank()
                            val detail = if (apiOk) {
                                "A API respondeu ao teste real: " + result.response.trim().take(240)
                            } else {
                                result.response.ifBlank { result.stderr }.ifBlank {
                                    "A API não retornou uma resposta válida."
                                }.take(420)
                            }
                            setCheck(
                                "gemini",
                                "Gemini / API generativa",
                                if (apiOk) "ok" else "fail",
                                detail,
                                SystemClock.elapsedRealtime() - apiStarted,
                            )
                            report.put("completed", true)
                            report.put("completedAt", System.currentTimeMillis())
                            report.put("elapsedMs", SystemClock.elapsedRealtime() - startedAt)
                            publish()
                        }
                    }
                }
            }, "stacy-core-diagnostics").start()
        }

        @JavascriptInterface
        fun stacySend(message: String) {
            runOnUiThread {
                responseHandler.removeCallbacksAndMessages(null)
                webState("pensando")
                vm.onInputChanged(message)
                vm.onSend()
            }
        }

        @JavascriptInterface
        fun stacyVoice() {
            runOnUiThread {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    webState("ouvindo")
                    voiceInput.startListening()
                } else requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
            }
        }

        @JavascriptInterface fun stacySetVoiceEnabled(enabled: Boolean) { voiceEnabled = enabled }
        @JavascriptInterface fun stacyConfigureAi() {
            runOnUiThread { configureAiProvider() }
        }
        @JavascriptInterface fun stacyCheckUpdate() { updater.checkAndUpdate() }
        @JavascriptInterface fun stacyOpenAppSettings() {
            runOnUiThread { startActivity(Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))) }
        }
        @JavascriptInterface fun stacyOpenAndroidSettings() { runOnUiThread { reportAutomationOutcome(androidAutomation.openSettings(), "Configurações do Android abertas.") } }
        @JavascriptInterface fun stacyOpenCalendar() { runOnUiThread { reportAutomationOutcome(androidAutomation.openCalendar(), "Calendário do Android aberto.") } }
        @JavascriptInterface fun stacyShareText(text: String) { runOnUiThread { reportAutomationOutcome(androidAutomation.shareText(text, "Compartilhar pela STACY"), "Menu de compartilhamento aberto.") } }
    }

    private fun reportAutomationOutcome(outcome: AutomationResult, successMessage: String) {
        val message = when (outcome) {
            is AutomationResult.Success -> successMessage
            is AutomationResult.Failure -> outcome.message
        }
        if (outcome is AutomationResult.Success) vm.addAssistantMessage(message) else vm.onCoreError(message)
        if (voiceEnabled) textToSpeech.speak(message)
        webResponse(message, if (outcome is AutomationResult.Success) "resposta" else "erro")
        if (outcome is AutomationResult.Success) {
            webState("respondendo")
            responseHandler.postDelayed({ webState("online") }, 1200L)
        } else webState("erro")
    }

    private fun webState(state: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript("(function(s){try{if(typeof window.stacyNativeState==='function'){window.stacyNativeState(s);return;}var app=document.getElementById('app');if(app){app.classList.remove('online','ouvindo','pensando','pesquisando','executando','respondendo','offline','erro');app.classList.add(s);}})(" + JSONObject.quote(state) + ")", null)
    }

    private fun publishDiagnosticCallback(functionName: String, payload: JSONObject) {
        if (!::webView.isInitialized || isFinishing || isDestroyed) return
        val serialized = JSONObject.quote(payload.toString())
        webView.evaluateJavascript(
            "window.$functionName && window.$functionName($serialized)",
            null,
        )
    }

    private fun webUpdateStatus(status: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript("(function(s){try{if(typeof window.stacyNativeUpdateStatus==='function'){window.stacyNativeUpdateStatus(s);return;}}catch(e){} })(" + JSONObject.quote(status) + ")", null)
    }

    private fun webResponse(response: String, tipo: String) {
        if (!::webView.isInitialized) return
        val responseJson = JSONObject.quote(response)
        val typeJson = JSONObject.quote(tipo)
        val script = """
            (function(r,t){
                var delivered=false;
                try{
                    if(typeof window.stacyNativeResponse==='function'){
                        try{window.stacyNativeResponse(r,t);delivered=true;}catch(e){}
                    }
                }catch(e){}
                if(delivered)return;
                try{
                    var app=document.getElementById('app');
                    var panel=document.querySelector('.responsePanel');
                    var bubble=document.querySelector('.responseBubble');
                    if(bubble){
                        bubble.textContent=r;
                        bubble.style.opacity='1';
                        bubble.style.transform='translateY(0)';
                    }
                    if(panel)panel.style.display='block';
                    if(app)app.classList.add('has-response');
                }catch(e){}
            }($responseJson,$typeJson));
        """.trimIndent()
        webView.evaluateJavascript(script, null)
    }

    override fun onDestroy() {
        pendingFileChooser?.onReceiveValue(null)
        pendingFileChooser = null
        responseHandler.removeCallbacksAndMessages(null)
        CoreResultStore.clear()
        CorePhaseStore.clear()
        if (::voiceInput.isInitialized) voiceInput.destroy()
        if (::textToSpeech.isInitialized) textToSpeech.shutdown()
        if (::coreBridge.isInitialized) coreBridge.shutdown()
        if (::webView.isInitialized) { webView.removeJavascriptInterface("Android"); webView.destroy() }
        super.onDestroy()
    }
}
