package com.mrmorning.stacy

import android.Manifest
import android.app.AlertDialog
import android.text.InputType
import android.view.WindowManager
import android.widget.EditText
import android.annotation.SuppressLint
import android.os.Bundle
import android.content.Intent
import android.net.Uri
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import android.webkit.ValueCallback
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
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
    private lateinit var historyStore: StacyLocalStore
    private lateinit var backCallback: OnBackPressedCallback
    private var activeConversationId: String = ""
    private var webPageLoaded = false
    private var drawerOpen = false
    private var sectionOpen = false
    private var chatOpen = false
    private var aiConnectionStatus = "SEM CHAVE"
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

        historyStore = StacyLocalStore(this)
        historyStore.markPendingMessagesInterrupted()
        activeConversationId = historyStore.listConversations().firstOrNull()?.id
            ?: historyStore.createConversation().id
        backCallback = object : OnBackPressedCallback(false) {
            override fun handleOnBackPressed() {
                if (!webPageLoaded || !::webView.isInitialized) {
                    isEnabled = false
                    return
                }
                webView.evaluateJavascript(
                    "if(typeof window.stacyNativeBack==='function'){window.stacyNativeBack();}",
                    null,
                )
            }
        }
        onBackPressedDispatcher.addCallback(this, backCallback)

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
                conversationId = activeConversationId,
                onQueued = { runOnUiThread { webState("pensando") } },
            )
        }

        CorePhaseStore.subscribe { state -> runOnUiThread { webState(state) } }
        CoreStatusStore.subscribe { status -> runOnUiThread { webCoreStatus(status) } }

        CoreResultStore.subscribe { result ->
            runOnUiThread {
                if (result.conversationId != null && result.conversationId != activeConversationId) return@runOnUiThread
                val action = result.androidAction
                if (action != null) {
                    webState("respondendo")
                    handleAndroidAction(action)
                } else if (result.response.isNotBlank()) {
                    val isError = result.tipo.equals("erro", ignoreCase = true) ||
                        result.tipo.equals("error", ignoreCase = true)
                    if (isError && (result.response.contains("HTTP 401") || result.response.contains("HTTP 403"))) {
                        aiConnectionStatus = "ERRO DE AUTENTICAÇÃO"
                        webAiStatus(aiConnectionStatus)
                    }
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
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    super.onPageFinished(view, url)
                    webPageLoaded = true
                    publishActiveConversationId()
                    val hasKey = StacySecretStore(this@MainActivity).hasGeminiApiKey()
                    aiConnectionStatus = if (hasKey) "CHAVE SALVA · NÃO VERIFICADA" else "SEM CHAVE"
                    webAiStatus(aiConnectionStatus)
                    publishNavigationState()
                }
            }
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
            "Uma chave está salva com criptografia do Android, mas isso não confirma conexão ativa. Informe outra para substituí-la ou deixe vazio para testar a chave atual. O teste é isolado e não altera o histórico de conversas."
        } else {
            "Configure uma chave Gemini API para ativar a conversa generativa. Crie uma chave em https://aistudio.google.com/apikey. A chave é cifrada no aparelho e não é enviada ao repositório. O teste verifica o acesso real ao Gemini sem criar uma conversa."
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("Conectar IA da STACY")
            .setMessage(message)
            .setView(entry)
            .setPositiveButton("Salvar e testar", null)
            .setNeutralButton("Apagar chave") { _, _ ->
                runCatching { store.clearGeminiApiKey() }
                    .onSuccess {
                        aiConnectionStatus = "SEM CHAVE"
                        webAiStatus(aiConnectionStatus)
                        webCoreStatus("Chave Gemini removida do armazenamento seguro.")
                        webState("online")
                    }
                    .onFailure {
                        webCoreStatus("Não foi possível remover a chave do armazenamento seguro.")
                        webState("erro")
                    }
            }
            .setNegativeButton("Cancelar", null)
            .create()

        dialog.show()
        dialog.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE)
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val key = entry.text?.toString()?.trim().orEmpty()
            if (key.isNotBlank()) {
                try {
                    store.saveGeminiApiKey(key)
                    aiConnectionStatus = "CHAVE SALVA · NÃO VERIFICADA"
                    webAiStatus(aiConnectionStatus)
                } catch (error: Exception) {
                    entry.error = "Falha ao salvar: \${error.message ?: "erro desconhecido"}"
                    entry.requestFocus()
                    return@setOnClickListener
                }
            } else if (!store.hasGeminiApiKey()) {
                entry.error = "Cole uma chave Gemini API antes de testar."
                entry.requestFocus()
                return@setOnClickListener
            }

            val savedKey = runCatching { store.getGeminiApiKey() }.getOrNull()
            if (savedKey.isNullOrBlank() || (key.isNotBlank() && savedKey != key)) {
                entry.error = "A chave não foi confirmada no armazenamento seguro. Tente novamente."
                entry.requestFocus()
                return@setOnClickListener
            }

            entry.error = null
            dialog.dismiss()
            aiConnectionStatus = "VERIFICANDO CONEXÃO…"
            webAiStatus(aiConnectionStatus)
            webCoreStatus("Testando autenticação e resposta do Gemini…")
            webState("pensando")
            coreBridge.testConnection { result ->
                val connected = !result.tipo.equals("erro", ignoreCase = true) &&
                    !result.tipo.equals("error", ignoreCase = true) &&
                    result.response.isNotBlank()
                aiConnectionStatus = if (connected) "CONECTADA · TESTE REAL APROVADO" else {
                    val detail = result.response.lowercase()
                    when {
                        detail.contains("401") || detail.contains("403") || detail.contains("chave") -> "ERRO DE AUTENTICAÇÃO"
                        detail.contains("429") || detail.contains("cota") -> "ERRO DE COTA/LIMITE"
                        detail.contains("internet") || detail.contains("conexão") || detail.contains("tempo") -> "SEM CONEXÃO CONFIRMADA"
                        else -> "ERRO NO TESTE DE CONEXÃO"
                    }
                }
                webAiStatus(aiConnectionStatus)
                webCoreStatus(if (connected) "Conexão com o Gemini validada por resposta real." else result.response)
                webState(if (connected) "online" else "erro")
            }
        }
    }

    inner class StacyJsBridge {
        @JavascriptInterface
        fun stacySend(message: String) {
            stacySendForConversation(message, activeConversationId)
        }

        @JavascriptInterface
        fun stacySendForConversation(message: String, conversationId: String) {
            runOnUiThread {
                val selected = historyStore.getConversation(conversationId)?.id
                if (selected != null) activeConversationId = selected
                else if (activeConversationId.isBlank() || historyStore.getConversation(activeConversationId) == null) {
                    activeConversationId = historyStore.createConversation().id
                }
                publishNavigationState()
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
        @JavascriptInterface fun stacyGetConversations() {
            runOnUiThread { publishConversationList() }
        }

        @JavascriptInterface fun stacyOpenConversation(id: String) {
            runOnUiThread {
                if (historyStore.getConversation(id) == null) {
                    webCoreStatus("Esta conversa não existe mais no histórico local.")
                    publishConversationList()
                    return@runOnUiThread
                }
                activeConversationId = id
                chatOpen = true
                publishActiveConversation()
                publishNavigationState()
            }
        }

        @JavascriptInterface fun stacyNewConversation() {
            runOnUiThread {
                activeConversationId = historyStore.createConversation().id
                chatOpen = true
                publishActiveConversation()
                publishNavigationState()
            }
        }

        @JavascriptInterface fun stacyDeleteConversation(id: String) {
            runOnUiThread {
                coreBridge.cancelConversation(id)
                val deleted = historyStore.deleteConversation(id)
                if (deleted && activeConversationId == id) {
                    activeConversationId = historyStore.createConversation().id
                    publishActiveConversation()
                }
                publishConversationList()
            }
        }

        @JavascriptInterface fun stacyClearConversationHistory() {
            runOnUiThread {
                historyStore.listConversations().forEach { coreBridge.cancelConversation(it.id) }
                historyStore.clearConversationHistory()
                activeConversationId = historyStore.createConversation().id
                publishActiveConversation()
                publishConversationList()
            }
        }

        @JavascriptInterface fun stacySetNavigationState(drawer: Boolean, section: Boolean, chat: Boolean) {
            runOnUiThread {
                drawerOpen = drawer
                sectionOpen = section
                chatOpen = chat
                publishNavigationState()
            }
        }

    }

    private fun publishActiveConversationId() {
        if (!webPageLoaded || !::webView.isInitialized) return
        webView.evaluateJavascript(
            "if(typeof window.stacySetActiveConversationId==='function'){window.stacySetActiveConversationId(${JSONObject.quote(activeConversationId)});}",
            null,
        )
    }

    private fun publishConversationList() {
        if (!webPageLoaded || !::webView.isInitialized) return
        val rows = org.json.JSONArray()
        historyStore.listConversations().forEach { item ->
            rows.put(JSONObject().put("id", item.id).put("title", item.title).put("preview", item.preview).put("updatedAt", item.updatedAt))
        }
        webView.evaluateJavascript(
            "if(typeof window.stacyRenderConversations==='function'){window.stacyRenderConversations($rows);}",
            null,
        )
    }

    private fun publishActiveConversation() {
        if (!webPageLoaded || !::webView.isInitialized) return
        val conversation = historyStore.getConversation(activeConversationId) ?: return
        val messages = org.json.JSONArray()
        historyStore.listConversationMessages(conversation.id).forEach { item ->
            messages.put(
                JSONObject().put("id", item.id).put("role", item.role).put("text", item.text)
                    .put("createdAt", item.createdAt).put("state", item.state),
            )
        }
        val payload = JSONObject().put("id", conversation.id).put("title", conversation.title).put("messages", messages)
        webView.evaluateJavascript(
            "if(typeof window.stacyLoadConversation==='function'){window.stacyLoadConversation($payload);}",
            null,
        )
    }

    private fun publishNavigationState() {
        if (!::backCallback.isInitialized) return
        backCallback.isEnabled = drawerOpen || sectionOpen || chatOpen
    }

    private fun webAiStatus(status: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript(
            "if(typeof window.stacyNativeAiStatus==='function'){window.stacyNativeAiStatus(\${JSONObject.quote(status)});}",
            null,
        )
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

    private fun webUpdateStatus(status: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript("(function(s){try{if(typeof window.stacyNativeUpdateStatus==='function'){window.stacyNativeUpdateStatus(s);return;}}catch(e){} })(" + JSONObject.quote(status) + ")", null)
    }

    private fun webCoreStatus(status: String) {
        if (!::webView.isInitialized) return
        webView.evaluateJavascript("(function(s){try{if(typeof window.stacyNativeCoreStatus==='function'){window.stacyNativeCoreStatus(s);return;}}catch(e){} })(" + JSONObject.quote(status) + ")", null)
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
        webPageLoaded = false
        if (::backCallback.isInitialized) backCallback.isEnabled = false
        CoreResultStore.clear()
        CorePhaseStore.clear()
        CoreStatusStore.clear()
        if (::voiceInput.isInitialized) voiceInput.destroy()
        if (::textToSpeech.isInitialized) textToSpeech.shutdown()
        if (::coreBridge.isInitialized) coreBridge.shutdown()
        if (::historyStore.isInitialized) historyStore.close()
        if (::webView.isInitialized) { webView.removeJavascriptInterface("Android"); webView.destroy() }
        super.onDestroy()
    }
}
