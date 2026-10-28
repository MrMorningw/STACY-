package com.mrmorning.stacy

import java.net.URI

/**
 * Rules for ARS (Autoconsulta e Atualização da STACY).
 *
 * This policy is deliberately deterministic: the channel is never considered
 * current if it is behind, malformed, or has a mismatched version identity.
 */
internal object StacyArsPolicy {
    enum class ChannelState {
        UP_TO_DATE,
        UPDATE_AVAILABLE,
        CHANNEL_OUTDATED,
        CHANNEL_INCONSISTENT,
    }

    data class Decision(
        val state: ChannelState,
        val message: String,
    )

    fun evaluate(
        installedVersionCode: Long,
        installedVersionName: String,
        publishedVersionCode: Long,
        publishedVersionName: String,
    ): Decision {
        if (installedVersionCode <= 0L ||
            publishedVersionCode <= 0L ||
            installedVersionName.isBlank() ||
            publishedVersionName.isBlank()
        ) {
            return Decision(
                ChannelState.CHANNEL_INCONSISTENT,
                "ARS: não foi possível confirmar a identidade ou a versão do aplicativo/canal.",
            )
        }

        return when {
            publishedVersionCode < installedVersionCode -> Decision(
                ChannelState.CHANNEL_OUTDATED,
                "ARS: canal desatualizado. Instalado $installedVersionName ($installedVersionCode), " +
                    "publicado $publishedVersionName ($publishedVersionCode). Não é seguro afirmar que está atualizado.",
            )

            publishedVersionCode == installedVersionCode &&
                publishedVersionName != installedVersionName -> Decision(
                ChannelState.CHANNEL_INCONSISTENT,
                "ARS: canal inconsistente. O código instalado coincide, mas o nome da versão difere.",
            )

            publishedVersionCode == installedVersionCode -> Decision(
                ChannelState.UP_TO_DATE,
                "ARS: versão instalada $installedVersionName ($installedVersionCode) coincide com o canal oficial. Nenhuma atualização nova.",
            )

            else -> Decision(
                ChannelState.UPDATE_AVAILABLE,
                "ARS: nova versão oficial disponível: $installedVersionName ($installedVersionCode) → " +
                    "$publishedVersionName ($publishedVersionCode).",
            )
        }
    }

    fun isValidSha256(value: String): Boolean =
        value.trim().lowercase().matches(Regex("[a-f0-9]{64}"))

    /**
     * The public release manifest may only point at the APK for its own
     * published version in the dedicated update repository. Signed APK and
     * SHA-256 validation still run after download.
     */
    fun isApprovedDownloadUrl(rawUrl: String, versionName: String): Boolean {
        if (versionName.isBlank() || !versionName.matches(Regex("[0-9A-Za-z._-]+"))) {
            return false
        }
        return try {
            val uri = URI(rawUrl)
            uri.scheme.equals("https", ignoreCase = true) &&
                uri.host.equals("raw.githubusercontent.com", ignoreCase = true) &&
                uri.port == -1 &&
                uri.userInfo == null &&
                uri.query == null &&
                uri.fragment == null &&
                uri.path == "/MrMorningw/STACY---UPTADES-DEFINITIVO/main/releases/STACY-$versionName.apk"
        } catch (_: Exception) {
            false
        }
    }
}
