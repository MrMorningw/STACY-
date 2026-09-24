package com.mrmorning.stacy

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel

enum class StacyState { ONLINE, LISTENING, THINKING, RESPONDING, OFFLINE, ERROR }

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

    fun onInputChanged(value: String) {
        uiState = uiState.copy(input = value, voiceError = null)
    }

    fun onSend() {
        val text = uiState.input.trim()
        if (text.isEmpty()) return
        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(text, true),
            input = "",
            state = StacyState.THINKING,
            voiceError = null,
        )
    }

    fun addAssistantMessage(text: String) {
        if (text.isBlank()) return
        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(text.trim(), false),
            state = StacyState.ONLINE,
        )
    }

    fun onVoiceStateChanged(listening: Boolean) {
        uiState = uiState.copy(
            isListening = listening,
            state = if (listening) StacyState.LISTENING else StacyState.ONLINE,
        )
    }

    fun onVoiceResult(result: VoiceResult) {
        when (result) {
            is VoiceResult.Success -> onInputChanged(result.text)
            is VoiceResult.Failure -> {
                uiState = uiState.copy(
                    isListening = false,
                    state = StacyState.ERROR,
                    voiceError = result.message,
                )
            }
        }
    }

    fun toggleSidebar() {
        uiState = uiState.copy(sidebarOpen = !uiState.sidebarOpen)
    }

    fun closeSidebar() {
        uiState = uiState.copy(sidebarOpen = false)
    }

    fun clearVoiceError() {
        uiState = uiState.copy(voiceError = null, state = StacyState.ONLINE)
    }
}
