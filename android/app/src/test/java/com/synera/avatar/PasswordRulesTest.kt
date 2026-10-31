package com.synera.avatar

import com.synera.avatar.util.PasswordRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Telefondaki kural sunucudakiyle aynı olmalı (backend/app/services/auth.py, tests/test_users_roles.py). */
class PasswordRulesTest {
    private fun problem(new: String, repeat: String = new, current: String = "gecici123") =
        PasswordRules.problem(current, new, repeat)

    @Test
    fun `gecerli sifre kabul edilir`() {
        assertNull(problem("kendisifrem9"))
        assertNull(problem("abcd!@#\$")) // harf + simge: sunucu da kabul eder
    }

    @Test
    fun `kisa, yalniz harf ya da yalniz rakam reddedilir`() {
        assertEquals("Yeni şifre en az 8 karakter olmalı.", problem("abc12"))
        assertEquals("Yeni şifrede hem harf hem rakam olmalı.", problem("yalnizharf"))
        assertEquals("Yeni şifrede hem harf hem rakam olmalı.", problem("12345678"))
    }

    @Test
    fun `eskisiyle ayni, tekrari farkli ya da mevcut bos reddedilir`() {
        assertEquals("Yeni şifre eskisiyle aynı olamaz.", problem("gecici123"))
        assertEquals("Yeni şifre ile tekrarı aynı değil.", problem("kendisifrem9", repeat = "kendisifrem8"))
        assertEquals("Mevcut şifrenizi yazın.", problem("kendisifrem9", current = ""))
    }
}
