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
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.Executors

class StacyUpdater(
    private val context: Context,
    private val onState: (String) -> Unit,
) {
    companion object {
        private const val API_URL =
            "https://raw.githubusercontent.com/MrMorningw/STACY---UPTADES-DEFINITIVO/main/update.json"
        private const val USER_AGENT = "STACY-Updater/1.0"
        private const val APK_PREFIX = "STACY"
    }

    private val executor = Executors.newSingleThreadExecutor()

    fun checkAndUpdate() {
        onState("Verificando atualizações da STACY…")
        executor.execute {
            try {
                val release = fetchLatestRelease()
                val asset = findApkAsset(release)
                    ?: throw IllegalStateException("Canal inválido: nenhum APK STACY foi publicado.")
                val publishedCode = release.optInt("versionCode", -1)
                val assetVersionCode = asset.optInt("version_code", -1)
                val publishedName = release.optString("versionName", "").trim()
                val packageName = release.optString("packageName", "").trim()
                val publishedDigest = release.optString("sha256", "").trim().lowercase()
                val assetDigest = asset.optString("digest", "").removePrefix("sha256:").trim().lowercase()
                val certificate = release.optString("signingCertificateSha256", "").replace(":", "").trim().lowercase()

                if (publishedCode <= 0 || assetVersionCode != publishedCode) {
                    throw IllegalStateException("Canal inconsistente: versionCode do manifesto e do APK não coincidem.")
                }
                if (publishedName.isBlank() || packageName != context.packageName) {
                    throw IllegalStateException("Canal inválido: identidade ou versão do pacote não corresponde à STACY.")
                }
                if (!publishedDigest.matches(Regex("[a-f0-9]{64}")) || publishedDigest != assetDigest) {
                    throw IllegalStateException("Canal inválido: SHA-256 do manifesto e do APK não coincidem.")
                }
                if (!certificate.matches(Regex("[a-f0-9]{64}"))) {
                    throw IllegalStateException("Canal inválido: certificado oficial não foi publicado corretamente.")
                }
                asset.put("signingCertificateSha256", certificate)
                val currentCode = currentVersionCode()
                val currentName = currentVersionName()

                if (publishedCode == currentCode && publishedName == currentName) {
                    onState("Verificação concluída: instalada $currentName (código $currentCode); canal oficial $publishedName (código $publishedCode). Não há versão mais nova publicada.")
                    return@execute
                }
                if (publishedCode < currentCode) {
                    throw IllegalStateException("Canal desatualizado: instalada $currentName (código $currentCode), mas o canal publica $publishedName (código $publishedCode). Não é seguro afirmar que a STACY está atualizada.")
                }
                if (publishedCode == currentCode && publishedName != currentName) {
                    throw IllegalStateException("Canal inconsistente: o código instalado coincide, mas o nome da versão difere (instalada $currentName; publicada $publishedName).")
                }

                onState("Nova versão confirmada: $currentName → $publishedName. Baixando e validando pacote…")
                val file = downloadApk(asset)
                validateApk(file, asset, assetVersionCode, currentCode)
                onState("Integridade e assinatura confirmadas para $publishedName. Abrindo instalador do Android…")
                installApk(file)
            } catch (e: Exception) {
                onState("Atualização indisponível: ${friendlyError(e)}")
            }
        }
    }

    private fun fetchLatestRelease(): JSONObject {
        val connection = (URL(API_URL).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/vnd.github+json")
            setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
            setRequestProperty("User-Agent", USER_AGENT)
        }
        return try {
            val code = connection.responseCode
            if (code == HttpURLConnection.HTTP_NOT_FOUND) {
                throw IllegalStateException(
                    "Nenhuma versão pública foi publicada no canal de atualização."
                )
            }
            if (code !in 200..299) {
                throw IllegalStateException("Servidor respondeu HTTP $code.")
            }
            JSONObject(connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
        } finally {
            connection.disconnect()
        }
    }

    private fun findApkAsset(release: JSONObject): JSONObject? {
        val assets = release.optJSONArray("assets") ?: return null
        for (i in 0 until assets.length()) {
            val asset = assets.getJSONObject(i)
            val name = asset.optString("name", "")
            if (name.endsWith(".apk", ignoreCase = true) &&
                name.startsWith(APK_PREFIX, ignoreCase = true)
            ) return asset
        }
        return null
    }

    private fun downloadApk(asset: JSONObject): File {
        val url = asset.optString("browser_download_url").ifBlank {
            throw IllegalStateException("O pacote da atualização não possui endereço de download.")
        }
        val target = File(context.cacheDir, "stacy-update.apk")
        if (target.exists()) target.delete()

        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 60_000
            instanceFollowRedirects = true
            setRequestProperty("Accept", "application/octet-stream")
            setRequestProperty("User-Agent", USER_AGENT)
        }
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
                        output.write(buffer, 0, read)
                        total += read
                        if (total > 250L * 1024L * 1024L) {
                            throw IllegalStateException("O pacote excede o limite seguro de 250 MB.")
                        }
                    }
                    output.fd.sync()
                }
            }
        } finally {
            connection.disconnect()
        }
        return target
    }

    private fun validateApk(file: File, asset: JSONObject, assetVersionCode: Int, currentVersionCode: Long) {
        val expectedDigest = asset.optString("digest", "")
            .removePrefix("sha256:")
            .lowercase()
        if (expectedDigest.isBlank()) {
            throw IllegalStateException("O servidor não publicou a assinatura SHA-256 do APK.")
        }
        if (sha256(file) != expectedDigest) {
            throw SecurityException("A integridade do APK não foi confirmada.")
        }

        @Suppress("DEPRECATION")
        val signingFlags = if (Build.VERSION.SDK_INT >= 28) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            PackageManager.GET_SIGNATURES
        }
        val archiveInfo = context.packageManager.getPackageArchiveInfo(file.absolutePath, signingFlags)
            ?: throw IllegalStateException("O arquivo baixado não é um APK válido.")
        if (archiveInfo.packageName != context.packageName) {
            throw SecurityException("O pacote baixado não pertence à STACY.")
        }

        val expectedCertificate = asset.optString("signingCertificateSha256", "")
            .ifBlank { "" }
            .replace(":", "")
            .lowercase()
        // The publisher stores the certificate digest at the top level of update.json.
        // Pass it through the selected asset when validating the downloaded APK.
        val actualCertificate = if (Build.VERSION.SDK_INT >= 28) {
            archiveInfo.signingInfo?.apkContentsSigners?.firstOrNull()?.toByteArray()
        } else {
            @Suppress("DEPRECATION")
            archiveInfo.signatures?.firstOrNull()?.toByteArray()
        }?.let { bytes ->
            MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it) }
        }
        if (expectedCertificate.isNotBlank() &&
            (actualCertificate == null || actualCertificate != expectedCertificate)
        ) {
            throw SecurityException("A assinatura do APK não corresponde ao certificado publicado.")
        }

        val downloadedVersionCode = if (Build.VERSION.SDK_INT >= 28) {
            archiveInfo.longVersionCode
        } else {
            @Suppress("DEPRECATION")
            archiveInfo.versionCode.toLong()
        }
        if (assetVersionCode > 0 && downloadedVersionCode != assetVersionCode.toLong()) {
            throw SecurityException("A versão do APK não corresponde à versão publicada.")
        }
        if (downloadedVersionCode <= currentVersionCode) {
            throw IllegalStateException("A versão baixada não é mais recente que a instalada.")
        }
    }

    private fun installApk(file: File) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !context.packageManager.canRequestPackageInstalls()
        ) {
            context.startActivity(
                Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${context.packageName}"),
                ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            onState("Autorize a STACY a instalar atualizações e toque novamente em ATUALIZAR STACY.")
            return
        }

        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        context.startActivity(Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        })
    }

    private fun currentVersionCode(): Long = installedPackageInfo().let { info ->
        if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else info.versionCode.toLong()
    }

    private fun currentVersionName(): String =
        installedPackageInfo().versionName?.takeIf { it.isNotBlank() } ?: "desconhecida"

    private fun installedPackageInfo() =
        if (Build.VERSION.SDK_INT >= 33) {
            context.packageManager.getPackageInfo(
                context.packageName,
                PackageManager.PackageInfoFlags.of(0),
            )
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(context.packageName, 0)
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
