package com.mrmorning.stacy

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import java.util.Locale

sealed interface VoiceResult {
    data class Success(val text: String) : VoiceResult
    data class Failure(val code: String, val message: String) : VoiceResult
}

interface StacyVoiceInput {
    fun startListening()
    fun stopListening()
    fun destroy()
}

interface StacyVoiceOutput {
    fun speak(text: String)
    fun stop()
    fun shutdown()
}

class AndroidVoiceInput(
    private val context: Context,
    private val locale: Locale = Locale("pt", "BR"),
    private val onResult: (VoiceResult) -> Unit,
    private val onStateChanged: (Boolean) -> Unit = {},
) : StacyVoiceInput {

    private var recognizer: SpeechRecognizer? = null

    override fun startListening() {
        if (
            context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            onResult(
                VoiceResult.Failure(
                    "MICROPHONE_PERMISSION_REQUIRED",
                    "A permissão do microfone precisa ser concedida pelo usuário.",
                ),
            )
            return
        }

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            onResult(
                VoiceResult.Failure(
                    "RECOGNIZER_UNAVAILABLE",
                    "O serviço de reconhecimento de voz não está disponível.",
                ),
            )
            return
        }

        if (recognizer == null) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(context).also {
                it.setRecognitionListener(listener)
            }
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, locale.toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, locale.toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
        }

        onStateChanged(true)
        recognizer?.startListening(intent)
    }

    override fun stopListening() {
        recognizer?.stopListening()
        onStateChanged(false)
    }

    override fun destroy() {
        recognizer?.destroy()
        recognizer = null
        onStateChanged(false)
    }

    private val listener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) = Unit
        override fun onBeginningOfSpeech() = Unit
        override fun onRmsChanged(rmsdB: Float) = Unit
        override fun onBufferReceived(buffer: ByteArray?) = Unit

        override fun onEndOfSpeech() {
            onStateChanged(false)
        }

        override fun onError(error: Int) {
            onStateChanged(false)
            onResult(
                VoiceResult.Failure(
                    "SPEECH_ERROR_$error",
                    "O reconhecimento de voz não conseguiu concluir a captura.",
                ),
            )
        }

        override fun onResults(results: Bundle?) {
            onStateChanged(false)
            val text = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                ?.trim()
                .orEmpty()

            if (text.isEmpty()) {
                onResult(
                    VoiceResult.Failure(
                        "EMPTY_TRANSCRIPTION",
                        "Nenhuma fala foi reconhecida.",
                    ),
                )
            } else {
                onResult(VoiceResult.Success(text))
            }
        }

        override fun onPartialResults(partialResults: Bundle?) = Unit
        override fun onEvent(eventType: Int, params: Bundle?) = Unit
    }
}

class AndroidTextToSpeech(
    context: Context,
    private val locale: Locale = Locale("pt", "BR"),
    private val onReady: (Boolean) -> Unit = {},
) : StacyVoiceOutput {

    private var engine: TextToSpeech? = null

    init {
        engine = TextToSpeech(context) { status ->
            val ready = status == TextToSpeech.SUCCESS &&
                engine?.setLanguage(locale)?.let { result ->
                    result != TextToSpeech.LANG_MISSING_DATA &&
                        result != TextToSpeech.LANG_NOT_SUPPORTED
                } == true
            onReady(ready)
        }
    }

    override fun speak(text: String) {
        val normalized = text.trim()
        if (normalized.isEmpty()) return

        engine?.speak(
            normalized,
            TextToSpeech.QUEUE_FLUSH,
            null,
            "stacy_${System.nanoTime()}",
        )
    }

    override fun stop() {
        engine?.stop()
    }

    override fun shutdown() {
        engine?.stop()
        engine?.shutdown()
        engine = null
    }
}
