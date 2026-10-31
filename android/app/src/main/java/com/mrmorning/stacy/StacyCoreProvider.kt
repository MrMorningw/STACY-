package com.mrmorning.stacy

import android.content.Context

/**
 * Stable boundary between the Android application and a replaceable STACY CORE.
 *
 * Implementations must return exactly one CoreResult for every accepted request.
 * Callbacks may arrive on any thread; CoreResultStore marshals delivery to main.
 */
interface StacyCoreProvider {
    val providerId: String

    fun process(message: String, callback: (CoreResult) -> Unit)

    fun testConnection(callback: (CoreResult) -> Unit)

    fun shutdown() {}
}

/**
 * Safe detached state: no legacy Gemini, Kotlin fast-path, Python, or Termux
 * implementation is invoked until a replacement provider is explicitly wired.
 */
internal class UnconfiguredStacyCoreProvider : StacyCoreProvider {
    override val providerId: String = "unconfigured"

    override fun process(message: String, callback: (CoreResult) -> Unit) {
        callback(unavailable())
    }

    override fun testConnection(callback: (CoreResult) -> Unit) {
        callback(unavailable())
    }

    private fun unavailable() = CoreResult(
        tipo = "erro",
        response = "Nenhum núcleo de inteligência está conectado. A interface está desacoplada e aguarda a integração de um CORE compatível.",
        exitCode = 2,
        stderr = "CORE_PROVIDER_NOT_CONFIGURED",
    )
}

/** Single composition point. Replace this factory when the new CORE is selected. */
internal object StacyCoreProviderFactory {
    fun create(context: Context): StacyCoreProvider = UnconfiguredStacyCoreProvider()
}
