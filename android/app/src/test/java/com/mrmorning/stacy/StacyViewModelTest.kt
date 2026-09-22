package com.mrmorning.stacy

import org.junit.Assert.assertEquals
import org.junit.Test

class StacyViewModelTest {
    @Test
    fun inputIsStoredInUiState() {
        val viewModel = StacyViewModel()

        viewModel.onInputChanged("oi stacy")

        assertEquals("oi stacy", viewModel.uiState.input)
    }

    @Test
    fun sendAddsUserMessageAndClearsInput() {
        val viewModel = StacyViewModel()

        viewModel.onInputChanged("oi stacy")
        viewModel.onSend()

        assertEquals("", viewModel.uiState.input)
        assertEquals("oi stacy", viewModel.uiState.messages.last().text)
        assertEquals(true, viewModel.uiState.messages.last().fromUser)
    }

    @Test
    fun blankInputDoesNotCreateMessage() {
        val viewModel = StacyViewModel()
        val initialSize = viewModel.uiState.messages.size

        viewModel.onInputChanged("   ")
        viewModel.onSend()

        assertEquals(initialSize, viewModel.uiState.messages.size)
    }
}
