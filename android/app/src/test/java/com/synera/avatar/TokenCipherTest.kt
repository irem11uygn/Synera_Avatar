package com.synera.avatar

import com.synera.avatar.data.repo.TokenCipher
import java.util.Base64
import javax.crypto.KeyGenerator
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Telefonda anahtar Keystore'dan gelir; burada aynı algoritma JVM'nin ürettiği anahtarla sınanır. */
class TokenCipherTest {
    private fun newKey() = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

    private val key = newKey()
    private val cipher = TokenCipher { key }
    private val plain = "ornek-oturum-degeri-0001" // uydurma, gerçek belirteç değil

    @Test
    fun `sifrelenen belirtec ayni anahtarla geri acilir`() {
        assertEquals(plain, cipher.open(cipher.seal(plain)))
    }

    @Test
    fun `saklanan metinde belirtec duz olarak gecmez ve her seferinde farklidir`() {
        val first = cipher.seal(plain)
        assertTrue(first.startsWith("v1:"))
        assertFalse(first.contains(plain))
        assertNotEquals(first, cipher.seal(plain)) // her şifrelemede yeni IV
    }

    @Test
    fun `degistirilmis icerik acilmaz`() {
        val bytes = Base64.getDecoder().decode(cipher.seal(plain).removePrefix("v1:"))
        bytes[bytes.size - 1] = (bytes[bytes.size - 1].toInt() xor 1).toByte()
        assertNull(cipher.open("v1:" + Base64.getEncoder().encodeToString(bytes)))
    }

    @Test
    fun `baska anahtarla ya da bozuk bicimde acilmaz`() {
        val sealed = cipher.seal(plain)
        val otherKey = newKey()
        assertNull(TokenCipher { otherKey }.open(sealed)) // başka cihaz / yeniden kurulum
        assertNull(cipher.open(plain)) // eski sürümün şifresiz değeri
        assertNull(cipher.open("v1:%%%"))
        assertNull(cipher.open("v1:"))
    }
}
