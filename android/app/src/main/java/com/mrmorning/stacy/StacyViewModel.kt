package com.mrmorning.stacy

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import java.util.concurrent.Executors

data class StacyUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage("Boa noite, senhor. Estou pronta.", false),
    ),
    val input: String = "",
    val isListening: Boolean = false,
    val isSending: Boolean = false,
    val coreOnline: Boolean = false,
    val voiceError: String? = null,
    val activeTopic: StacyTopic? = null,
    val lastAssistantResponse: String? = null,
)

class StacyViewModel : ViewModel() {
    private val executor = Executors.newSingleThreadExecutor()

    var uiState by mutableStateOf(StacyUiState())
        private set

    fun checkCore() {
        executor.execute {
            val online = StacyApi.health()
            update { it.copy(coreOnline = online) }
        }
    }

    fun onInputChanged(value: String) {
        update { it.copy(input = value, voiceError = null) }
    }

    fun selectTopic(topic: StacyTopic?) {
        update { it.copy(activeTopic = topic) }
    }

    fun onSend() {
        val text = uiState.input.trim()
        if (text.isEmpty() || uiState.isSending) return
        submit(text)
    }

    private fun submit(text: String) {
        update {
            it.copy(
                messages = it.messages + ChatMessage(text, true),
                input = "",
                isSending = true,
                voiceError = null,
                lastAssistantResponse = null,
            )
        }

        executor.execute {
            try {
                val response = StacyApi.send(text)
                update {
                    it.copy(
                        messages = it.messages + ChatMessage(response.text, false),
                        isSending = false,
                        coreOnline = true,
                        activeTopic = response.topic ?: it.activeTopic,
                        lastAssistantResponse = response.text,
                    )
                }
            } catch (error: Exception) {
                update {
                    it.copy(
                        messages = it.messages + ChatMessage(
                            "Não consegui alcançar o STACY CORE agora. " +
                                "Verifique se o STACY Bridge está online no Termux.",
                            false,
                        ),
                        isSending = false,
                        coreOnline = false,
                        voiceError = error.message,
                        lastAssistantResponse = null,
                    )
                }
            }
        }
    }

    fun onFileSelected(name: String) {
        update {
            it.copy(
                messages = it.messages + ChatMessage(
                    "Arquivo selecionado: $name",
                    true,
                ),
            )
        }
    }

    fun onVoiceStateChanged(listening: Boolean) {
        update { it.copy(isListening = listening) }
    }

    fun onVoiceResult(result: VoiceResult) {
        when (result) {
            is VoiceResult.Success -> {
                val text = result.text.trim()
                if (text.isNotEmpty()) submit(text)
            }

            is VoiceResult.Failure -> {
                update {
                    it.copy(
                        isListening = false,
                        voiceError = result.message,
                    )
                }
            }
        }
    }

    fun clearVoiceError() {
        update { it.copy(voiceError = null) }
    }

    fun clearSpokenResponse() {
        update { it.copy(lastAssistantResponse = null) }
    }

    private fun update(transform: (StacyUiState) -> StacyUiState) {
        uiState = transform(uiState)
    }

    override fun onCleared() {
        executor.shutdownNow()
        super.onCleared()
    }
}
