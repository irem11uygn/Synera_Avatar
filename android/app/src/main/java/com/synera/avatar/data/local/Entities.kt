package com.synera.avatar.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Cihazdaki SQLite tabloları (docs/data_model.md §6). Para: kuruş, miktar: binde bir birim.

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
    /** Sunucu veri kümesi kimliği; sürüm 1'den gelen cihazlarda boştur (ilk çekişte baştan kurulur). */
    val datasetId: String?,
)

/** Cihazda yapılan satış. Gönderilene kadar BEKLIYOR; sunucunun cevabına göre GONDERILDI ya da HATA. */
@Entity(tableName = "sale")
data class SaleEntity(
    @PrimaryKey val clientUuid: String,
    val customerId: Long,
    val soldAtMillis: Long,
    val syncState: String,
    val serverSaleNo: String? = null,
    /** Sunucunun uyarısı (ör. geri çağrılmış lot) ya da ret nedeni. */
    val serverMessage: String? = null,
    /** NAKIT, KART, HAVALE, VERESIYE; sürüm 3'ten gelen satışlarda boş. */
    val paymentMethod: String? = null,
)

/** Satış satırı: bir satır = bir lot (FR-401). Lot numarası gönderim için satırda da saklanır. */
@Entity(tableName = "sale_line", primaryKeys = ["saleUuid", "lineNo"], indices = [Index("lotId")])
data class SaleLineEntity(
    val saleUuid: String,
    val lineNo: Int,
    val productId: Long,
    val lotId: Long,
    val lotNo: String,
    val qtyMilli: Long,
    val unitPriceCents: Long,
    val amountCents: Long,
)

object SyncState {
    const val PENDING = "BEKLIYOR"
    const val SENT = "GONDERILDI"
    const val FAILED = "HATA"
}

/** Araç deposundaki lot: sunucu bakiyesi ve gönderilmemiş satışlar düşüldükten sonra kullanılabilir miktar. */
data class VanStockRow(
    val lotId: Long,
    val lotNo: String,
    val productId: Long,
    val productName: String,
    val baseUnit: String,
    val salePriceCents: Long?,
    val qtyMilli: Long,
    val availableMilli: Long,
    val status: String,
    val expiryDate: String?,
)

/** Satış listesi satırı. */
data class SaleSummaryRow(
    val clientUuid: String,
    val soldAtMillis: Long,
    val syncState: String,
    val serverSaleNo: String?,
    val serverMessage: String?,
    val customerName: String?,
    val paymentMethod: String?,
    val totalCents: Long,
    val lineCount: Int,
)

/** Ödeme türü sabitleri (sunucudaki PaymentMethod ile aynı). */
object Payment {
    const val CASH = "NAKIT"
    const val CARD = "KART"
    const val TRANSFER = "HAVALE"
    const val CREDIT = "VERESIYE"
    val ALL = listOf(CASH, CARD, TRANSFER, CREDIT)
}
