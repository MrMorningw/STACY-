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
            "https://raw.githubusercontent.com/MrMorningw/STACY--UPDATES-DEFINITIVO/main/update.json"
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
                    ?: throw IllegalStateException("A versão publicada não possui um APK STACY.")
                val assetVersionCode = asset.optInt("version_code", -1)
                val currentVersionCode = currentVersionCode()

                if (assetVersionCode > 0 && assetVersionCode <= currentVersionCode) {
                    onState("A STACY já está atualizada.")
                    return@execute
                }

                val file = downloadApk(asset)
                validateApk(file, asset, assetVersionCode, currentVersionCode)
                onState("Atualização pronta. Abrindo o instalador…")
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
            setRequestProperty("X-GitHub-Api-Version", "2026-03-10")
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

        val archiveInfo = context.packageManager.getPackageArchiveInfo(file.absolutePath, 0)
            ?: throw IllegalStateException("O arquivo baixado não é um APK válido.")
        if (archiveInfo.packageName != context.packageName) {
            throw SecurityException("O pacote baixado não pertence à STACY.")
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

    private fun currentVersionCode(): Long =
        if (Build.VERSION.SDK_INT >= 33) {
            context.packageManager.getPackageInfo(
                context.packageName,
                PackageManager.PackageInfoFlags.of(0),
            ).longVersionCode
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(context.packageName, 0).versionCode.toLong()
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
