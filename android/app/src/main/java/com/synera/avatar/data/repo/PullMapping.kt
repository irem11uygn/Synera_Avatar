package com.synera.avatar.data.repo

import com.synera.avatar.data.local.CustomerEntity
import com.synera.avatar.data.local.LotEntity
import com.synera.avatar.data.local.ProductEntity
import com.synera.avatar.data.local.PulledChanges
import com.synera.avatar.data.local.StockEntity
import com.synera.avatar.data.remote.PullResponse
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity

/** Sunucu yanıtını cihaz tablolarına çevirir: metin ondalıklar → tamsayı kuruş / binde bir birim. */
fun PullResponse.toChanges(): PulledChanges =
    PulledChanges(
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
