package com.mrmorning.stacy

import android.Manifest
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
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
            vm.onCoreResponse(result.response)
            if (result.response.isNotBlank()) {
                textToSpeech.speak(result.response)
            }
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
                        ) {
                            voiceInput.startListening()
                        } else {
                            requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
                        }
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
            background = Color(0xFF000000),
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

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing),
        ) {
            StacyHeader()

            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(uiState.messages) { message ->
                    MessageBubble(message)
                }
            }

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
private fun StacyHeader() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text("STACY", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(
                "INTERFACE • CORE CONECTADO",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.secondary,
            )
        }
        Text(
            "ONLINE",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.primary,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun MessageBubble(message: ChatMessage) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start,
    ) {
        Box(
            modifier = Modifier
                .background(
                    color = if (message.fromUser) {
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)
                    } else {
                        MaterialTheme.colorScheme.surface
                    },
                    shape = RoundedCornerShape(20.dp),
                )
                .padding(horizontal = 16.dp, vertical = 12.dp),
        ) {
            Text(
                text = message.text,
                color = MaterialTheme.colorScheme.onSurface,
                style = MaterialTheme.typography.bodyLarge,
            )
        }
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
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .windowInsetsPadding(WindowInsets.ime)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        IconButton(onClick = onFiles) {
            Icon(Icons.Default.Add, contentDescription = "Adicionar fotos ou arquivos", tint = StacyOrange)
        }

        TextField(
            modifier = Modifier.weight(1f),
            value = value,
            onValueChange = onValueChange,
            placeholder = { Text("Mensagem para STACY") },
            maxLines = 5,
            shape = RoundedCornerShape(24.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = MaterialTheme.colorScheme.surface,
                unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
            ),
        )

        Spacer(modifier = Modifier.width(4.dp))

        IconButton(onClick = onVoice) {
            Icon(Icons.Default.Mic, contentDescription = "Voz", tint = StacyOrange)
        }

        IconButton(onClick = onSend, enabled = value.isNotBlank()) {
            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Enviar")
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StacyPreview() {
    StacyTheme { StacyApp(StacyViewModel()) }
}
