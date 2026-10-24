package com.synera.avatar

import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class UnitsTest {
    @Test
    fun `tutarlar kayipsiz kurusa cevrilir`() {
        assertEquals(2490L, Money.toCents("24.90"))
        assertEquals(154350L, Money.toCents("1543.50"))
        assertEquals(1816L, Money.toCents("18.16"))
        assertEquals(0L, Money.toCents("0.00"))
    }

    @Test
    fun `kurustan hassas tutar sessizce yuvarlanmaz`() {
        assertThrows(ArithmeticException::class.java) { Money.toCents("1.005") }
    }

    @Test
    fun `tutar Turkce bicimde gosterilir`() {
        assertEquals("1.543,50 €", Money.format(154350))
        assertEquals("24,90 €", Money.format(2490))
    }

    @Test
    fun `miktarlar binde bir birime cevrilir ve geri doner`() {
        assertEquals(100_000L, Quantity.toMilli("100.000"))
        assertEquals(1_000L, Quantity.toMilli("1.000"))
        assertEquals("2.500", Quantity.toApiText(2_500))
    }

    @Test
    fun `miktar birimiyle gosterilir`() {
        assertEquals("2,5 kg", Quantity.format(2_500, "KG"))
        assertEquals("85 adet", Quantity.format(85_000, "ADET"))
        assertEquals("1.000 kg", Quantity.format(1_000_000, "KG"))
    }
}
