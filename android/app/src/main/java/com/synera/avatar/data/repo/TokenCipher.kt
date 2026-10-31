package com.synera.avatar.data.repo

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.GeneralSecurityException
import java.security.KeyStore
import java.security.ProviderException
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Oturum belirtecini AES-GCM ile şifreler. Telefonda anahtar Android Keystore'da üretilir ve
 * dışarı çıkarılamaz; kopyalanan ayar dosyası başka cihazda ya da yeniden kurulumdan sonra açılmaz.
 * Saklanan biçim: "v1:" + Base64(12 baytlık IV + şifreli metin + 16 baytlık doğrulama etiketi).
 */
class TokenCipher(private val key: () -> SecretKey) {

    fun seal(plain: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val sealed = cipher.iv + cipher.doFinal(plain.toByteArray(Charsets.UTF_8))
        return PREFIX + Base64.getEncoder().encodeToString(sealed)
    }

    /** Biçim bozuk, içerik değiştirilmiş ya da anahtar farklıysa null (kullanıcı yeniden giriş yapar). */
    fun open(stored: String): String? {
        if (!stored.startsWith(PREFIX)) return null
        return try {
            val bytes = Base64.getDecoder().decode(stored.removePrefix(PREFIX))
            if (bytes.size <= IV_BYTES) return null
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, bytes, 0, IV_BYTES))
            String(cipher.doFinal(bytes, IV_BYTES, bytes.size - IV_BYTES), Charsets.UTF_8)
        } catch (e: GeneralSecurityException) {
            null
        } catch (e: IllegalArgumentException) {
            null
        } catch (e: ProviderException) {
            null
        }
    }

    companion object {
        private const val PREFIX = "v1:"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val IV_BYTES = 12
        private const val TAG_BITS = 128
        private const val KEYSTORE = "AndroidKeyStore"
        private const val ALIAS = "avatar_oturum"

        fun keystore(): TokenCipher = TokenCipher(::keystoreKey)

        private fun keystoreKey(): SecretKey {
            val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
            (store.getKey(ALIAS, null) as? SecretKey)?.let { return it }
            val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
            generator.init(
                KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build(),
            )
            return generator.generateKey()
        }
    }
}
