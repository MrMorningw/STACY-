package com.mrmorning.stacy

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper

/**
 * Accepts visual-only lifecycle events emitted by the CORE running in Termux.
 * Execution IDs prevent a delayed event from an old request changing the current UI.
 */
class StacyCorePhaseReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_CORE_PHASE) return

        val executionId = intent.getIntExtra(EXTRA_EXECUTION_ID, -1)
        if (executionId < 0 || !StacyCoreBridge.isExecutionActive(executionId)) return

        val state = intent.getStringExtra(EXTRA_STATE) ?: return
        if (state !in ALLOWED_STATES) return

        CorePhaseStore.publish(context, state)
    }

    companion object {
        const val ACTION_CORE_PHASE = "com.mrmorning.stacy.CORE_PHASE"
        const val EXTRA_EXECUTION_ID = "execution_id"
        const val EXTRA_STATE = "state"
        private val ALLOWED_STATES = setOf("pensando", "pesquisando", "executando")
    }
}

object CorePhaseStore {
    @Volatile private var listener: ((String) -> Unit)? = null

    fun subscribe(listener: (String) -> Unit) {
        this.listener = listener
    }

    fun clear() {
        listener = null
    }

    fun publish(context: Context, state: String) {
        Handler(Looper.getMainLooper()).post {
            listener?.invoke(state)
        }
    }
}
