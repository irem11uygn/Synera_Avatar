package com.synera.avatar.util

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

/**
 * Para ve miktar dönüşümleri (ADR-006).
 *
 * SQLite'ta ondalık tip yok; REAL ikili kayan noktalıdır. Bu yüzden cihazda tutarlar tamsayı
 * kuruş, miktarlar tamsayı "binde bir birim" (kg için gram, adet için adet × 1000) saklanır.
 * API ondalıkları metin olarak gönderir ("24.90"); dönüşüm BigDecimal ile kayıpsız yapılır.
 */
object Money {
    /** "24.90" → 2490. Kuruştan hassas değer gelirse hata verir (sessizce yuvarlamaz). */
    fun toCents(text: String): Long =
        BigDecimal(text).movePointRight(2).setScale(0, RoundingMode.UNNECESSARY).longValueExact()

    fun fromCents(cents: Long): BigDecimal = BigDecimal.valueOf(cents, 2)

    /** 154350 → "1.543,50 €" */
    fun format(cents: Long): String = moneyFormat().format(fromCents(cents)) + " €"
}

object Quantity {
    /** "100.000" → 100000 (gram ya da adet × 1000). */
    fun toMilli(text: String): Long =
        BigDecimal(text).movePointRight(3).setScale(0, RoundingMode.UNNECESSARY).longValueExact()

    fun fromMilli(milli: Long): BigDecimal = BigDecimal.valueOf(milli, 3)

    /** API'ye gönderilecek metin: 2500 → "2.500". */
    fun toApiText(milli: Long): String = fromMilli(milli).toPlainString()

    /** Ekranda: 2500 + KG → "2,5 kg"; 85000 + ADET → "85 adet". */
    fun format(milli: Long, baseUnit: String): String {
        val unit = if (baseUnit == "ADET") "adet" else "kg"
        return qtyFormat().format(fromMilli(milli)) + " " + unit
    }
}

private val turkish: Locale = Locale.forLanguageTag("tr-TR")

private fun moneyFormat() = DecimalFormat("#,##0.00", DecimalFormatSymbols(turkish))

private fun qtyFormat() = DecimalFormat("#,##0.###", DecimalFormatSymbols(turkish))
