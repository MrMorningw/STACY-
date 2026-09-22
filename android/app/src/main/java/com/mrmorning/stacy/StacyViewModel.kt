package com.mrmorning.stacy

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class StacyUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage("Boa tarde, senhor. Estou pronta.", false),
    ),
    val input: String = "",
)

class StacyViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(StacyUiState())
    val uiState: StateFlow<StacyUiState> = _uiState.asStateFlow()

    fun onInputChanged(value: String) {
        _uiState.value = _uiState.value.copy(input = value)
    }

    fun onSend() {
        val text = _uiState.value.input.trim()
        if (text.isEmpty()) return

        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + ChatMessage(text, true),
            input = "",
        )
    }
}
