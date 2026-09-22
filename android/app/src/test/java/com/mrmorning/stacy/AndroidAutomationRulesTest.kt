package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AndroidAutomationRulesTest {

    @Test
    fun blankPackageIsRejected() {
        assertEquals(
            "INVALID_PACKAGE",
            AndroidAutomationRules.packageNameError("   "),
        )
    }

    @Test
    fun validPackageIsAccepted() {
        assertNull(AndroidAutomationRules.packageNameError("com.android.settings"))
    }

    @Test
    fun invalidCalendarIntervalIsRejected() {
        assertEquals(
            "INVALID_INTERVAL",
            AndroidAutomationRules.calendarError("Aula", 2_000L, 1_000L),
        )
    }

    @Test
    fun emptyNotificationIsRejected() {
        assertEquals(
            "INVALID_NOTIFICATION",
            AndroidAutomationRules.notificationError("STACY", " "),
        )
    }

    @Test
    fun emptyShareTextIsRejected() {
        assertEquals(
            "EMPTY_TEXT",
            AndroidAutomationRules.shareTextError(" "),
        )
    }
}
