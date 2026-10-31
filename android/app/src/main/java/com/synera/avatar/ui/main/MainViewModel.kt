package com.synera.avatar.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.local.SaleSummaryRow
import com.synera.avatar.data.local.SyncMetaEntity
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.Session
import com.synera.avatar.data.repo.SyncReport
import com.synera.avatar.util.t
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.ZoneId

data class MainUiState(
    val syncing: Boolean = false,
    /** Son eşitlemenin sonucu; metni ekranda seçili dille yazılır. */
    val report: SyncReport? = null,
    val error: String? = null,
    val offline: Boolean = false,
    val signedOut: Boolean = false,
    /** Yönetici şifreyi sıfırladı: sunucu yeni şifre belirlenmeden eşitlemeye izin vermiyor. */
    val passwordRequired: Boolean = false,
)

/** Ana ekranın verisi: araç stoku, bugünkü satışlar, bekleyen gönderimler ve eşitleme durumu. */
class MainViewModel(private val repository: AvatarRepository, zone: ZoneId = ZoneId.systemDefault()) : ViewModel() {
    val session: Session? = repository.currentSession()
    val serverUrl: String get() = repository.serverUrl
    val deviceId: String get() = repository.deviceId

    private val startOfToday = LocalDate.now(zone).atStartOfDay(zone).toInstant().toEpochMilli()

    val vanStock: StateFlow<List<VanStockRow>> = repository.observeVanStock().asState(emptyList())
    val syncMeta: StateFlow<SyncMetaEntity?> = repository.observeSyncMeta().asState(null)
    val pendingCount: StateFlow<Int> = repository.observePendingCount().asState(0)
    val recentSales: StateFlow<List<SaleSummaryRow>> = repository.observeRecentSales().asState(emptyList())
    val todaySales: StateFlow<List<SaleSummaryRow>> = repository.observeSalesSince(startOfToday).asState(emptyList())

    private val _ui = MutableStateFlow(MainUiState())
    val ui: StateFlow<MainUiState> = _ui.asStateFlow()

    init {
        refresh()
    }

    /** Önce bekleyen satışları gönderir, sonra sunucudan çeker. */
    fun refresh() {
        if (_ui.value.syncing) return
        _ui.update { it.copy(syncing = true, report = null, error = null) }
        viewModelScope.launch {
            try {
                val report = repository.sync()
                _ui.update { it.copy(syncing = false, offline = false, report = report) }
            } catch (e: ApiException) {
                _ui.update {
                    it.copy(
                        syncing = false,
                        offline = e.code == "NETWORK",
                        error = if (e.code == "NETWORK") null else e.message,
                        signedOut = e.code == "UNAUTHORIZED",
                        passwordRequired = e.code == "PASSWORD_CHANGE_REQUIRED",
                    )
                }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            _ui.update { it.copy(signedOut = true) }
        }
    }

    private fun <T> Flow<T>.asState(initial: T): StateFlow<T> =
        stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)
}

/** Eşitleme sonucu, seçili dilde (ör. "2 satış gönderildi · yeni değişiklik yok."). */
fun describe(report: SyncReport): String {
    val parts = buildList {
        if (report.sent > 0) add(t("{n} satış gönderildi", "n" to report.sent))
        if (report.failed > 0) add(t("{n} satış reddedildi", "n" to report.failed))
        add(if (report.pulled == 0) t("yeni değişiklik yok") else t("{n} kayıt güncellendi", "n" to report.pulled))
    }
    return parts.joinToString(" · ").replaceFirstChar { it.uppercaseChar() } + "."
}
