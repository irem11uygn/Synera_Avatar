package com.synera.avatar.data.repo

import com.synera.avatar.data.local.CustomerEntity
import com.synera.avatar.data.local.MasterDataDao
import com.synera.avatar.data.local.SaleEntity
import com.synera.avatar.data.local.SaleLineEntity
import com.synera.avatar.data.local.SaleSummaryRow
import com.synera.avatar.data.local.SalesDao
import com.synera.avatar.data.local.SyncMetaEntity
import com.synera.avatar.data.local.SyncState
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.remote.ApiClient
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.remote.AvatarApi
import com.synera.avatar.data.remote.LoginRequest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.UUID

/** Satışa eklenecek satır (ekrandan). */
data class SaleLineDraft(
    val lotId: Long,
    val lotNo: String,
    val productId: Long,
    val qtyMilli: Long,
    val unitPriceCents: Long,
)

/** Bir eşitlemenin sonucu: gönderilen/reddedilen satışlar ve çekilen kayıt sayısı. */
data class SyncReport(val sent: Int, val failed: Int, val pulled: Int)

/** Ekranların tek veri kaynağı: oturum, satış, sunucuya gönderme ve sunucudan çekme. */
class AvatarRepository(
    private val sessions: SessionStore,
    private val dao: MasterDataDao,
    private val sales: SalesDao,
    private val apiFor: (String) -> AvatarApi = ApiClient::create,
    private val now: () -> Long = System::currentTimeMillis,
    /** Satış kaydedilince arka planda gönderimi başlatır (WorkManager); testte boş bırakılır. */
    private val onSaleSaved: () -> Unit = {},
) {
    // Ön plandaki "Verileri güncelle" ile arka plandaki iş aynı anda gönderim yapmasın.
    private val syncLock = Mutex()

    val serverUrl: String get() = sessions.serverUrl

    /** Eski sürümden kalan oturumda araç deposu kimliği yoktur; satış gönderebilmek için yeniden giriş istenir. */
    fun currentSession(): Session? {
        val session = sessions.current() ?: return null
        if (session.warehouseId != null) return session
        sessions.clearToken()
        return null
    }

    suspend fun login(serverUrl: String, username: String, password: String): Session {
        val response = ApiClient.call { apiFor(serverUrl).login(LoginRequest(username.trim(), password)) }
        val user = response.user
        if (user.role != "SATIS" || user.warehouseCode == null || user.warehouseId == null) {
            throw ApiException("Bu uygulama yalnız araç deposu atanmış satış kullanıcıları içindir.")
        }
        val previous = sessions.lastUsername()
        if (previous != null && previous != user.username) {
            // Gönderilmemiş satış başka kullanıcının adıyla gönderilmesin.
            if (sales.pendingCount() > 0) {
                throw ApiException("$previous kullanıcısının gönderilmemiş satışları var; önce o kullanıcıyla eşitleyin.")
            }
            sales.clearAll()
            dao.clearAll()
        } else if (previous == null) {
            dao.clearAll()
        }
        sessions.serverUrl = serverUrl
        val session = Session(response.token, user.username, user.fullName, user.warehouseCode, user.warehouseId)
        sessions.save(session)
        return session
    }

    /**
     * Satışı cihazda tek işlemde kaydeder (FR-404): bağlantı gerekmez. Bloke lot ve kullanılabilir
     * miktarı aşan satır kaydedilmez (SaleNotAllowed). Gönderim arka planda başlatılır.
     */
    suspend fun createSale(customerId: Long, lines: List<SaleLineDraft>): String {
        require(lines.isNotEmpty()) { "Satışta en az bir satır olmalı." }
        val uuid = UUID.randomUUID().toString()
        sales.saveSale(
            SaleEntity(clientUuid = uuid, customerId = customerId, soldAtMillis = now(), syncState = SyncState.PENDING),
            lines.mapIndexed { index, line ->
                SaleLineEntity(
                    saleUuid = uuid,
                    lineNo = index + 1,
                    productId = line.productId,
                    lotId = line.lotId,
                    lotNo = line.lotNo,
                    qtyMilli = line.qtyMilli,
                    unitPriceCents = line.unitPriceCents,
                    amountCents = SaleRules.amountCents(line.qtyMilli, line.unitPriceCents),
                )
            },
        )
        onSaleSaved()
        return uuid
    }

    /** Önce bekleyen satışları gönderir, sonra sunucudaki değişiklikleri çeker (ADR-004). */
    suspend fun sync(): SyncReport =
        syncLock.withLock {
            val session = sessions.current() ?: throw ApiException("Oturum yok; yeniden giriş yapın.", UNAUTHORIZED)
            val (sent, failed) = pushPending(session)
            SyncReport(sent, failed, pullChanges(session))
        }

    private suspend fun pushPending(session: Session): Pair<Int, Int> {
        val pending = sales.pendingSales()
        if (pending.isEmpty()) return 0 to 0
        val warehouseId = session.warehouseId ?: run {
            sessions.clearToken()
            throw ApiException("Oturum bilgisi eski sürümden; satışları göndermek için yeniden giriş yapın.", UNAUTHORIZED)
        }
        var sent = 0
        var failed = 0
        for (batch in pending.chunked(PUSH_BATCH)) {
            val request = toPushRequest(sessions.deviceId, warehouseId, batch, sales.linesOf(batch.map { it.clientUuid }))
            val response = authorized { apiFor(sessions.serverUrl).push(bearer(session), request) }
            for (outcome in response.results.map { it.toOutcome() }) {
                sales.markResult(outcome.clientUuid, outcome.state, outcome.saleNo, outcome.message)
                if (outcome.state == SyncState.SENT) sent++ else failed++
            }
        }
        return sent to failed
    }

    /**
     * Son alınan değişiklik numarasından sonraki kayıtları çeker ve tek işlemde uygular (ADR-004).
     * Sunucu sıfırlanmışsa tam kopyayı çeker ve yerel kopyanın yerine koyar.
     */
    private suspend fun pullChanges(session: Session): Int {
        val meta = dao.syncMeta()
        var changes = fetchChanges(session, meta?.lastChangeSeq ?: 0)
        if (meta.isStaleFor(changes)) {
            changes = fetchChanges(session, 0)
            dao.replaceAll(changes, now())
            sales.clearFinished() // eski sunucuya gönderilmiş satışlar "son satışlar"da kalmasın
        } else {
            dao.applyPull(changes, now())
        }
        return changes.products.size + changes.customers.size + changes.lots.size + changes.stock.size
    }

    private suspend fun fetchChanges(session: Session, since: Long) =
        authorized { apiFor(sessions.serverUrl).pull(bearer(session), since) }.toChanges()

    /** 401 gelirse belirteç silinir; ekran giriş sayfasına döner. */
    private suspend fun <T> authorized(block: suspend () -> T): T =
        try {
            ApiClient.call(block)
        } catch (e: ApiException) {
            if (e.code == UNAUTHORIZED) sessions.clearToken()
            throw e
        }

    private fun bearer(session: Session) = "Bearer ${session.token}"

    fun logout() = sessions.clearToken()

    fun observeSyncMeta(): Flow<SyncMetaEntity?> = dao.observeSyncMeta()

    fun observeProductCount(): Flow<Int> = dao.observeProductCount()

    fun observeCustomerCount(): Flow<Int> = dao.observeCustomerCount()

    fun observeCustomers(): Flow<List<CustomerEntity>> = dao.observeCustomers()

    fun observeVanStock(): Flow<List<VanStockRow>> = dao.observeVanStock()

    fun observePendingCount(): Flow<Int> = sales.observePendingCount()

    fun observeRecentSales(): Flow<List<SaleSummaryRow>> = sales.observeRecentSales()

    private companion object {
        const val UNAUTHORIZED = "UNAUTHORIZED"
        const val PUSH_BATCH = 50
    }
}
