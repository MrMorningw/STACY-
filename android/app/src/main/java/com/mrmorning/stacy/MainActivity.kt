package com.mrmorning.stacy

import android.Manifest
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider

class MainActivity : ComponentActivity() {
    private lateinit var voiceInput: AndroidVoiceInput
    private lateinit var coreBridge: StacyCoreBridge
    private lateinit var textToSpeech: AndroidTextToSpeech

    private val requestMicrophone =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) voiceInput.startListening()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val vm = ViewModelProvider(this)[StacyViewModel::class.java]
        currentViewModel = vm
        coreBridge = StacyCoreBridge(this)
        textToSpeech = AndroidTextToSpeech(this)

        vm.bindCore { message ->
            coreBridge.process(
                message = message,
                onQueued = { runOnUiThread { vm.clearVoiceError() } },
                onError = { error -> runOnUiThread { vm.onCoreError(error) } },
            )
        }
        CoreResultStore.subscribe { result ->
            vm.onCoreResponse(result)
            if (result.response.isNotBlank()) textToSpeech.speak(result.response)
        }
        voiceInput = AndroidVoiceInput(
            context = this,
            onResult = { result -> runOnUiThread { vm.onVoiceResult(result) } },
            onStateChanged = { listening -> runOnUiThread { vm.onVoiceStateChanged(listening) } },
        )
        setContent {
            StacyTheme {
                StacyApp(
                    vm,
                    onVoice = {
                        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                            android.content.pm.PackageManager.PERMISSION_GRANTED
                        ) voiceInput.startListening()
                        else requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
                    },
                    onFiles = { pickFiles.launch(arrayOf("*/*")) },
                )
            }
        }
    }

    private var currentViewModel: StacyViewModel? = null
    private val pickFiles =
        registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
            if (uris.isNotEmpty()) {
                currentViewModel?.addAssistantMessage(
                    "Recebi ${uris.size} arquivo(s). O módulo de arquivos foi conectado à interface; " +
                        "o processamento semântico dos arquivos depende da integração correspondente no CORE.",
                )
            }
        }

    override fun onDestroy() {
        CoreResultStore.clear()
        if (::voiceInput.isInitialized) voiceInput.destroy()
        if (::textToSpeech.isInitialized) textToSpeech.shutdown()
        super.onDestroy()
    }
}

@Composable
fun StacyTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF9EC5FF),
            secondary = Color(0xFFFF6A00),
            background = Color.Black,
            surface = Color(0xFF1A1A1A),
            onBackground = Color(0xFFE8EDF7),
            onSurface = Color(0xFFE8EDF7),
        ),
        content = content,
    )
}

@Composable
fun StacyApp(
    viewModel: StacyViewModel,
    onVoice: (StacyViewModel) -> Unit = {},
    onFiles: () -> Unit = {},
) {
    val uiState = viewModel.uiState
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
            StacyHeader(uiState.state)
            LazyColumn(
                Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) { items(uiState.messages) { MessageBubble(it) } }
            Composer(
                value = uiState.input,
                onValueChange = viewModel::onInputChanged,
                onSend = viewModel::onSend,
                onVoice = { onVoice(viewModel) },
                onFiles = onFiles,
            )
        }
    }
}

private val StacyOrange = Color(0xFFFF8A00)

@Composable
private fun StacyHeader(state: StacyState) {
    val label = when (state) {
        StacyState.ONLINE -> "ONLINE"
        StacyState.LISTENING -> "OUVINDO"
        StacyState.THINKING -> "PENSANDO"
        StacyState.RESEARCHING -> "PESQUISANDO"
        StacyState.EXECUTING -> "EXECUTANDO"
        StacyState.RESPONDING -> "RESPONDENDO"
        StacyState.OFFLINE -> "OFFLINE"
        StacyState.ERROR -> "ERRO"
    }
    Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("STACY", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text("INTERFACE • PROTÓTIPO 36 • CORE", style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.secondary)
        }
        Text(label, style = MaterialTheme.typography.labelSmall,
            color = if (state == StacyState.ERROR) Color(0xFFFF4438) else StacyOrange,
            fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun MessageBubble(message: ChatMessage) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start) {
        Box(
            Modifier.background(
                if (message.fromUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)
                else MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp)
            ).padding(horizontal = 16.dp, vertical = 12.dp)
        ) { Text(message.text, color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.bodyLarge) }
    }
}

@Composable
private fun Composer(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    onVoice: () -> Unit,
    onFiles: () -> Unit = {},
) {
    Row(Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.ime).padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.Bottom) {
        IconButton(onClick = onFiles) { Icon(Icons.Default.Add, "Adicionar fotos ou arquivos", tint = StacyOrange) }
        TextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.weight(1f),
            placeholder = { Text("Mensagem para STACY") }, maxLines = 5,
            shape = RoundedCornerShape(24.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = MaterialTheme.colorScheme.surface,
                unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
            ),
        )
        Spacer(Modifier.width(4.dp))
        IconButton(onClick = onVoice) { Icon(Icons.Default.Mic, "Voz", tint = StacyOrange) }
        IconButton(onClick = onSend, enabled = value.isNotBlank()) {
            Icon(Icons.AutoMirrored.Filled.Send, "Enviar")
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StacyPreview() { StacyTheme { StacyApp(StacyViewModel()) } }
