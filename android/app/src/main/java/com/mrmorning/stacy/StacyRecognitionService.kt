package com.mrmorning.stacy

import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionService
import android.speech.SpeechRecognizer

/**
 * Minimal RecognitionService required for a Voice Interaction Application.
 *
 * Speech recognition itself remains delegated to Android's selected
 * recognizer through the existing AndroidVoiceInput path. This service
 * satisfies the VIA contract without creating a second recognition stack.
 */
class StacyRecognitionService : RecognitionService() {

    private val sessions = mutableMapOf<Callback, SpeechRecognizer>()

    override fun onStartListening(intent: Intent?, callback: Callback?) {
        if (callback == null) return
        val recognizer = SpeechRecognizer.createSpeechRecognizer(this)
        sessions[callback] = recognizer
        recognizer.setRecognitionListener(object : android.speech.RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) = callback.readyForSpeech(params)
            override fun onBeginningOfSpeech() = callback.beginningOfSpeech()
            override fun onRmsChanged(rmsdB: Float) = callback.rmsChanged(rmsdB)
            override fun onBufferReceived(buffer: ByteArray?) = callback.bufferReceived(buffer)
            override fun onEndOfSpeech() = callback.endOfSpeech()
            override fun onError(error: Int) {
                callback.error(error)
                cleanup(callback)
            }
            override fun onResults(results: Bundle?) {
                callback.results(results ?: Bundle())
                cleanup(callback)
            }
            override fun onPartialResults(partialResults: Bundle?) =
                callback.partialResults(partialResults ?: Bundle())
            override fun onEvent(eventType: Int, params: Bundle?) =
                Unit
        })
        recognizer.startListening(intent ?: Intent(Intent.ACTION_RECOGNIZE_SPEECH))
    }

    override fun onStopListening(callback: Callback?) {
        callback?.let { sessions[it]?.stopListening() }
    }

    override fun onCancel(callback: Callback?) {
        callback?.let { cleanup(it) }
    }

    override fun onDestroy() {
        sessions.values.forEach { it.destroy() }
        sessions.clear()
        super.onDestroy()
    }

    private fun cleanup(callback: Callback) {
        sessions.remove(callback)?.destroy()
    }
}
