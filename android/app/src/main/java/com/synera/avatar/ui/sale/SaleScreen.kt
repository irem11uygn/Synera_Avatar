package com.synera.avatar.ui.sale

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val date = DateTimeFormatter.ofPattern("dd.MM.yyyy")

@Composable
fun SaleScreen(viewModel: SaleViewModel, onClose: () -> Unit) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val customers by viewModel.customers.collectAsStateWithLifecycle()
    val stock by viewModel.stock.collectAsStateWithLifecycle()

    BackHandler(onBack = onClose)
    LaunchedEffect(ui.saved) { if (ui.saved) onClose() }

    // İlk biten ilk çıkar (FR-402): her ürünün satılabilir ilk lotu önerilir.
    val suggested = stock.filter { it.status != "BLOKE" && it.availableMilli > 0 }
        .groupBy { it.productId }
        .mapNotNull { (_, rows) -> rows.firstOrNull()?.lotId }
        .toSet()

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Row(Modifier.padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Yeni satış", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                TextButton(onClick = onClose) { Text("Vazgeç") }
            }
        }

        item { Text("Müşteri", style = MaterialTheme.typography.titleMedium) }
        items(customers, key = { "c-${it.id}" }) { customer ->
            Row(
                Modifier.fillMaxWidth()
                    .selectable(selected = ui.customerId == customer.id, onClick = { viewModel.selectCustomer(customer.id) }, role = Role.RadioButton)
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = ui.customerId == customer.id, onClick = null)
                Column(Modifier.padding(start = 8.dp)) {
                    Text(customer.name, style = MaterialTheme.typography.bodyLarge)
                    customer.contactPerson?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
            }
        }

        item { Text("Lot seçin (ilk biten önce)", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        if (stock.isEmpty()) item { Text("Araçta satılabilir stok yok. Önce \"Verileri güncelle\".") }
        items(stock, key = { "l-${it.lotId}" }) { row ->
            LotCard(
                row = row,
                suggested = row.lotId in suggested,
                selected = ui.selectedLotId == row.lotId,
                onSelect = { viewModel.selectLot(row) },
            )
            if (ui.selectedLotId == row.lotId) {
                LineEditor(row, ui.qtyText, ui.priceText, ui.lineError, viewModel::onQtyChange, viewModel::onPriceChange, viewModel::addLine)
            }
        }

        item { Text("Satırlar", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        if (ui.lines.isEmpty()) item { Text("Henüz satır yok.", style = MaterialTheme.typography.bodyMedium) }
        itemsIndexed(ui.lines) { index, line ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("${line.lot.productName} · ${line.lot.lotNo}", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        "${Quantity.format(line.qtyMilli, line.lot.baseUnit)} × ${Money.format(line.unitPriceCents)}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(Money.format(line.amountCents), style = MaterialTheme.typography.bodyMedium)
                TextButton(onClick = { viewModel.removeLine(index) }) { Text("Sil") }
            }
        }

        item {
            Column(Modifier.padding(vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Toplam: ${Money.format(ui.totalCents)}", style = MaterialTheme.typography.titleMedium)
                ui.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Button(onClick = viewModel::save, enabled = !ui.saving, modifier = Modifier.fillMaxWidth()) {
                    Text(if (ui.saving) "Kaydediliyor…" else "Satışı kaydet")
                }
                Text(
                    "Satış önce telefona kaydedilir; bağlantı varsa hemen, yoksa bağlantı gelince sunucuya gönderilir.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun LotCard(row: VanStockRow, suggested: Boolean, selected: Boolean, onSelect: () -> Unit) {
    val blocked = row.status == "BLOKE"
    val colors = if (selected) CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer) else CardDefaults.cardColors()
    Card(
        modifier = Modifier.fillMaxWidth().selectable(selected = selected, enabled = !blocked, onClick = onSelect, role = Role.Button),
        colors = colors,
    ) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(row.productName, style = MaterialTheme.typography.titleSmall)
                val expiry = row.expiryDate?.let { " · SKT " + date.format(LocalDate.parse(it)) }.orEmpty()
                Text("Lot ${row.lotNo}$expiry", style = MaterialTheme.typography.bodySmall)
                if (suggested) Text("Önerilen: ilk biten", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(Quantity.format(row.availableMilli, row.baseUnit), style = MaterialTheme.typography.titleSmall)
                if (blocked) Text("BLOKE — satılamaz", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun LineEditor(
    row: VanStockRow,
    qtyText: String,
    priceText: String,
    error: String?,
    onQty: (String) -> Unit,
    onPrice: (String) -> Unit,
    onAdd: () -> Unit,
) {
    val unit = if (row.baseUnit == "ADET") "adet" else "kg"
    Column(Modifier.fillMaxWidth().padding(horizontal = 4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = qtyText,
                onValueChange = onQty,
                label = { Text("Miktar ($unit)") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = priceText,
                onValueChange = onPrice,
                label = { Text("Birim fiyat (€)") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        Button(onClick = onAdd) { Text("Satıra ekle") }
    }
}
