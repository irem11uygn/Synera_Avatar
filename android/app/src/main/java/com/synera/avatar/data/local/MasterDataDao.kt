package com.synera.avatar.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
abstract class MasterDataDao {
    @Upsert
    protected abstract suspend fun upsertProducts(items: List<ProductEntity>)

    @Upsert
    protected abstract suspend fun upsertCustomers(items: List<CustomerEntity>)

    @Upsert
    protected abstract suspend fun upsertLots(items: List<LotEntity>)

    @Upsert
    protected abstract suspend fun upsertStock(items: List<StockEntity>)

    @Upsert
    protected abstract suspend fun upsertSyncMeta(meta: SyncMetaEntity)

    @Query("SELECT * FROM sync_meta WHERE id = 1")
    abstract suspend fun syncMeta(): SyncMetaEntity?

    @Query("SELECT * FROM sync_meta WHERE id = 1")
    abstract fun observeSyncMeta(): Flow<SyncMetaEntity?>

    /** Sunucudan gelen değişiklikleri tek SQLite işleminde uygular; yarım güncelleme kalmaz. */
    @Transaction
    open suspend fun applyPull(changes: PulledChanges, pulledAtMillis: Long) {
        upsertProducts(changes.products)
        upsertCustomers(changes.customers)
        upsertLots(changes.lots)
        upsertStock(changes.stock)
        upsertSyncMeta(
            SyncMetaEntity(
                lastChangeSeq = changes.nextSince,
                lastPullAtMillis = pulledAtMillis,
                datasetId = changes.datasetId,
            ),
        )
    }

    /** Yerel kopyayı sunucunun tam kopyasıyla değiştirir; silme ve yazma aynı işlemde, yarıda kalırsa eski kopya durur. */
    @Transaction
    open suspend fun replaceAll(changes: PulledChanges, pulledAtMillis: Long) {
        clearAll()
        applyPull(changes, pulledAtMillis)
    }

    @Query("SELECT COUNT(*) FROM product WHERE active = 1")
    abstract fun observeProductCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM customer")
    abstract fun observeCustomerCount(): Flow<Int>

    @Query(
        """
        SELECT l.lotNo AS lotNo, p.name AS productName, p.baseUnit AS baseUnit, s.qtyMilli AS qtyMilli,
               l.status AS status, l.expiryDate AS expiryDate
        FROM stock s
        JOIN lot l ON l.id = s.lotId
        JOIN product p ON p.id = l.productId
        WHERE s.qtyMilli > 0
        ORDER BY l.expiryDate, l.lotNo
        """,
    )
    abstract fun observeVanStock(): Flow<List<VanStockRow>>

    @Query("DELETE FROM product")
    protected abstract suspend fun clearProducts()

    @Query("DELETE FROM customer")
    protected abstract suspend fun clearCustomers()

    @Query("DELETE FROM lot")
    protected abstract suspend fun clearLots()

    @Query("DELETE FROM stock")
    protected abstract suspend fun clearStock()

    @Query("DELETE FROM sync_meta")
    protected abstract suspend fun clearSyncMeta()

    /** Başka bir kullanıcı giriş yaptığında önceki kullanıcının verisi silinir. */
    @Transaction
    open suspend fun clearAll() {
        clearProducts()
        clearCustomers()
        clearLots()
        clearStock()
        clearSyncMeta()
    }
}

data class PulledChanges(
    val datasetId: String,
    val nextSince: Long,
    val products: List<ProductEntity>,
    val customers: List<CustomerEntity>,
    val lots: List<LotEntity>,
    val stock: List<StockEntity>,
)
