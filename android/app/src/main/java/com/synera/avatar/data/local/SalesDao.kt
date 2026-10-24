package com.synera.avatar.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/** Satışın kullanılabilir stoku aştığı ya da lotun bloke olduğu durumda kayıt yapılmaz. */
class SaleNotAllowed(message: String) : Exception(message)

@Dao
abstract class SalesDao {
    @Insert
    protected abstract suspend fun insertSale(sale: SaleEntity)

    @Insert
    protected abstract suspend fun insertLines(lines: List<SaleLineEntity>)

    @Query(
        """
        SELECT s.qtyMilli - COALESCE((
            SELECT SUM(sl.qtyMilli) FROM sale_line sl JOIN sale sa ON sa.clientUuid = sl.saleUuid
            WHERE sa.syncState = 'BEKLIYOR' AND sl.lotId = :lotId
        ), 0)
        FROM stock s WHERE s.lotId = :lotId
        """,
    )
    protected abstract suspend fun availableMilli(lotId: Long): Long?

    @Query("SELECT status FROM lot WHERE id = :lotId")
    protected abstract suspend fun lotStatus(lotId: Long): String?

    /**
     * Satışı ve satırlarını tek SQLite işleminde yazar. Bloke lot ve kullanılabilir miktarı aşan satır
     * işlem içinde yeniden denetlenir; ekrandaki bilgi eskimiş olsa da yanlış kayıt oluşmaz (FR-403).
     */
    @Transaction
    open suspend fun saveSale(sale: SaleEntity, lines: List<SaleLineEntity>) {
        for ((lotId, lotLines) in lines.groupBy { it.lotId }) {
            val lotNo = lotLines.first().lotNo
            if (lotStatus(lotId) == "BLOKE") throw SaleNotAllowed("$lotNo lotu bloke (geri çağrıldı); satılamaz.")
            if (lotLines.sumOf { it.qtyMilli } > (availableMilli(lotId) ?: 0)) {
                throw SaleNotAllowed("$lotNo lotunda araçta bu kadar kullanılabilir miktar yok.")
            }
        }
        insertSale(sale)
        insertLines(lines)
    }

    @Query("DELETE FROM sale_line")
    protected abstract suspend fun clearLines()

    @Query("DELETE FROM sale")
    protected abstract suspend fun clearSales()

    /** Başka kullanıcı giriş yaptığında satış geçmişi silinir (gönderilmemiş satış varken çağrılmaz). */
    @Transaction
    open suspend fun clearAll() {
        clearLines()
        clearSales()
    }

    @Query("SELECT * FROM sale WHERE syncState = 'BEKLIYOR' ORDER BY soldAtMillis")
    abstract suspend fun pendingSales(): List<SaleEntity>

    @Query("SELECT * FROM sale_line WHERE saleUuid IN (:uuids) ORDER BY saleUuid, lineNo")
    abstract suspend fun linesOf(uuids: List<String>): List<SaleLineEntity>

    @Query(
        "UPDATE sale SET syncState = :state, serverSaleNo = :saleNo, serverMessage = :message WHERE clientUuid = :uuid",
    )
    abstract suspend fun markResult(uuid: String, state: String, saleNo: String?, message: String?)

    @Query("SELECT COUNT(*) FROM sale WHERE syncState = 'BEKLIYOR'")
    abstract suspend fun pendingCount(): Int

    @Query("SELECT COUNT(*) FROM sale WHERE syncState = 'BEKLIYOR'")
    abstract fun observePendingCount(): Flow<Int>

    @Query(
        """
        SELECT sa.clientUuid AS clientUuid, sa.soldAtMillis AS soldAtMillis, sa.syncState AS syncState,
               sa.serverSaleNo AS serverSaleNo, sa.serverMessage AS serverMessage, c.name AS customerName,
               COALESCE(SUM(sl.amountCents), 0) AS totalCents, COUNT(sl.lineNo) AS lineCount
        FROM sale sa
        LEFT JOIN customer c ON c.id = sa.customerId
        LEFT JOIN sale_line sl ON sl.saleUuid = sa.clientUuid
        GROUP BY sa.clientUuid
        ORDER BY sa.soldAtMillis DESC
        LIMIT 30
        """,
    )
    abstract fun observeRecentSales(): Flow<List<SaleSummaryRow>>
}
