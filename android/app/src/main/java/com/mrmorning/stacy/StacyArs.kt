package com.mrmorning.stacy

import android.content.Context
import android.content.Intent
import org.json.JSONObject

/**
 * ARS — Autoconsulta e Atualização da STACY.
 *
 * Coordinates self-reporting and the signed APK update path. It does not
 * execute downloaded scripts or modify live code: new code is installed only
 * as a package whose repository, hash, package identity, version and signer
 * have been verified, with the final confirmation handled by Android.
 */
class StacyArs(
    context: Context,
    onStatus: (String) -> Unit,
    private val onReport: (JSONObject) -> Unit,
    onInstallIntent: (Intent) -> Boolean,
) {
    private val updater = StacyUpdater(
        context = context.applicationContext,
        onState = onStatus,
        onInstallIntent = onInstallIntent,
    )

    /** Reads the installed version and the current official channel, without installing anything. */
    fun consultar() {
        updater.consult(onReport)
    }

    /** Checks, downloads and validates an available release before opening Android's installer. */
    fun atualizar() {
        updater.checkAndUpdate()
    }

    /** Confirms success only after PackageManager reports the target build installed. */
    fun verificarInstalacaoPendente() {
        updater.verifyPendingInstallation()
    }

    fun encerrar() {
        updater.shutdown()
    }
}
