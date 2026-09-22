package com.mrmorning.stacy

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
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
                StacyApp(StacyViewModel())
            }
        }

        composeRule.onNodeWithText("STACY").assertIsDisplayed()
        composeRule.onNodeWithText("Boa tarde, senhor. Estou pronta.").assertIsDisplayed()
        composeRule.onNodeWithText("Mensagem para STACY").assertIsDisplayed()
    }

    @Test
    fun userMessageAppearsAfterSend() {
        composeRule.setContent {
            StacyTheme {
                StacyApp(StacyViewModel())
            }
        }

        composeRule.onNodeWithText("Mensagem para STACY").performTextInput("oi stacy")
        composeRule.onNodeWithText("Enviar").performClick()
        composeRule.onNodeWithText("oi stacy").assertIsDisplayed()
    }
}
