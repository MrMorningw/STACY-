package com.mrmorning.stacy

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Secure APK updater used by ARS.
 *
 * The installed version and public update channel are compared independently.
 * The updater only accepts a versioned APK from the official update repository,
 * validates manifest metadata, SHA-256, package identity, version and signing
 * certificate, then delegates the final install confirmation to Android.
 */
class StacyUpdater(
    context: Context,
    private val onState: (String) -> Unit,
    private val onInstallIntent: (Intent) -> Unit = { intent ->
        context.startActivity(intent)
    },
) {
    companion object {
        private const val API_URL =
            "https://raw.githubusercontent.com/MrMorningw/STACY---UPTADES-DEFINITIVO/main/update.json"
        private const val USER_AGENT = "STACY-ARS/1.0"
        private const val APK_PREFIX = "STACY"
        private const val MAX_MANIFEST_BYTES = 256 * 1024
        private const val MAX_APK_BYTES = 250L * 1024L * 1024L
        private const val PREFS_NAME = "stacy_ars"
        private const val KEY_PENDING_VERSION_CODE = "pending_version_code"
        private const val KEY_PENDING_VERSION_NAME = "pending_version_name"
        private const val KEY_PENDING_AT = "pending_install_started_at"
    }

    private val appContext = context.applicationContext
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val preferences = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private data class ReleaseSnapshot(
        val asset: JSONObject,
        val installedCode: Long,
        val installedName: String,
        val publishedCode: Long,
        val publishedName: String,
        val digest: String,
        val certificate: String,
        val minAndroid: Int,
    )

    /** Consults installed build vs. official channel without downloading or installing. */
    fun consult(onReport: (JSONObject) -> Unit) {
        onState("ARS: consultando a versão instalada e o canal oficial…")
        executor.execute {
            val report = try {
                val snapshot = loadValidatedRelease()
                val decision = StacyArsPolicy.evaluate(
                    snapshot.installedCode,
                    snapshot.installedName,
                    snapshot.publishedCode,
                    snapshot.publishedName,
                )
                JSONObject()
                    .put("status", decision.state.name.lowercase(Locale.ROOT))
                    .put("summary", decision.message)
                    .put("checkedAt", System.currentTimeMillis())
                    .put(
                        "installed",
                        JSONObject()
                            .put("versionName", snapshot.installedName)
                            .put("versionCode", snapshot.installedCode),
                    )
                    .put(
                        "published",
                        JSONObject()
                            .put("versionName", snapshot.publishedName)
                            .put("versionCode", snapshot.publishedCode)
                            .put("minAndroid", snapshot.minAndroid),
                    )
                    .put(
                        "integrity",
                        JSONObject()
                            .put("manifestValid", true)
                            .put("sha256MetadataConsistent", true)
                            .put("certificateMetadataValid", true)
                            .put("installedSignatureMatchesOfficial", true)
                            .put("downloadOriginApproved", true),
                    )
                    .put("termux", "not_used")
            } catch (error: Exception) {
                val installed = try {
                    JSONObject()
                        .put("versionName", currentVersionName())
                        .put("versionCode", currentVersionCode())
                } catch (_: Exception) {
                    JSONObject()
                }
                JSONObject()
                    .put("status", "error")
                    .put("summary", "ARS: consulta não concluída — ${friendlyError(error)}")
                    .put("checkedAt", System.currentTimeMillis())
                    .put("installed", installed)
                    .put("published", JSONObject())
                    .put(
                        "integrity",
                        JSONObject()
                            .put("manifestValid", false)
                            .put("sha256MetadataConsistent", false)
                            .put("certificateMetadataValid", false)
                            .put("installedSignatureMatchesOfficial", false)
                            .put("downloadOriginApproved", false),
                    )
                    .put("termux", "not_used")
            }
            val summary = report.optString("summary", "ARS: consulta concluída sem resumo.")
            onState(summary)
            onReport(report)
        }
    }

    /** Checks the official channel and starts the verified Android installer only when needed. */
    fun checkAndUpdate() {
        onState("ARS: verificando o canal oficial…")
        executor.execute {
            try {
                val release = loadValidatedRelease()
                val decision = StacyArsPolicy.evaluate(
                    release.installedCode,
                    release.installedName,
                    release.publishedCode,
                    release.publishedName,
                )
                when (decision.state) {
                    StacyArsPolicy.ChannelState.UP_TO_DATE -> {
                        onState("ARS: ${decision.message}")
                    }

                    StacyArsPolicy.ChannelState.CHANNEL_OUTDATED -> {
                        throw IllegalStateException(decision.message)
                    }

                    StacyArsPolicy.ChannelState.CHANNEL_INCONSISTENT -> {
                        throw IllegalStateException(decision.message)
                    }

                    StacyArsPolicy.ChannelState.UPDATE_AVAILABLE -> {
                        onState("${decision.message} Baixando o pacote oficial e validando a integridade…")
                        val file = downloadApk(release.asset, release.publishedName)
                        validateApk(
                            file = file,
                            asset = release.asset,
                            expectedDigest = release.digest,
                            expectedCertificate = release.certificate,
                            assetVersionCode = release.publishedCode,
                            expectedVersionName = release.publishedName,
                            currentVersionCode = release.installedCode,
                        )
                        onState(
                            "ARS: pacote ${release.publishedName} validado. Abrindo o instalador oficial do Android; a instalação ainda precisa ser confirmada pelo sistema.",
                        )
                        installApk(file, release.publishedCode, release.publishedName)
                    }
                }
            } catch (error: Exception) {
                onState("ARS: atualização não concluída — ${friendlyError(error)}")
            }
        }
    }

    /**
     * Called when the app returns from Android's package installer.
     * Success is reported only if PackageManager shows the target version installed.
     */
    fun verifyPendingInstallation() {
        val pendingCode = preferences.getLong(KEY_PENDING_VERSION_CODE, -1L)
        if (pendingCode <= 0L) return

        val pendingName = preferences.getString(KEY_PENDING_VERSION_NAME, "desconhecida") ?: "desconhecida"
        val currentCode = try {
            currentVersionCode()
        } catch (error: Exception) {
            onState("ARS: não foi possível confirmar a instalação — ${friendlyError(error)}")
            return
        }
        val currentName = currentVersionName()

        preferences.edit()
            .remove(KEY_PENDING_VERSION_CODE)
            .remove(KEY_PENDING_VERSION_NAME)
            .remove(KEY_PENDING_AT)
            .apply()

        if (currentCode >= pendingCode && currentName == pendingName) {
            onState("ARS: atualização instalada e confirmada pelo Android — versão $currentName (código $currentCode).")
        } else {
            onState(
                "ARS: instalação não confirmada pelo Android. Continua instalada $currentName (código $currentCode); alvo $pendingName (código $pendingCode).",
            )
        }
    }

    fun shutdown() {
        executor.shutdownNow()
    }

    private fun loadValidatedRelease(): ReleaseSnapshot {
        val release = fetchLatestRelease()
        val asset = findApkAsset(release)
            ?: throw IllegalStateException("Canal inválido: nenhum APK STACY foi publicado.")

        val publishedCode = release.optLong("versionCode", -1L)
        val assetVersionCode = asset.optLong("version_code", -1L)
        val publishedName = release.optString("versionName", "").trim()
        val packageName = release.optString("packageName", "").trim()
        val publishedDigest = release.optString("sha256", "").trim().lowercase(Locale.ROOT)
        val assetDigest = asset.optString("digest", "")
            .removePrefix("sha256:")
            .trim()
            .lowercase(Locale.ROOT)
        val certificate = release.optString("signingCertificateSha256", "")
            .replace(":", "")
            .trim()
            .lowercase(Locale.ROOT)
        val minAndroid = release.optInt("minAndroid", -1)
        val currentCode = currentVersionCode()
        val currentName = currentVersionName()

        if (publishedCode <= 0L || assetVersionCode != publishedCode) {
            throw IllegalStateException("Canal inconsistente: versionCode do manifesto e do APK não coincidem.")
        }
        if (publishedName.isBlank() ||
            !publishedName.matches(Regex("[0-9A-Za-z._-]+")) ||
            packageName != appContext.packageName
        ) {
            throw IllegalStateException("Canal inválido: identidade ou versão do pacote não corresponde à STACY.")
        }
        if (asset.optString("name", "") != "$APK_PREFIX-$publishedName.apk") {
            throw IllegalStateException("Canal inconsistente: nome do ativo não corresponde à versão publicada.")
        }
        if (minAndroid < 1) {
            throw IllegalStateException("Canal inválido: versão mínima do Android não foi publicada.")
        }
        if (Build.VERSION.SDK_INT < minAndroid) {
            throw IllegalStateException("Esta atualização exige Android $minAndroid; este dispositivo usa API ${Build.VERSION.SDK_INT}.")
        }
        if (!StacyArsPolicy.isValidSha256(publishedDigest) ||
            !StacyArsPolicy.isValidSha256(assetDigest) ||
            publishedDigest != assetDigest
        ) {
            throw IllegalStateException("Canal inválido: SHA-256 do manifesto e do APK não coincidem.")
        }
        if (!StacyArsPolicy.isValidSha256(certificate)) {
            throw IllegalStateException("Canal inválido: certificado oficial não foi publicado corretamente.")
        }
        val installedCertificate = installedSigningCertificateSha256()
        if (installedCertificate == null || installedCertificate != certificate) {
            throw SecurityException("A assinatura instalada não corresponde ao certificado oficial do canal. Esta instalação não pode confirmar identidade ou atualizar com segurança.")
        }
        val downloadUrl = asset.optString("browser_download_url", "").trim()
        if (!StacyArsPolicy.isApprovedDownloadUrl(downloadUrl, publishedName)) {
            throw SecurityException("Canal inválido: o download não aponta para o APK versionado do repositório oficial.")
        }

        asset.put("signingCertificateSha256", certificate)
        asset.put("browser_download_url", downloadUrl)
        return ReleaseSnapshot(
            asset = asset,
            installedCode = currentCode,
            installedName = currentName,
            publishedCode = publishedCode,
            publishedName = publishedName,
            digest = publishedDigest,
            certificate = certificate,
            minAndroid = minAndroid,
        )
    }

    private fun fetchLatestRelease(): JSONObject {
        // A cache-busting query avoids stale raw-content CDN responses after publishing.
        val freshUrl = "$API_URL?ars_check=${System.currentTimeMillis()}"
        val connection = (URL(freshUrl).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 20_000
            instanceFollowRedirects = false
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Cache-Control", "no-cache")
            setRequestProperty("User-Agent", USER_AGENT)
        }
        return try {
            val code = connection.responseCode
            if (code == HttpURLConnection.HTTP_NOT_FOUND) {
                throw IllegalStateException("Nenhuma versão pública foi publicada no canal de atualização.")
            }
            if (code !in 200..299) {
                throw IllegalStateException("Servidor respondeu HTTP $code.")
            }
            val bytes = ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val buffer = ByteArray(8 * 1024)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    if (bytes.size() + read > MAX_MANIFEST_BYTES) {
                        throw IllegalStateException("O manifesto de atualização excede o limite seguro.")
                    }
                    bytes.write(buffer, 0, read)
                }
            }
            JSONObject(bytes.toString(Charsets.UTF_8.name()))
        } finally {
            connection.disconnect()
        }
    }

    private fun findApkAsset(release: JSONObject): JSONObject? {
        val assets = release.optJSONArray("assets") ?: return null
        for (i in 0 until assets.length()) {
            val asset = assets.optJSONObject(i) ?: continue
            val name = asset.optString("name", "")
            if (name.endsWith(".apk", ignoreCase = true) &&
                name.startsWith(APK_PREFIX, ignoreCase = true)
            ) return asset
        }
        return null
    }

    private fun downloadApk(asset: JSONObject, versionName: String): File {
        val url = asset.optString("browser_download_url", "").trim()
        if (!StacyArsPolicy.isApprovedDownloadUrl(url, versionName)) {
            throw SecurityException("O endereço de download não pertence ao canal oficial autorizado.")
        }
        val target = File(appContext.cacheDir, "stacy-update-$versionName.apk")
        if (target.exists() && !target.delete()) {
            throw IllegalStateException("Não foi possível limpar o pacote temporário anterior.")
        }

        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 60_000
            instanceFollowRedirects = false
            setRequestProperty("Accept", "application/octet-stream")
            setRequestProperty("Cache-Control", "no-cache")
            setRequestProperty("User-Agent", USER_AGENT)
        }
        var completed = false
        try {
            if (connection.responseCode !in 200..299) {
                throw IllegalStateException("Falha no download (HTTP ${connection.responseCode}).")
            }
            BufferedInputStream(connection.inputStream).use { input ->
                FileOutputStream(target).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    var total = 0L
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > MAX_APK_BYTES) {
                            throw IllegalStateException("O pacote excede o limite seguro de 250 MB.")
                        }
                        output.write(buffer, 0, read)
                    }
                    output.fd.sync()
                }
            }
            if (!target.isFile || target.length() <= 0L) {
                throw IllegalStateException("O download terminou sem produzir um APK válido.")
            }
            completed = true
            return target
        } finally {
            connection.disconnect()
            if (!completed) target.delete()
        }
    }

    private fun validateApk(
        file: File,
        asset: JSONObject,
        expectedDigest: String,
        expectedCertificate: String,
        assetVersionCode: Long,
        expectedVersionName: String,
        currentVersionCode: Long,
    ) {
        if (!file.isFile || file.length() <= 0L) {
            throw IllegalStateException("O arquivo baixado está vazio ou ausente.")
        }
        if (sha256(file) != expectedDigest) {
            throw SecurityException("A integridade SHA-256 do APK não foi confirmada.")
        }

        @Suppress("DEPRECATION")
        val signingFlags = if (Build.VERSION.SDK_INT >= 28) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            PackageManager.GET_SIGNATURES
        }
        val archiveInfo = appContext.packageManager.getPackageArchiveInfo(file.absolutePath, signingFlags)
            ?: throw IllegalStateException("O arquivo baixado não é um APK válido.")
        if (archiveInfo.packageName != appContext.packageName) {
            throw SecurityException("O pacote baixado não pertence à STACY.")
        }

        val actualCertificate = if (Build.VERSION.SDK_INT >= 28) {
            archiveInfo.signingInfo?.apkContentsSigners?.firstOrNull()?.toByteArray()
        } else {
            @Suppress("DEPRECATION")
            archiveInfo.signatures?.firstOrNull()?.toByteArray()
        }?.let { bytes ->
            MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it) }
        }
        if (actualCertificate == null || actualCertificate != expectedCertificate) {
            throw SecurityException("A assinatura do APK não corresponde ao certificado oficial publicado.")
        }

        val downloadedVersionCode = if (Build.VERSION.SDK_INT >= 28) {
            archiveInfo.longVersionCode
        } else {
            @Suppress("DEPRECATION")
            archiveInfo.versionCode.toLong()
        }
        val downloadedVersionName = archiveInfo.versionName ?: ""
        if (downloadedVersionName != expectedVersionName) {
            throw SecurityException("O versionName do APK não corresponde à versão oficial publicada.")
        }
        if (assetVersionCode <= 0L || downloadedVersionCode != assetVersionCode) {
            throw SecurityException("O versionCode do APK não corresponde ao manifesto publicado.")
        }
        if (downloadedVersionCode <= currentVersionCode) {
            throw IllegalStateException("A versão baixada não é mais recente que a instalada.")
        }
        val declaredName = asset.optString("name", "")
        if (declaredName != "$APK_PREFIX-$downloadedVersionName.apk") {
            throw SecurityException("O nome e a versão interna do APK não coincidem.")
        }
    }

    private fun installApk(file: File, targetVersionCode: Long, targetVersionName: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !appContext.packageManager.canRequestPackageInstalls()
        ) {
            onInstallIntent(
                Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${appContext.packageName}"),
                )
            )
            onState("ARS: autorize a instalação de atualizações nas configurações do Android e toque em ATUALIZAR novamente.")
            return
        }

        val uri = FileProvider.getUriForFile(
            appContext,
            "${appContext.packageName}.fileprovider",
            file,
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        preferences.edit()
            .putLong(KEY_PENDING_VERSION_CODE, targetVersionCode)
            .putString(KEY_PENDING_VERSION_NAME, targetVersionName)
            .putLong(KEY_PENDING_AT, System.currentTimeMillis())
            .apply()
        try {
            onInstallIntent(intent)
        } catch (error: Exception) {
            preferences.edit()
                .remove(KEY_PENDING_VERSION_CODE)
                .remove(KEY_PENDING_VERSION_NAME)
                .remove(KEY_PENDING_AT)
                .apply()
            throw error
        }
    }

    private fun installedSigningCertificateSha256(): String? {
        @Suppress("DEPRECATION")
        val signingFlags = if (Build.VERSION.SDK_INT >= 28) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            PackageManager.GET_SIGNATURES
        }
        val info = if (Build.VERSION.SDK_INT >= 33) {
            appContext.packageManager.getPackageInfo(
                appContext.packageName,
                PackageManager.PackageInfoFlags.of(signingFlags.toLong()),
            )
        } else {
            @Suppress("DEPRECATION")
            appContext.packageManager.getPackageInfo(appContext.packageName, signingFlags)
        }
        val certificateBytes = if (Build.VERSION.SDK_INT >= 28) {
            info.signingInfo?.apkContentsSigners?.firstOrNull()?.toByteArray()
        } else {
            @Suppress("DEPRECATION")
            info.signatures?.firstOrNull()?.toByteArray()
        } ?: return null
        return MessageDigest.getInstance("SHA-256").digest(certificateBytes)
            .joinToString("") { "%02x".format(it) }
    }

    private fun currentVersionCode(): Long = installedPackageInfo().let { info ->
        if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else info.versionCode.toLong()
    }

    private fun currentVersionName(): String =
        installedPackageInfo().versionName?.takeIf { it.isNotBlank() } ?: "desconhecida"

    private fun installedPackageInfo() =
        if (Build.VERSION.SDK_INT >= 33) {
            appContext.packageManager.getPackageInfo(
                appContext.packageName,
                PackageManager.PackageInfoFlags.of(0),
            )
        } else {
            @Suppress("DEPRECATION")
            appContext.packageManager.getPackageInfo(appContext.packageName, 0)
        }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun friendlyError(error: Throwable): String =
        error.message?.trim().orEmpty().ifBlank { "não foi possível concluir a verificação." }
}
