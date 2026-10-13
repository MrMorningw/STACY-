package com.mrmorning.stacy

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import org.json.JSONObject

class StacyCoreResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val executionId = intent.getIntExtra(EXTRA_EXECUTION_ID, 0)
        val bundle = intent.getBundleExtra(EXTRA_RESULT_BUNDLE) ?: run {
            StacyCoreBridge.fail(executionId, "O Termux não devolveu o resultado do CORE.")
            return
        }
        val stdout = bundle.getString(EXTRA_STDOUT, "").orEmpty()
        val stderr = bundle.getString(EXTRA_STDERR, "").orEmpty()
        val exitCode = bundle.getInt(EXTRA_EXIT_CODE, -1)

        if (exitCode != 0) {
            StacyCoreBridge.fail(executionId, stderr.ifBlank { "O CORE terminou com código $exitCode." })
            return
        }

        try {
            val json = JSONObject(stdout.trim())
            val tipo = json.optString("tipo", "resposta").trim()
            val response = json.optString("resposta").trim()
            if (response.isEmpty()) {
                StacyCoreBridge.fail(executionId, "O CORE concluiu sem retornar uma resposta.")
                return
            }
            CoreResultStore.publish(
                context,
                CoreResult(tipo, response, exitCode, stderr, json.optJSONObject("acao_android")),
            ) {
                StacyCoreBridge.complete(executionId)
            }
        } catch (_: Exception) {
            StacyCoreBridge.fail(executionId, "A STACY recebeu uma resposta inválida do CORE.")
        }
    }

    companion object {
        const val EXTRA_EXECUTION_ID = "stacy_execution_id"
        private const val EXTRA_RESULT_BUNDLE = "com.termux.plugin_result_bundle"
        private const val EXTRA_STDOUT = "stdout"
        private const val EXTRA_STDERR = "stderr"
        private const val EXTRA_EXIT_CODE = "exitCode"
    }
}
