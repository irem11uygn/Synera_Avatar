package com.synera.avatar.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

// Cihazdaki SQLite tabloları (docs/data_model.md §6). Para: kuruş, miktar: binde bir birim.
// Satış tabloları (sale, sale_line) satış akışıyla birlikte eklenecek (T-14).

@Entity(tableName = "product")
data class ProductEntity(
    @PrimaryKey val id: Long,
    val code: String,
    val name: String,
    val baseUnit: String,
    val unitWeightMilli: Long?,
    val salePriceCents: Long?,
    val active: Boolean,
)

@Entity(tableName = "customer")
data class CustomerEntity(
    @PrimaryKey val id: Long,
    val code: String,
    val name: String,
    val contactPerson: String?,
    val phone: String?,
)

@Entity(tableName = "lot")
data class LotEntity(
    @PrimaryKey val id: Long,
    val lotNo: String,
    val productId: Long,
    val expiryDate: String?,
    val status: String,
)

/** Sunucudaki araç deposu bakiyesi. */
@Entity(tableName = "stock")
data class StockEntity(
    @PrimaryKey val lotId: Long,
    val qtyMilli: Long,
)

@Entity(tableName = "sync_meta")
data class SyncMetaEntity(
    @PrimaryKey val id: Int = 1,
    val lastChangeSeq: Long,
    val lastPullAtMillis: Long?,
)

/** Araç deposu ekranı için birleşik satır. */
data class VanStockRow(
    val lotNo: String,
    val productName: String,
    val baseUnit: String,
    val qtyMilli: Long,
    val status: String,
    val expiryDate: String?,
)
