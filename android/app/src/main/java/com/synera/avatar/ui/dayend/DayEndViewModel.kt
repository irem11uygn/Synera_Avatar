package com.synera.avatar.ui.dayend

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.remote.DayEndDto
import com.synera.avatar.data.remote.StockCountResponse
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.t
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate

data class DayEndUiState(
    val loading: Boolean = false,
    val report: DayEndDto? = null,
    val error: String? = null,
    val counting: Boolean = false,
    val counted: Map<String, String> = emptyMap(), // lot no → yazılan miktar
    val countError: String? = null,
    val saving: Boolean = false,
    val countResult: StockCountResponse? = null,
)

/** Gün sonu (sunucudan) ve araç sayımı. İkisi de bağlantı ister; satış yapmak istemez. */
class DayEndViewModel(private val repository: AvatarRepository) : ViewModel() {
    val stock: StateFlow<List<VanStockRow>> =
        repository.observeVanStock().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _ui = MutableStateFlow(DayEndUiState())
    val ui: StateFlow<DayEndUiState> = _ui.asStateFlow()

    fun load() {
        if (_ui.value.loading) return
        _ui.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            try {
                runCatching { repository.sync() } // önce bekleyen satışlar gönderilsin ki rapora girsin
                val report = repository.dayEnd(LocalDate.now())
                _ui.update { it.copy(loading = false, report = report) }
            } catch (e: ApiException) {
                _ui.update { it.copy(loading = false, error = e.message) }
            }
        }
    }

    fun startCount() = _ui.update { it.copy(counting = true, counted = emptyMap(), countError = null, countResult = null) }

    fun cancelCount() = _ui.update { it.copy(counting = false, countError = null) }

    fun onCounted(lotNo: String, value: String) = _ui.update { it.copy(counted = it.counted + (lotNo to value), countError = null) }

    fun saveCount() {
        val state = _ui.value
        val entered = state.counted.filterValues { it.isNotBlank() }
        if (entered.isEmpty()) {
            _ui.update { it.copy(countError = t("En az bir lotun sayılan miktarını yazın.")) }
            return
        }
        val parsed = entered.mapValues { (_, text) -> Quantity.parseInput(text) }
        val invalid = parsed.filterValues { it == null }.keys
        if (invalid.isNotEmpty()) {
            _ui.update { it.copy(countError = t("Geçersiz miktar: {lots}", "lots" to invalid.joinToString(", "))) }
            return
        }
        _ui.update { it.copy(saving = true, countError = null) }
        viewModelScope.launch {
            try {
                val result = repository.countVan(parsed.mapValues { it.value!! }, t("Araç gün sonu sayımı"))
                _ui.update { it.copy(saving = false, counting = false, countResult = result) }
                load()
            } catch (e: ApiException) {
                _ui.update { it.copy(saving = false, countError = e.message) }
            }
        }
    }
}
