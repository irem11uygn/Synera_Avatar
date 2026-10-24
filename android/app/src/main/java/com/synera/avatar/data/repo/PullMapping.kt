package com.synera.avatar.data.repo

import com.synera.avatar.data.local.CustomerEntity
import com.synera.avatar.data.local.LotEntity
import com.synera.avatar.data.local.ProductEntity
import com.synera.avatar.data.local.PulledChanges
import com.synera.avatar.data.local.StockEntity
import com.synera.avatar.data.local.SyncMetaEntity
import com.synera.avatar.data.remote.PullResponse
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity

/** Sunucu yanıtını cihaz tablolarına çevirir: metin ondalıklar → tamsayı kuruş / binde bir birim. */
fun PullResponse.toChanges(): PulledChanges =
    PulledChanges(
        datasetId = datasetId,
        nextSince = nextSince,
        products = products.map {
            ProductEntity(
                id = it.id,
                code = it.code,
                name = it.name,
                baseUnit = it.baseUnit,
                unitWeightMilli = it.unitWeightKg?.let(Quantity::toMilli),
                salePriceCents = it.salePrice?.let(Money::toCents),
                active = it.active,
            )
        },
        customers = customers.map {
            CustomerEntity(id = it.id, code = it.code, name = it.name, contactPerson = it.contactPerson, phone = it.phone)
        },
        lots = lots.map {
            LotEntity(id = it.id, lotNo = it.lotNo, productId = it.productId, expiryDate = it.expiryDate, status = it.status)
        },
        stock = stock.map { StockEntity(lotId = it.lotId, qtyMilli = Quantity.toMilli(it.qty)) },
    )

/**
 * Sunucu sıfırdan kurulduysa (veri kümesi kimliği değişti) ya da eski bir yedekten döndüyse (sayaç geriledi)
 * artımlı çekme sunucuda artık olmayan kayıtları cihazda bırakır; yerel kopya baştan kurulmalıdır.
 */
fun SyncMetaEntity?.isStaleFor(changes: PulledChanges): Boolean =
    this != null && (datasetId != changes.datasetId || changes.nextSince < lastChangeSeq)
