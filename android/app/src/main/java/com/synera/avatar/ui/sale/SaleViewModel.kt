package com.synera.avatar.ui.sale

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.local.CustomerEntity
import com.synera.avatar.data.local.SaleNotAllowed
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.SaleLineDraft
import com.synera.avatar.data.repo.SaleRules
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DraftLine(val lot: VanStockRow, val qtyMilli: Long, val unitPriceCents: Long) {
    val amountCents: Long = SaleRules.amountCents(qtyMilli, unitPriceCents)
}

data class SaleUiState(
    val customerId: Long? = null,
    val lines: List<DraftLine> = emptyList(),
    val selectedLotId: Long? = null,
    val qtyText: String = "",
    val priceText: String = "",
    val lineError: String? = null,
    val error: String? = null,
    val saving: Boolean = false,
    val saved: Boolean = false,
) {
    val totalCents: Long get() = lines.sumOf { it.amountCents }
}

/** Satış taslağı: müşteri, lot bazında satırlar (FR-401); kayıt cihazda, gönderim arka planda. */
class SaleViewModel(private val repository: AvatarRepository) : ViewModel() {
    val customers: StateFlow<List<CustomerEntity>> = repository.observeCustomers().asState(emptyList())
    val stock: StateFlow<List<VanStockRow>> = repository.observeVanStock().asState(emptyList())

    private val _ui = MutableStateFlow(SaleUiState())
    val ui: StateFlow<SaleUiState> = _ui.asStateFlow()

    fun selectCustomer(id: Long) = _ui.update { it.copy(customerId = id, error = null) }

    fun selectLot(row: VanStockRow) = _ui.update {
        it.copy(
            selectedLotId = row.lotId,
            qtyText = "",
            // Liste fiyatı (VKP) gelir, satırda değiştirilebilir (architecture.md §15).
            priceText = row.salePriceCents?.let { cents -> Money.fromCents(cents).toPlainString().replace('.', ',') }.orEmpty(),
            lineError = null,
        )
    }

    fun onQtyChange(value: String) = _ui.update { it.copy(qtyText = value, lineError = null) }

    fun onPriceChange(value: String) = _ui.update { it.copy(priceText = value, lineError = null) }

    fun addLine() {
        val state = _ui.value
        val row = stock.value.firstOrNull { it.lotId == state.selectedLotId } ?: return
        val qty = Quantity.parseInput(state.qtyText)
        val inDraft = state.lines.filter { it.lot.lotId == row.lotId }.sumOf { it.qtyMilli }
        val qtyError = SaleRules.lineError(row.baseUnit, row.status, qty, row.availableMilli, inDraft)
        val price = Money.parseInput(state.priceText)
        val error = qtyError ?: if (price == null) "Geçerli bir birim fiyat yazın (ör. 24,90)." else null
        if (error != null || qty == null || price == null) {
            _ui.update { it.copy(lineError = error) }
            return
        }
        _ui.update {
            it.copy(lines = it.lines + DraftLine(row, qty, price), selectedLotId = null, qtyText = "", priceText = "", error = null)
        }
    }

    fun removeLine(index: Int) = _ui.update { it.copy(lines = it.lines.filterIndexed { i, _ -> i != index }) }

    fun save() {
        val state = _ui.value
        val customer = state.customerId
        when {
            customer == null -> _ui.update { it.copy(error = "Müşteri seçin.") }
            state.lines.isEmpty() -> _ui.update { it.copy(error = "En az bir satır ekleyin.") }
            else -> {
                _ui.update { it.copy(saving = true, error = null) }
                viewModelScope.launch {
                    try {
                        repository.createSale(
                            customer,
                            state.lines.map { SaleLineDraft(it.lot.lotId, it.lot.lotNo, it.lot.productId, it.qtyMilli, it.unitPriceCents) },
                        )
                        _ui.update { it.copy(saving = false, saved = true) }
                    } catch (e: SaleNotAllowed) {
                        _ui.update { it.copy(saving = false, error = e.message) }
                    }
                }
            }
        }
    }

    private fun <T> Flow<T>.asState(initial: T): StateFlow<T> =
        stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)
}
