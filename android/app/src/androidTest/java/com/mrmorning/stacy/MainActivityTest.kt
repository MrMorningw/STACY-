package com.mrmorning.stacy

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Rule
import org.junit.Test

class MainActivityTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun stacyHomeScreenIsDisplayed() {
        composeRule.setContent {
            StacyTheme {
                StacyApp()
            }
        }

        composeRule.onNodeWithText("STACY").assertIsDisplayed()
        composeRule.onNodeWithText("Boa tarde, senhor. Estou pronta.").assertIsDisplayed()
        composeRule.onNodeWithText("Mensagem para STACY").assertIsDisplayed()
    }
}
