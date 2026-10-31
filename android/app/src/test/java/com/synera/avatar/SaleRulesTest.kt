package com.synera.avatar

import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.repo.SaleRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class SaleRulesTest {
    private val today = LocalDate.of(2026, 10, 28)

    private fun lot(id: Long, no: String, available: Long, expiry: String?, status: String = "AKTIF", product: Long = 5) =
        VanStockRow(id, no, product, "Narin sucuk", "ADET", 2490, available, available, status, expiry)

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
    fun `geri cagrilmis ve suresi gecmis lot satilamaz, miktar kullanilabiliri asamaz`() {
        assertTrue(SaleRules.lineError("ADET", "BLOKE", 1_000, 85_000)!!.contains("geri çağrıldı"))
        assertTrue(SaleRules.lineError("ADET", "AKTIF", 1_000, 85_000, expired = true)!!.contains("son kullanma"))
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

    @Test
    fun `ilk dolan lottan baslar, gecmis ve geri cagrilmis lotu atlar`() {
        val lots = listOf(
            lot(1, "SUC-3", 10_000, "2026-11-20"),
            lot(2, "SUC-1", 4_000, "2026-11-02"),
            lot(3, "SUC-OLD", 9_000, "2026-10-20"),
            lot(4, "SUC-BLK", 9_000, "2026-11-01", status = "BLOKE"),
            lot(5, "BASKA", 9_000, "2026-10-30", product = 7),
        )
        val (picks, short) = SaleRules.allocate(lots, productId = 5, qtyMilli = 6_000, today = today)
        assertEquals(listOf("SUC-1" to 4_000L, "SUC-3" to 2_000L), picks.map { it.lot.lotNo to it.qtyMilli })
        assertEquals(0L, short)
    }

    @Test
    fun `dort saatten eski ya da hic yapilmamis esitleme bayat sayilir`() {
        val now = 1_000_000_000L
        val hour = 60 * 60 * 1000L
        assertTrue(SaleRules.isStale(null, now))
        assertTrue(SaleRules.isStale(now - 4 * hour - 1, now))
        assertFalse(SaleRules.isStale(now - 4 * hour, now))
        assertFalse(SaleRules.isStale(now - 10 * 60 * 1000L, now))
    }

    @Test
    fun `liste fiyatinin altindaki satis yuzdesiyle bulunur`() {
        assertEquals(20, SaleRules.discountPercent(1200, 1500))
        assertEquals(1, SaleRules.discountPercent(2489, 2490)) // 1 kuruş altı bile görünür
        assertNull(SaleRules.discountPercent(2490, 2490))
        assertNull(SaleRules.discountPercent(2600, 2490)) // liste üstü indirim değildir
        assertNull(SaleRules.discountPercent(1000, null)) // liste fiyatı tanımsız
    }

    @Test
    fun `taslaga ayrilan miktar dusulur, yetmezse eksik soylenir`() {
        val lots = listOf(lot(1, "SUC-1", 4_000, "2026-11-02"), lot(2, "SUC-3", 10_000, "2026-11-20"))
        val (picks, short) = SaleRules.allocate(lots, 5, 13_000, today, inDraft = mapOf(1L to 3_000L))
        assertEquals(listOf("SUC-1" to 1_000L, "SUC-3" to 10_000L), picks.map { it.lot.lotNo to it.qtyMilli })
        assertEquals(2_000L, short)
    }
}
