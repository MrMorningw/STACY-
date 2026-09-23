package com.mrmorning.stacy

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Divider
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import kotlinx.coroutines.launch

data class ChatMessage(
    val text: String,
    val fromUser: Boolean,
)

class MainActivity : ComponentActivity() {
    private lateinit var voiceInput: AndroidVoiceInput
    private lateinit var voiceOutput: AndroidTextToSpeech

    private val requestMicrophone =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) voiceInput.startListening()
        }

    private val pickFile =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            uri?.let {
                val name = it.lastPathSegment ?: "arquivo selecionado"
                currentViewModel?.onFileSelected(name)
            }
        }

    private var currentViewModel: StacyViewModel? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val vm = ViewModelProvider(this)[StacyViewModel::class.java]
        currentViewModel = vm

        voiceInput = AndroidVoiceInput(
            context = this,
            onResult = { result ->
                runOnUiThread { vm.onVoiceResult(result) }
            },
            onStateChanged = { listening ->
                runOnUiThread { vm.onVoiceStateChanged(listening) }
            },
        )

        voiceOutput = AndroidTextToSpeech(this)

        setContent {
            StacyTheme {
                StacyApp(
                    viewModel = vm,
                    onVoice = {
                        if (
                            checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                            PackageManager.PERMISSION_GRANTED
                        ) {
                            voiceInput.startListening()
                        } else {
                            requestMicrophone.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    },
                    onAttach = {
                        pickFile.launch(arrayOf("*/*"))
                    },
                )
            }
        }
    }

    override fun onDestroy() {
        if (::voiceInput.isInitialized) voiceInput.destroy()
        if (::voiceOutput.isInitialized) voiceOutput.shutdown()
        super.onDestroy()
    }
}

@Composable
fun StacyTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF9EC5FF),
            secondary = Color(0xFFB8C7E6),
            background = Color(0xFF080B12),
            surface = Color(0xFF101521),
            onBackground = Color(0xFFE8EDF7),
            onSurface = Color(0xFFE8EDF7),
        ),
        content = content,
    )
}

@Composable
fun StacyApp(
    viewModel: StacyViewModel,
    onVoice: () -> Unit = {},
    onAttach: () -> Unit = {},
) {
    val uiState = viewModel.uiState
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        viewModel.checkCore()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        ModalNavigationDrawer(
            drawerState = drawerState,
            drawerContent = {
                StacyDrawer(
                    activeTopic = uiState.activeTopic,
                    onSelect = { topic ->
                        viewModel.selectTopic(topic)
                        scope.launch { drawerState.close() }
                    },
                )
            },
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing),
            ) {
                StacyHeader(
                    topic = uiState.activeTopic,
                    coreOnline = uiState.coreOnline,
                    onMenu = { scope.launch { drawerState.open() } },
                )

                if (uiState.activeTopic == StacyTopic.CONFIGURACOES) {
                    IntegrationPanel()
                }

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

                if (uiState.isSending) {
                    Text(
                        text = "STACY está processando...",
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                }

                uiState.voiceError?.let { error ->
                    Text(
                        text = error,
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }

                Composer(
                    value = uiState.input,
                    onValueChange = viewModel::onInputChanged,
                    onSend = viewModel::onSend,
                    onVoice = onVoice,
                    onAttach = onAttach,
                    isListening = uiState.isListening,
                    enabled = !uiState.isSending,
                )
            }
        }
    }
}

@Composable
private fun StacyDrawer(
    activeTopic: StacyTopic?,
    onSelect: (StacyTopic) -> Unit,
) {
    ModalDrawerSheet(
        drawerContainerColor = MaterialTheme.colorScheme.surface,
    ) {
        Text(
            text = "STACY",
            modifier = Modifier.padding(horizontal = 24.dp, vertical = 24.dp),
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
        )

        Text(
            text = "TÓPICOS DENRY",
            modifier = Modifier.padding(horizontal = 24.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.secondary,
        )

        Spacer(modifier = Modifier.height(8.dp))

        StacyTopic.entries.forEach { topic ->
            NavigationDrawerItem(
                label = { Text(topic.title) },
                icon = { Text(topic.icon) },
                selected = activeTopic == topic,
                onClick = { onSelect(topic) },
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 2.dp),
            )
        }
    }
}

@Composable
private fun StacyHeader(
    topic: StacyTopic?,
    coreOnline: Boolean,
    onMenu: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onMenu) {
            Icon(
                imageVector = Icons.Default.Menu,
                contentDescription = "Tópicos Denry",
            )
        }

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "STACY",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = topic?.title ?: "Conversa",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.secondary,
            )
        }

        Text(
            text = if (coreOnline) "ONLINE" else "CORE OFFLINE",
            style = MaterialTheme.typography.labelSmall,
            color = if (coreOnline) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.error
            },
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun IntegrationPanel() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 4.dp),
    ) {
        Text(
            text = "INTEGRAÇÕES",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.secondary,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(6.dp))

        val integrations = listOf(
            "Calendário",
            "Alarmes",
            "Notificações",
            "WhatsApp",
            "Instagram",
            "Microsoft Teams",
            "Gmail",
            "Outlook",
            "Outros aplicativos",
        )

        integrations.forEach { item ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(text = "•", color = MaterialTheme.colorScheme.primary)
                Text(
                    text = item,
                    modifier = Modifier.padding(start = 10.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        Divider(modifier = Modifier.padding(top = 8.dp))
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
    onAttach: () -> Unit,
    isListening: Boolean,
    enabled: Boolean,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        IconButton(onClick = onAttach, enabled = enabled) {
            Icon(
                imageVector = Icons.Default.Add,
                contentDescription = "Adicionar arquivo ou foto",
            )
        }

        TextField(
            modifier = Modifier.weight(1f),
            value = value,
            onValueChange = onValueChange,
            placeholder = {
                Text(if (isListening) "Ouvindo..." else "Mensagem para STACY")
            },
            maxLines = 5,
            shape = RoundedCornerShape(24.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = MaterialTheme.colorScheme.surface,
                unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
            ),
        )

        IconButton(onClick = onVoice, enabled = enabled) {
            Icon(
                imageVector = Icons.Default.Mic,
                contentDescription = "Falar com STACY",
                tint = if (isListening) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
            )
        }

        IconButton(
            onClick = onSend,
            enabled = enabled && value.isNotBlank(),
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.Send,
                contentDescription = "Enviar",
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StacyPreview() {
    StacyTheme {
        StacyApp(StacyViewModel())
    }
}
