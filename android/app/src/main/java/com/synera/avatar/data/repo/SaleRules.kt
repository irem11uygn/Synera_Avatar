package com.synera.avatar.data.repo

import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import java.math.RoundingMode

/** Satış satırı kuralları. Cihazda hızlı geri bildirim içindir; sunucu aynılarını yeniden denetler. */
object SaleRules {
    /** Satır tutarı (kuruş): miktar × birim fiyat, kuruşa yarım yukarı — sunucudaki hesapla aynı. */
    fun amountCents(qtyMilli: Long, unitPriceCents: Long): Long =
        Quantity.fromMilli(qtyMilli)
            .multiply(Money.fromCents(unitPriceCents))
            .setScale(2, RoundingMode.HALF_UP)
            .movePointRight(2)
            .longValueExact()

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
    ): String? {
        val remaining = availableMilli - alreadyInDraftMilli
        return when {
            lotStatus == "BLOKE" -> "Bu lot bloke (geri çağrıldı); satılamaz."
            qtyMilli == null -> "Geçerli bir miktar yazın (en çok 3 ondalık, binlik ayırıcı olmadan)."
            qtyMilli <= 0 -> "Miktar sıfırdan büyük olmalı."
            baseUnit == "ADET" && qtyMilli % 1000 != 0L -> "Bu ürün adet ile satılır; tam sayı girin."
            qtyMilli > remaining -> "Araçta kullanılabilir miktar: ${Quantity.format(remaining.coerceAtLeast(0), baseUnit)}."
            else -> null
        }
    }
}
