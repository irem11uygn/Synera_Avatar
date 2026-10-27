package com.synera.avatar.data.repo

import com.synera.avatar.data.local.SaleEntity
import com.synera.avatar.data.local.SaleLineEntity
import com.synera.avatar.data.local.SyncState
import com.synera.avatar.data.remote.PushLineDto
import com.synera.avatar.data.remote.PushRequest
import com.synera.avatar.data.remote.PushResultDto
import com.synera.avatar.data.remote.PushSaleDto
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.t
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId

/** Bekleyen satışları sunucunun beklediği biçime çevirir (docs/api.md §4.4); tutarlar metin ondalık. */
fun toPushRequest(
    deviceId: String,
    warehouseId: Long,
    sales: List<SaleEntity>,
    lines: List<SaleLineEntity>,
    zone: ZoneId = ZoneId.systemDefault(),
): PushRequest {
    val bySale = lines.groupBy { it.saleUuid }
    return PushRequest(
        deviceId = deviceId,
        sales = sales.map { sale ->
            PushSaleDto(
                clientUuid = sale.clientUuid,
                customerId = sale.customerId,
                warehouseId = warehouseId,
                soldAt = OffsetDateTime.ofInstant(Instant.ofEpochMilli(sale.soldAtMillis), zone).toString(),
                lines = bySale[sale.clientUuid].orEmpty().sortedBy { it.lineNo }.map {
                    PushLineDto(it.lotNo, Quantity.toApiText(it.qtyMilli), Money.toApiText(it.unitPriceCents))
                },
                paymentMethod = sale.paymentMethod,
            )
        },
    )
}

/** Sunucunun bir satış için verdiği sonuç, cihazdaki durum olarak. */
data class SaleOutcome(val clientUuid: String, val state: String, val saleNo: String?, val message: String?)

fun PushResultDto.toOutcome(): SaleOutcome =
    when (status) {
        // DUPLICATE: daha önce kaydedilmiş (ör. cevap yolda kayboldu); ilk sonuç geçerli.
        "ACCEPTED", "DUPLICATE" -> SaleOutcome(clientUuid, SyncState.SENT, saleNo, warnings.joinToString(" ").ifEmpty { null })
        "ACCEPTED_WITH_WARNING" -> SaleOutcome(clientUuid, SyncState.SENT, saleNo, warnings.joinToString(" "))
        else -> SaleOutcome(clientUuid, SyncState.FAILED, null, error?.message ?: t("Sunucu satışı reddetti."))
    }
