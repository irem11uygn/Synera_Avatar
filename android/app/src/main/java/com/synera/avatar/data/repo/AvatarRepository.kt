package com.synera.avatar.data.repo

import com.synera.avatar.data.local.MasterDataDao
import com.synera.avatar.data.local.SyncMetaEntity
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.remote.ApiClient
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.remote.AvatarApi
import com.synera.avatar.data.remote.LoginRequest
import kotlinx.coroutines.flow.Flow

/** Ekranların tek veri kaynağı: oturum, sunucudan çekme ve yerel veritabanı. */
class AvatarRepository(
    private val sessions: SessionStore,
    private val dao: MasterDataDao,
    private val apiFor: (String) -> AvatarApi = ApiClient::create,
    private val now: () -> Long = System::currentTimeMillis,
) {
    val serverUrl: String get() = sessions.serverUrl

    fun currentSession(): Session? = sessions.current()

    suspend fun login(serverUrl: String, username: String, password: String): Session {
        val response = ApiClient.call { apiFor(serverUrl).login(LoginRequest(username.trim(), password)) }
        if (response.user.role != "SATIS" || response.user.warehouseCode == null) {
            throw ApiException("Bu uygulama yalnız araç deposu atanmış satış kullanıcıları içindir.")
        }
        if (sessions.lastUsername() != response.user.username) dao.clearAll()
        sessions.serverUrl = serverUrl
        val session = Session(response.token, response.user.username, response.user.fullName, response.user.warehouseCode)
        sessions.save(session)
        return session
    }

    /**
     * Son alınan değişiklik numarasından sonraki kayıtları çeker ve tek işlemde uygular (ADR-004).
     * Sunucu sıfırlanmışsa tam kopyayı çeker ve yerel kopyanın yerine koyar.
     */
    suspend fun pull(): Int {
        val session = sessions.current() ?: throw ApiException("Oturum yok; yeniden giriş yapın.")
        val meta = dao.syncMeta()
        var changes = fetchChanges(session, meta?.lastChangeSeq ?: 0)
        if (meta.isStaleFor(changes)) {
            changes = fetchChanges(session, 0)
            dao.replaceAll(changes, now())
        } else {
            dao.applyPull(changes, now())
        }
        return changes.products.size + changes.customers.size + changes.lots.size + changes.stock.size
    }

    private suspend fun fetchChanges(session: Session, since: Long) =
        try {
            ApiClient.call { apiFor(sessions.serverUrl).pull("Bearer ${session.token}", since) }.toChanges()
        } catch (e: ApiException) {
            if (e.code == "UNAUTHORIZED") sessions.clearToken()
            throw e
        }

    fun logout() = sessions.clearToken()

    fun observeSyncMeta(): Flow<SyncMetaEntity?> = dao.observeSyncMeta()

    fun observeProductCount(): Flow<Int> = dao.observeProductCount()

    fun observeCustomerCount(): Flow<Int> = dao.observeCustomerCount()

    fun observeVanStock(): Flow<List<VanStockRow>> = dao.observeVanStock()
}
