package com.mrmorning.stacy

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.CalendarContract
import android.provider.Settings
import java.util.concurrent.atomic.AtomicInteger

sealed interface AutomationResult {
    data class Success(val message: String) : AutomationResult
    data class Failure(val code: String, val message: String) : AutomationResult
}

interface StacyAndroidAutomation {
    fun openApplication(packageName: String): AutomationResult
    fun openSettings(): AutomationResult
    fun createCalendarEvent(
        title: String,
        startMillis: Long,
        endMillis: Long,
        description: String? = null,
    ): AutomationResult
    fun shareText(text: String, title: String = "STACY"): AutomationResult
    fun pickFile(mimeType: String = "*/*"): AutomationResult
    fun postNotification(title: String, text: String): AutomationResult
}

class AndroidAutomation(
    private val context: Context,
) : StacyAndroidAutomation {

    override fun openApplication(packageName: String): AutomationResult {
        val normalized = packageName.trim()
        if (AndroidAutomationRules.packageNameError(normalized) != null) {
            return AutomationResult.Failure("INVALID_PACKAGE", "Pacote do aplicativo não informado.")
        }

        val launchIntent = context.packageManager.getLaunchIntentForPackage(normalized)
            ?: return AutomationResult.Failure(
                "APP_NOT_FOUND",
                "Não encontrei um aplicativo iniciável para: $normalized",
            )

        return startActivity(launchIntent)
    }

    override fun openSettings(): AutomationResult =
        startActivity(Intent(Settings.ACTION_SETTINGS))

    override fun createCalendarEvent(
        title: String,
        startMillis: Long,
        endMillis: Long,
        description: String?,
    ): AutomationResult {
        val normalizedTitle = title.trim()
        when (AndroidAutomationRules.calendarError(normalizedTitle, startMillis, endMillis)) {
            "INVALID_TITLE" -> return AutomationResult.Failure(
                "INVALID_TITLE",
                "O título do evento não pode ser vazio.",
            )
            "INVALID_INTERVAL" -> return AutomationResult.Failure(
                "INVALID_INTERVAL",
                "O horário final deve ser posterior ao horário inicial.",
            )
        }

        val intent = Intent(Intent.ACTION_INSERT).apply {
            data = CalendarContract.Events.CONTENT_URI
            putExtra(CalendarContract.Events.TITLE, normalizedTitle)
            putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMillis)
            putExtra(CalendarContract.EXTRA_EVENT_END_TIME, endMillis)
            description?.trim()?.takeIf { it.isNotEmpty() }?.let {
                putExtra(CalendarContract.Events.DESCRIPTION, it)
            }
        }

        return startActivity(intent)
    }

    override fun shareText(text: String, title: String): AutomationResult {
        val normalizedText = text.trim()
        if (AndroidAutomationRules.shareTextError(normalizedText) != null) {
            return AutomationResult.Failure("EMPTY_TEXT", "Não há texto para compartilhar.")
        }

        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, normalizedText)
        }
        return startActivity(
            Intent.createChooser(intent, title.trim().ifEmpty { "STACY" }),
        )
    }

    override fun pickFile(mimeType: String): AutomationResult {
        val normalizedType = mimeType.trim().ifEmpty { "*/*" }
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            type = normalizedType
            addCategory(Intent.CATEGORY_OPENABLE)
        }
        return startActivity(intent)
    }

    override fun postNotification(title: String, text: String): AutomationResult {
        val normalizedTitle = title.trim()
        val normalizedText = text.trim()

        if (AndroidAutomationRules.notificationError(normalizedTitle, normalizedText) != null) {
            return AutomationResult.Failure(
                "INVALID_NOTIFICATION",
                "Título e texto da notificação são obrigatórios.",
            )
        }

        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return AutomationResult.Failure(
                "NOTIFICATION_PERMISSION_REQUIRED",
                "A permissão de notificações precisa ser concedida pelo usuário.",
            )
        }

        val manager = context.getSystemService(NotificationManager::class.java)
            ?: return AutomationResult.Failure(
                "NOTIFICATION_UNAVAILABLE",
                "O serviço de notificações do Android não está disponível.",
            )

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    NOTIFICATION_CHANNEL_ID,
                    "STACY",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ).apply {
                    description = "Notificações da STACY"
                },
            )
        }

        val notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            android.app.Notification.Builder(context, NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(normalizedTitle)
                .setContentText(normalizedText)
                .setAutoCancel(true)
                .build()
        } else {
            @Suppress("DEPRECATION")
            android.app.Notification.Builder(context)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(normalizedTitle)
                .setContentText(normalizedText)
                .setAutoCancel(true)
                .build()
        }

        manager.notify(NOTIFICATION_ID.getAndIncrement(), notification)
        return AutomationResult.Success("Notificação enviada.")
    }

    private fun startActivity(intent: Intent): AutomationResult =
        try {
            context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            AutomationResult.Success("Ação Android executada.")
        } catch (_: ActivityNotFoundException) {
            AutomationResult.Failure(
                "ACTIVITY_NOT_FOUND",
                "O Android não encontrou um aplicativo capaz de executar essa ação.",
            )
        } catch (_: SecurityException) {
            AutomationResult.Failure(
                "SECURITY_RESTRICTION",
                "O Android bloqueou essa ação por segurança ou permissão.",
            )
        }

    companion object {
        private const val NOTIFICATION_CHANNEL_ID = "stacy_general"
        private val NOTIFICATION_ID = AtomicInteger(1000)
    }
}
