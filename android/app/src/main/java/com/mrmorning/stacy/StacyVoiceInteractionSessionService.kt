package com.mrmorning.stacy

import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService

class StacyVoiceInteractionSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: android.os.Bundle?): VoiceInteractionSession =
        StacyVoiceInteractionSession(this)
}
