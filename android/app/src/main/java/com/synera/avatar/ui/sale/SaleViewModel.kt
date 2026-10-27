package com.synera.avatar.ui.sale

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.local.CustomerEntity
import com.synera.avatar.data.local.SaleNotAllowed
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.LotPick
import com.synera.avatar.data.repo.SaleLineDraft
import com.synera.avatar.data.repo.SaleRules
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
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

enum class Step { CUSTOMER, PRODUCTS, PAYMENT, SUMMARY }

/** Sepetteki bir ürün; miktar FEFO ile bir ya da birkaç lota bölünmüştür. */
data class CartLine(
    val productId: Long,
    val productName: String,
    val baseUnit: String,
    val qtyMilli: Long,
    val unitPriceCents: Long,
    val picks: List<LotPick>,
) {
    val amountCents: Long = picks.sumOf { SaleRules.amountCents(it.qtyMilli, unitPriceCents) }
}

/** Satılabilir ürün özeti (ürün seçme listesi). */
data class ProductChoice(val productId: Long, val name: String, val baseUnit: String, val priceCents: Long?, val sellableMilli: Long, val nearestExpiry: String?)

data class SaleUiState(
    val step: Step = Step.CUSTOMER,
    val customerQuery: String = "",
    val customerId: Long? = null,
    val lines: List<CartLine> = emptyList(),
    val editingProductId: Long? = null,
    val qtyText: String = "",
    val priceText: String = "",
    val lineError: String? = null,
    val payment: String? = null,
    val error: String? = null,
    val saving: Boolean = false,
    val saved: Boolean = false,
) {
    val totalCents: Long get() = lines.sumOf { it.amountCents }
}

/** Satış sihirbazı: kayıt telefonda yapılır, gönderim arka planda (bağlantı yoksa sonra). */
class SaleViewModel(private val repository: AvatarRepository, private val today: () -> LocalDate = LocalDate::now) : ViewModel() {
    val customers: StateFlow<List<CustomerEntity>> = repository.observeCustomers().asState(emptyList())
    val stock: StateFlow<List<VanStockRow>> = repository.observeVanStock().asState(emptyList())

    private val _ui = MutableStateFlow(SaleUiState())
    val ui: StateFlow<SaleUiState> = _ui.asStateFlow()

    /** Sepette lot başına ayrılmış miktar. */
    private fun reserved(lines: List<CartLine>): Map<Long, Long> =
        lines.flatMap { it.picks }.groupBy { it.lot.lotId }.mapValues { (_, picks) -> picks.sumOf { it.qtyMilli } }

    fun productChoices(rows: List<VanStockRow>, lines: List<CartLine>): List<ProductChoice> {
        val date = today()
        val held = reserved(lines)
        return rows.filter { SaleRules.isSellable(it, date) }
            .groupBy { it.productId }
            .map { (productId, lots) ->
                val first = lots.first()
                ProductChoice(
                    productId = productId,
                    name = first.productName,
                    baseUnit = first.baseUnit,
                    priceCents = first.salePriceCents,
                    sellableMilli = lots.sumOf { (it.availableMilli - (held[it.lotId] ?: 0)).coerceAtLeast(0) },
                    nearestExpiry = lots.mapNotNull { it.expiryDate }.minOrNull(),
                )
            }
            .filter { it.sellableMilli > 0 }
            .sortedBy { it.name }
    }

    fun onCustomerQuery(value: String) = _ui.update { it.copy(customerQuery = value) }

    fun selectCustomer(id: Long) = _ui.update { it.copy(customerId = id, error = null, step = Step.PRODUCTS) }

    fun goTo(step: Step) = _ui.update { it.copy(step = step, error = null) }

    fun editProduct(choice: ProductChoice) = _ui.update {
        it.copy(
            editingProductId = choice.productId,
            qtyText = if (choice.baseUnit == "ADET") "1" else "",
            priceText = choice.priceCents?.let { cents -> Money.fromCents(cents).toPlainString().replace('.', ',') }.orEmpty(),
            lineError = null,
        )
    }

    fun cancelEdit() = _ui.update { it.copy(editingProductId = null, lineError = null) }

    fun onQtyChange(value: String) = _ui.update { it.copy(qtyText = value, lineError = null) }

    fun onPriceChange(value: String) = _ui.update { it.copy(priceText = value, lineError = null) }

    fun addLine() {
        val state = _ui.value
        val productId = state.editingProductId ?: return
        val lots = stock.value.filter { it.productId == productId }
        val first = lots.firstOrNull() ?: return
        val qty = Quantity.parseInput(state.qtyText)
        val price = Money.parseInput(state.priceText)
        val error = when {
            qty == null -> t("Geçerli bir miktar yazın (en çok 3 ondalık, binlik ayırıcı olmadan).")
            qty <= 0 -> t("Miktar sıfırdan büyük olmalı.")
            first.baseUnit == "ADET" && qty % 1000 != 0L -> t("Bu ürün adet ile satılır; tam sayı girin.")
            price == null -> t("Geçerli bir birim fiyat yazın (ör. 24,90).")
            else -> null
        }
        if (error != null || qty == null || price == null) {
            _ui.update { it.copy(lineError = error) }
            return
        }
        val (picks, short) = SaleRules.allocate(lots, productId, qty, today(), reserved(state.lines))
        if (short > 0) {
            _ui.update { it.copy(lineError = t("Araçta satılabilir miktar yetmiyor: {qty} eksik.", "qty" to Quantity.format(short, first.baseUnit))) }
            return
        }
        val line = CartLine(productId, first.productName, first.baseUnit, qty, price, picks)
        _ui.update { it.copy(lines = it.lines + line, editingProductId = null, qtyText = "", priceText = "", lineError = null, error = null) }
    }

    fun removeLine(index: Int) = _ui.update { it.copy(lines = it.lines.filterIndexed { i, _ -> i != index }) }

    fun selectPayment(method: String) = _ui.update { it.copy(payment = method, error = null, step = Step.SUMMARY) }

    fun save() {
        val state = _ui.value
        val customer = state.customerId
        when {
            customer == null -> _ui.update { it.copy(error = t("Müşteriyi seçin."), step = Step.CUSTOMER) }
            state.lines.isEmpty() -> _ui.update { it.copy(error = t("En az bir ürün ekleyin."), step = Step.PRODUCTS) }
            state.payment == null -> _ui.update { it.copy(error = t("Ödeme türünü seçin."), step = Step.PAYMENT) }
            else -> {
                _ui.update { it.copy(saving = true, error = null) }
                viewModelScope.launch {
                    try {
                        repository.createSale(
                            customer,
                            state.lines.flatMap { line ->
                                line.picks.map { SaleLineDraft(it.lot.lotId, it.lot.lotNo, line.productId, it.qtyMilli, line.unitPriceCents) }
                            },
                            state.payment,
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
