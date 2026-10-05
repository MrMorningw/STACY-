package com.mrmorning.stacy

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel

enum class StacyState {
    ONLINE, LISTENING, THINKING, RESEARCHING, EXECUTING, RESPONDING, OFFLINE, ERROR
}

data class ChatMessage(
    val text: String,
    val fromUser: Boolean,
)

data class StacyUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage("Boa tarde, senhor. Estou pronta.", false),
    ),
    val input: String = "",
    val isListening: Boolean = false,
    val voiceError: String? = null,
    val state: StacyState = StacyState.ONLINE,
    val sidebarOpen: Boolean = false,
)

class StacyViewModel : ViewModel() {
    var uiState by mutableStateOf(StacyUiState())
        private set

    private var submitToCore: ((String) -> Unit)? = null

    fun bindCore(submitter: (String) -> Unit) { submitToCore = submitter }

    fun onInputChanged(value: String) {
        uiState = uiState.copy(input = value, voiceError = null)
    }

    fun onSend() { submitText(uiState.input) }

    private fun submitText(rawText: String) {
        val text = rawText.trim()
        if (text.isEmpty()) return
        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(text, true),
            input = "",
            state = StacyState.THINKING,
            voiceError = null,
        )
        val bridge = submitToCore
        if (bridge == null) {
            uiState = uiState.copy(
                state = StacyState.ERROR,
                voiceError = "O CORE da STACY ainda não foi conectado.",
            )
            return
        }
        bridge(text)
    }

    fun onCoreResponse(result: CoreResult) {
        if (result.response.isBlank()) return
        val nextState = when (result.tipo.lowercase()) {
            "pesquisa", "pesquisando", "research" -> StacyState.RESEARCHING
            "execucao", "execução", "executando", "execution", "task" -> StacyState.EXECUTING
            "erro", "error" -> StacyState.ERROR
            else -> StacyState.RESPONDING
        }
        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(result.response.trim(), false),
            state = nextState,
            voiceError = if (nextState == StacyState.ERROR) result.stderr.ifBlank { result.response } else null,
        )
    }

    fun onCoreError(message: String) {
        uiState = uiState.copy(state = StacyState.ERROR, voiceError = message)
    }

    fun addAssistantMessage(text: String) {
        if (text.isBlank()) return
        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(text.trim(), false),
            state = StacyState.RESPONDING,
            voiceError = null,
        )
    }

    fun onVoiceStateChanged(listening: Boolean) {
        uiState = uiState.copy(
            isListening = listening,
            state = if (listening) StacyState.LISTENING else uiState.state,
        )
    }

    fun onVoiceResult(result: VoiceResult) {
        when (result) {
            is VoiceResult.Success -> submitText(result.text)
            is VoiceResult.Failure -> uiState = uiState.copy(
                isListening = false,
                state = StacyState.ERROR,
                voiceError = result.message,
            )
        }
    }

    fun toggleSidebar() { uiState = uiState.copy(sidebarOpen = !uiState.sidebarOpen) }
    fun closeSidebar() { uiState = uiState.copy(sidebarOpen = false) }
    fun clearVoiceError() { uiState = uiState.copy(voiceError = null, state = StacyState.ONLINE) }
}
