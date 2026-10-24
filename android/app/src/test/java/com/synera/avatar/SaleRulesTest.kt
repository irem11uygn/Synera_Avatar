package com.synera.avatar

import com.synera.avatar.data.repo.SaleRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SaleRulesTest {
    @Test
    fun `satir tutari sunucudaki gibi kurusa yarim yukari yuvarlanir`() {
        assertEquals(74700L, SaleRules.amountCents(30_000, 2490)) // 30 × 24,90 = 747,00 €
        assertEquals(4800L, SaleRules.amountCents(4_000, 1200)) // 4 kg × 12,00 = 48,00 €
    }

    @Test
    fun `yarim kurus yukari yuvarlanir`() {
        assertEquals(416L, SaleRules.amountCents(333, 1250)) // 4,1625 → 4,16
        assertEquals(13L, SaleRules.amountCents(125, 100)) // 0,125 → 0,13
    }

    @Test
    fun `bloke lot satilamaz ve miktar kullanilabiliri asamaz`() {
        assertTrue(SaleRules.lineError("ADET", "BLOKE", 1_000, 85_000)!!.contains("bloke"))
        assertNull(SaleRules.lineError("ADET", "AKTIF", 30_000, 85_000))
        assertEquals(
            "Araçta kullanılabilir miktar: 55 adet.",
            SaleRules.lineError("ADET", "AKTIF", 60_000, 85_000, alreadyInDraftMilli = 30_000),
        )
    }

    @Test
    fun `adet urunde kesirli miktar ve gecersiz giris reddedilir`() {
        assertTrue(SaleRules.lineError("ADET", "AKTIF", 1_500, 85_000)!!.contains("tam sayı"))
        assertNull(SaleRules.lineError("KG", "AKTIF", 1_500, 85_000))
        assertTrue(SaleRules.lineError("KG", "AKTIF", null, 85_000)!!.contains("Geçerli"))
        assertTrue(SaleRules.lineError("KG", "AKTIF", 0, 85_000)!!.contains("sıfırdan büyük"))
    }
}
