package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StacyArsPolicyTest {
    @Test
    fun reportsUpToDateOnlyWhenCodeAndNameMatch() {
        val decision = StacyArsPolicy.evaluate(28, "0.3.7", 28, "0.3.7")
        assertEquals(StacyArsPolicy.ChannelState.UP_TO_DATE, decision.state)
        assertTrue(decision.message.contains("coincide"))
    }

    @Test
    fun reportsAvailableWhenPublishedBuildIsNewer() {
        val decision = StacyArsPolicy.evaluate(28, "0.3.7", 29, "0.3.8")
        assertEquals(StacyArsPolicy.ChannelState.UPDATE_AVAILABLE, decision.state)
        assertTrue(decision.message.contains("nova versão"))
    }

    @Test
    fun neverClaimsUpToDateWhenPublishedChannelIsBehind() {
        val decision = StacyArsPolicy.evaluate(29, "0.3.8", 28, "0.3.7")
        assertEquals(StacyArsPolicy.ChannelState.CHANNEL_OUTDATED, decision.state)
        assertTrue(decision.message.contains("canal desatualizado"))
        assertFalse(decision.message.contains("Nenhuma atualização nova"))
    }

    @Test
    fun reportsInconsistentWhenVersionCodeMatchesButNameDiffers() {
        val decision = StacyArsPolicy.evaluate(29, "0.3.8", 29, "0.3.9")
        assertEquals(StacyArsPolicy.ChannelState.CHANNEL_INCONSISTENT, decision.state)
    }

    @Test
    fun rejectsMissingOrMalformedVersionMetadata() {
        assertEquals(
            StacyArsPolicy.ChannelState.CHANNEL_INCONSISTENT,
            StacyArsPolicy.evaluate(29, "0.3.8", -1, ""),
        )
        assertFalse(StacyArsPolicy.isValidSha256(""))
        assertFalse(StacyArsPolicy.isValidSha256("abc"))
        assertTrue(StacyArsPolicy.isValidSha256("a".repeat(64)))
    }

    @Test
    fun acceptsOnlyTheVersionedOfficialReleasePath() {
        val approved = "https://raw.githubusercontent.com/MrMorningw/STACY---UPTADES-DEFINITIVO/main/releases/STACY-0.3.8.apk"
        assertTrue(StacyArsPolicy.isApprovedDownloadUrl(approved, "0.3.8"))
        assertFalse(StacyArsPolicy.isApprovedDownloadUrl("http://raw.githubusercontent.com/MrMorningw/STACY---UPTADES-DEFINITIVO/main/releases/STACY-0.3.8.apk", "0.3.8"))
        assertFalse(StacyArsPolicy.isApprovedDownloadUrl("https://example.com/STACY-0.3.8.apk", "0.3.8"))
        assertFalse(StacyArsPolicy.isApprovedDownloadUrl("https://raw.githubusercontent.com/attacker/repo/main/releases/STACY-0.3.8.apk", "0.3.8"))
        assertFalse(StacyArsPolicy.isApprovedDownloadUrl("$approved?mirror=1", "0.3.8"))
        assertFalse(StacyArsPolicy.isApprovedDownloadUrl(approved, "../0.3.8"))
    }
}
