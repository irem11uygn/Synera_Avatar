package com.synera.avatar.data.repo

import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.t
import java.math.RoundingMode
import java.time.LocalDate

/** Bir satır için seçilen lot ve miktarı. */
data class LotPick(val lot: VanStockRow, val qtyMilli: Long)

/** Satış satırı kuralları. Cihazda hızlı geri bildirim içindir; sunucu aynılarını yeniden denetler. */
object SaleRules {
    /** Satır tutarı (kuruş): miktar × birim fiyat, kuruşa yarım yukarı — sunucudaki hesapla aynı. */
    fun amountCents(qtyMilli: Long, unitPriceCents: Long): Long =
        Quantity.fromMilli(qtyMilli)
            .multiply(Money.fromCents(unitPriceCents))
            .setScale(2, RoundingMode.HALF_UP)
            .movePointRight(2)
            .longValueExact()

    fun isExpired(lot: VanStockRow, today: LocalDate): Boolean =
        lot.expiryDate?.let { LocalDate.parse(it).isBefore(today) } ?: false

    /** Satılabilir: satışa açık, süresi geçmemiş, araçta kullanılabilir miktarı olan lot. */
    fun isSellable(lot: VanStockRow, today: LocalDate): Boolean =
        lot.status != "BLOKE" && !isExpired(lot, today) && lot.availableMilli > 0

    /**
     * İlk dolan ilk çıkar (FEFO): miktarı, son kullanma tarihi en yakın lottan başlayarak böler.
     * inDraft: bu satışın taslağında lot başına zaten ayrılmış miktar. Dönen ikinci değer: eksik kalan (0 = yetti).
     */
    fun allocate(
        lots: List<VanStockRow>,
        productId: Long,
        qtyMilli: Long,
        today: LocalDate,
        inDraft: Map<Long, Long> = emptyMap(),
    ): Pair<List<LotPick>, Long> {
        val picks = mutableListOf<LotPick>()
        var remaining = qtyMilli
        val candidates = lots
            .filter { it.productId == productId && isSellable(it, today) }
            .sortedWith(compareBy<VanStockRow>({ it.expiryDate == null }, { it.expiryDate }, { it.lotNo }))
        for (lot in candidates) {
            if (remaining <= 0) break
            val free = lot.availableMilli - (inDraft[lot.lotId] ?: 0)
            if (free <= 0) continue
            val take = minOf(free, remaining)
            picks += LotPick(lot, take)
            remaining -= take
        }
        return picks to remaining.coerceAtLeast(0)
    }

    /**
     * Satıra eklemeden önce denetim; hata mesajı ya da null.
     * alreadyInDraftMilli: aynı lottan bu satışın taslağına zaten eklenmiş miktar.
     */
    fun lineError(
        baseUnit: String,
        lotStatus: String,
        qtyMilli: Long?,
        availableMilli: Long,
        alreadyInDraftMilli: Long = 0,
        expired: Boolean = false,
    ): String? {
        val remaining = availableMilli - alreadyInDraftMilli
        return when {
            lotStatus == "BLOKE" -> t("Bu lot geri çağrıldı; satılamaz.")
            expired -> t("Bu lotun son kullanma tarihi geçmiş; satılamaz.")
            qtyMilli == null -> t("Geçerli bir miktar yazın (en çok 3 ondalık, binlik ayırıcı olmadan).")
            qtyMilli <= 0 -> t("Miktar sıfırdan büyük olmalı.")
            baseUnit == "ADET" && qtyMilli % 1000 != 0L -> t("Bu ürün adet ile satılır; tam sayı girin.")
            qtyMilli > remaining -> t("Araçta kullanılabilir miktar: {qty}.", "qty" to Quantity.format(remaining.coerceAtLeast(0), baseUnit))
            else -> null
        }
    }
}
