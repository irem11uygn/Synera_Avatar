package com.synera.avatar.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.data.local.SaleSummaryRow
import com.synera.avatar.data.local.SyncState
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val dateTime = DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm")
private val date = DateTimeFormatter.ofPattern("dd.MM.yyyy")
private val warning = Color(0xFF9A6700)

private fun formatMillis(millis: Long): String = dateTime.format(Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault()))

@Composable
fun HomeScreen(viewModel: HomeViewModel, onNewSale: () -> Unit, onSignedOut: () -> Unit) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val products by viewModel.productCount.collectAsStateWithLifecycle()
    val customers by viewModel.customerCount.collectAsStateWithLifecycle()
    val vanStock by viewModel.vanStock.collectAsStateWithLifecycle()
    val syncMeta by viewModel.syncMeta.collectAsStateWithLifecycle()
    val pending by viewModel.pendingCount.collectAsStateWithLifecycle()
    val sales by viewModel.recentSales.collectAsStateWithLifecycle()

    LaunchedEffect(ui.signedOut) { if (ui.signedOut) onSignedOut() }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Row(Modifier.padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(viewModel.session?.fullName.orEmpty(), style = MaterialTheme.typography.titleMedium)
                    Text("Araç deposu: ${viewModel.session?.warehouseCode.orEmpty()}", style = MaterialTheme.typography.bodyMedium)
                }
                TextButton(onClick = viewModel::logout) { Text("Çıkış") }
            }
        }

        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Eşitleme", style = MaterialTheme.typography.titleSmall)
                    val last = syncMeta?.lastPullAtMillis
                    Text(if (last == null) "Henüz eşitlenmedi." else "Son eşitleme: " + formatMillis(last))
                    Text("$products ürün · $customers müşteri · ${vanStock.size} lot araçta")
                    if (pending > 0) {
                        Text("$pending satış gönderilmeyi bekliyor (bağlantı gelince gönderilir).", color = warning)
                    }
                    ui.message?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                    ui.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = onNewSale) { Text("Yeni satış") }
                        OutlinedButton(onClick = viewModel::refresh, enabled = !ui.syncing) {
                            Text(if (ui.syncing) "Eşitleniyor…" else "Verileri güncelle")
                        }
                    }
                }
            }
        }

        item { Text("Araç deposu stoku", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        if (vanStock.isEmpty()) {
            item {
                Text(
                    "Araç deposunda stok yok. Ana depodan araca yükleme yapıldığında burada görünür.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        items(vanStock, key = { "lot-${it.lotNo}" }) { VanStockItem(it) }

        item { Text("Son satışlar", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        if (sales.isEmpty()) {
            item { Text("Bu cihazda henüz satış yapılmadı.", style = MaterialTheme.typography.bodyMedium) }
        }
        items(sales, key = { "sale-${it.clientUuid}" }) { SaleItem(it) }
        item { Text("", Modifier.padding(bottom = 16.dp)) }
    }
}

@Composable
private fun VanStockItem(row: VanStockRow) {
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(row.productName, style = MaterialTheme.typography.titleSmall)
                val expiry = row.expiryDate?.let { " · SKT " + date.format(LocalDate.parse(it)) }.orEmpty()
                Text("Lot ${row.lotNo}$expiry", style = MaterialTheme.typography.bodySmall)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(Quantity.format(row.availableMilli, row.baseUnit), style = MaterialTheme.typography.titleSmall)
                if (row.availableMilli != row.qtyMilli) {
                    Text("araçta ${Quantity.format(row.qtyMilli, row.baseUnit)}, gönderilmemiş satış var", style = MaterialTheme.typography.labelSmall)
                }
                if (row.status == "BLOKE") {
                    Text("BLOKE — satılamaz", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

@Composable
private fun SaleItem(sale: SaleSummaryRow) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(sale.customerName ?: "Müşteri", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                Text(Money.format(sale.totalCents), style = MaterialTheme.typography.titleSmall)
            }
            Text("${formatMillis(sale.soldAtMillis)} · ${sale.lineCount} satır", style = MaterialTheme.typography.bodySmall)
            when (sale.syncState) {
                SyncState.PENDING -> Text("Gönderilmeyi bekliyor", style = MaterialTheme.typography.labelMedium, color = warning)
                SyncState.SENT -> Text("Gönderildi · ${sale.serverSaleNo.orEmpty()}", style = MaterialTheme.typography.labelMedium, color = Color(0xFF1A7F37))
                else -> Text("Reddedildi", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.error)
            }
            sale.serverMessage?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = if (sale.syncState == SyncState.FAILED) MaterialTheme.colorScheme.error else warning)
            }
        }
    }
}
