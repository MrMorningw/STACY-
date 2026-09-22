package com.mrmorning.stacy

object AndroidAutomationRules {
    fun packageNameError(packageName: String): String? =
        if (packageName.trim().isEmpty()) "INVALID_PACKAGE" else null

    fun calendarError(title: String, startMillis: Long, endMillis: Long): String? =
        when {
            title.trim().isEmpty() -> "INVALID_TITLE"
            endMillis <= startMillis -> "INVALID_INTERVAL"
            else -> null
        }

    fun notificationError(title: String, text: String): String? =
        if (title.trim().isEmpty() || text.trim().isEmpty()) {
            "INVALID_NOTIFICATION"
        } else {
            null
        }

    fun shareTextError(text: String): String? =
        if (text.trim().isEmpty()) "EMPTY_TEXT" else null
}
