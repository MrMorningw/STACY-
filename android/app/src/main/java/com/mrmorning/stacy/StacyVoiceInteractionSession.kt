package com.mrmorning.stacy

import android.graphics.Color
import android.os.Bundle
import android.service.voice.VoiceInteractionSession
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView

class StacyVoiceInteractionSession(
    context: android.content.Context
) : VoiceInteractionSession(context) {

    private lateinit var status: TextView

    override fun onCreateContentView(): View {
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(48, 36, 48, 36)
            setBackgroundColor(Color.argb(245, 8, 8, 8))
        }

        val title = TextView(context).apply {
            text = "STACY"
            textSize = 28f
            setTextColor(Color.rgb(255, 138, 0))
            gravity = Gravity.CENTER
        }

        status = TextView(context).apply {
            text = "ASSISTENTE • PRONTA"
            textSize = 15f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(0, 12, 0, 0)
        }

        root.addView(title)
        root.addView(status)
        return root
    }

    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        val hasAssist = showFlags and SHOW_WITH_ASSIST != 0
        val hasScreenshot = showFlags and SHOW_WITH_SCREENSHOT != 0
        status.text = when {
            hasAssist && hasScreenshot -> "ASSISTENTE • CONTEXTO + TELA"
            hasAssist -> "ASSISTENTE • CONTEXTO DA TELA"
            hasScreenshot -> "ASSISTENTE • CAPTURA DA TELA"
            else -> "ASSISTENTE • PRONTA"
        }
    }
}
