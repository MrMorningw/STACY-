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
)

class StacyViewModel : ViewModel() {
    var uiState by mutableStateOf(StacyUiState())
        private set

    fun onInputChanged(value: String) {
        uiState = uiState.copy(input = value)
    }

    fun onSend() {
        val text = uiState.input.trim()
        if (text.isEmpty()) return

        uiState = uiState.copy(
            messages = uiState.messages + ChatMessage(text, true),
            input = "",
        )
    }
}
