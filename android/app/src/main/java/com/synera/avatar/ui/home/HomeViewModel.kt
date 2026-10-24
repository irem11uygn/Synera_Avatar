package com.synera.avatar.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.local.SaleSummaryRow
import com.synera.avatar.data.local.SyncMetaEntity
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.Session
import com.synera.avatar.data.repo.SyncReport
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val syncing: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val signedOut: Boolean = false,
)

class HomeViewModel(private val repository: AvatarRepository) : ViewModel() {
    val session: Session? = repository.currentSession()

    val productCount: StateFlow<Int> = repository.observeProductCount().asState(0)
    val customerCount: StateFlow<Int> = repository.observeCustomerCount().asState(0)
    val vanStock: StateFlow<List<VanStockRow>> = repository.observeVanStock().asState(emptyList())
    val syncMeta: StateFlow<SyncMetaEntity?> = repository.observeSyncMeta().asState(null)
    val pendingCount: StateFlow<Int> = repository.observePendingCount().asState(0)
    val recentSales: StateFlow<List<SaleSummaryRow>> = repository.observeRecentSales().asState(emptyList())

    private val _ui = MutableStateFlow(HomeUiState())
    val ui: StateFlow<HomeUiState> = _ui.asStateFlow()

    init {
        refresh()
    }

    /** Önce bekleyen satışları gönderir, sonra sunucudan çeker. */
    fun refresh() {
        if (_ui.value.syncing) return
        _ui.update { it.copy(syncing = true, message = null, error = null) }
        viewModelScope.launch {
            try {
                val report = repository.sync()
                _ui.update { it.copy(syncing = false, message = describe(report)) }
            } catch (e: ApiException) {
                _ui.update { it.copy(syncing = false, error = e.message, signedOut = e.code == "UNAUTHORIZED") }
            }
        }
    }

    fun logout() {
        repository.logout()
        _ui.update { it.copy(signedOut = true) }
    }

    private fun describe(report: SyncReport): String {
        val parts = buildList {
            if (report.sent > 0) add("${report.sent} satış gönderildi")
            if (report.failed > 0) add("${report.failed} satış reddedildi")
            add(if (report.pulled == 0) "yeni değişiklik yok" else "${report.pulled} kayıt güncellendi")
        }
        return parts.joinToString(" · ").replaceFirstChar { it.uppercaseChar() } + "."
    }

    private fun <T> Flow<T>.asState(initial: T): StateFlow<T> =
        stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)
}
