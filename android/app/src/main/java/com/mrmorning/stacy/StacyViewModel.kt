package com.mrmorning.stacy

import androidx.lifecycle.ViewModel
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

data class StacyUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage("Boa tarde, senhor. Estou pronta.", false),
    ),
    val input: String = "",
    val isListening: Boolean = false,
    val voiceError: String? = null,
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
            voiceError = null,
        )
    }

    fun onVoiceStateChanged(listening: Boolean) {
        uiState = uiState.copy(isListening = listening)
    }

    fun onVoiceResult(result: VoiceResult) {
        when (result) {
            is VoiceResult.Success -> onInputChanged(result.text)
            is VoiceResult.Failure -> {
                uiState = uiState.copy(
                    isListening = false,
                    voiceError = result.message,
                )
            }
        }
    }

    fun clearVoiceError() {
        uiState = uiState.copy(voiceError = null)
    }
}
