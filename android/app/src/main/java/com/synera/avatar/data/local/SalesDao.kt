package com.synera.avatar.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import com.synera.avatar.util.t
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
            if (lotStatus(lotId) == "BLOKE") throw SaleNotAllowed(t("{lot} lotu geri çağrıldı; satılamaz.", "lot" to lotNo))
            if (lotLines.sumOf { it.qtyMilli } > (availableMilli(lotId) ?: 0)) {
                throw SaleNotAllowed(t("{lot} lotunda araçta bu kadar kullanılabilir miktar yok.", "lot" to lotNo))
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

    @Query("DELETE FROM sale_line WHERE saleUuid IN (SELECT clientUuid FROM sale WHERE syncState <> 'BEKLIYOR')")
    protected abstract suspend fun clearFinishedLines()

    @Query("DELETE FROM sale WHERE syncState <> 'BEKLIYOR'")
    protected abstract suspend fun clearFinishedSales()

    /** Sunucu sıfırlanınca (veri kümesi değişti) eski sunucuya ait satış geçmişi silinir; bekleyenler kalır. */
    @Transaction
    open suspend fun clearFinished() {
        clearFinishedLines()
        clearFinishedSales()
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
               sa.paymentMethod AS paymentMethod,
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

    /** Belli bir andan sonraki satışlar (bugünün özeti: çevrimdışıyken de çalışır). */
    @Query(
        """
        SELECT sa.clientUuid AS clientUuid, sa.soldAtMillis AS soldAtMillis, sa.syncState AS syncState,
               sa.serverSaleNo AS serverSaleNo, sa.serverMessage AS serverMessage, c.name AS customerName,
               sa.paymentMethod AS paymentMethod,
               COALESCE(SUM(sl.amountCents), 0) AS totalCents, COUNT(sl.lineNo) AS lineCount
        FROM sale sa
        LEFT JOIN customer c ON c.id = sa.customerId
        LEFT JOIN sale_line sl ON sl.saleUuid = sa.clientUuid
        WHERE sa.soldAtMillis >= :fromMillis AND sa.syncState <> 'HATA'
        GROUP BY sa.clientUuid
        ORDER BY sa.soldAtMillis DESC
        """,
    )
    abstract fun observeSalesSince(fromMillis: Long): Flow<List<SaleSummaryRow>>

    /** Sunucu sıfırlandıysa bekleyen satışlar gönderilmez: lot numaraları başka bir veri kümesine aittir. */
    @Query(
        "UPDATE sale SET syncState = 'HATA', serverMessage = :message WHERE syncState = 'BEKLIYOR'",
    )
    abstract suspend fun failPending(message: String)
}
