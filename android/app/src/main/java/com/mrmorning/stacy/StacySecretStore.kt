package com.mrmorning.stacy

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Encrypted storage for the user's Gemini API key.
 * The AES key is generated and kept by Android Keystore; plaintext is not persisted.
 */
internal class StacySecretStore(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun hasGeminiApiKey(): Boolean = getGeminiApiKey() != null

    fun getGeminiApiKey(): String? = synchronized(LOCK) {
        val encoded = preferences.getString(ENCRYPTED_KEY, null) ?: return@synchronized null
        try {
            val envelope = Base64.decode(encoded, Base64.NO_WRAP)
            if (envelope.size <= IV_BYTES) {
                preferences.edit().remove(ENCRYPTED_KEY).apply()
                return@synchronized null
            }
            val iv = envelope.copyOfRange(0, IV_BYTES)
            val ciphertext = envelope.copyOfRange(IV_BYTES, envelope.size)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), GCMParameterSpec(TAG_BITS, iv))
            String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8).trim().takeIf { it.isNotEmpty() }
        } catch (_: Exception) {
            // This can occur after an app restore where the old Keystore key is unavailable.
            preferences.edit().remove(ENCRYPTED_KEY).apply()
            null
        }
    }

    fun saveGeminiApiKey(value: String) = synchronized(LOCK) {
        val cleaned = value.trim()
        require(cleaned.isNotEmpty()) { "Informe uma chave Gemini API válida." }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(cleaned.toByteArray(StandardCharsets.UTF_8))
        val envelope = ByteArray(iv.size + ciphertext.size)
        System.arraycopy(iv, 0, envelope, 0, iv.size)
        System.arraycopy(ciphertext, 0, envelope, iv.size, ciphertext.size)
        preferences.edit().putString(ENCRYPTED_KEY, Base64.encodeToString(envelope, Base64.NO_WRAP)).apply()
    }

    fun clearGeminiApiKey() = synchronized(LOCK) {
        preferences.edit().remove(ENCRYPTED_KEY).apply()
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val existing = keyStore.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setKeySize(256)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val PREFERENCES = "stacy_secure_settings"
        const val ENCRYPTED_KEY = "gemini_api_key_encrypted"
        const val KEY_ALIAS = "stacy.gemini.api-key.aes"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
        const val TAG_BITS = 128
        val LOCK = Any()
    }
}
