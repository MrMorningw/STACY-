package com.mrmorning.stacy

import android.service.voice.VoiceInteractionService

/**
 * Lightweight Android system-assistant bridge for STACY.
 * Heavy UI/context handling lives in the session service.
 */
class StacyVoiceInteractionService : VoiceInteractionService() {

    override fun onReady() {
        super.onReady()
        setInvocationEffectEnabled(true)
    }

    override fun onGetSupportedVoiceActions(
        voiceActions: Set<String>
    ): Set<String> = emptySet()
}
