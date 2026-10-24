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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.util.Quantity
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val dateTime = DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm")
private val date = DateTimeFormatter.ofPattern("dd.MM.yyyy")

@Composable
fun HomeScreen(viewModel: HomeViewModel, onSignedOut: () -> Unit) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val products by viewModel.productCount.collectAsStateWithLifecycle()
    val customers by viewModel.customerCount.collectAsStateWithLifecycle()
    val vanStock by viewModel.vanStock.collectAsStateWithLifecycle()
    val syncMeta by viewModel.syncMeta.collectAsStateWithLifecycle()

    LaunchedEffect(ui.signedOut) { if (ui.signedOut) onSignedOut() }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(viewModel.session?.fullName.orEmpty(), style = MaterialTheme.typography.titleMedium)
                Text("Araç deposu: ${viewModel.session?.warehouseCode.orEmpty()}", style = MaterialTheme.typography.bodyMedium)
            }
            TextButton(onClick = viewModel::logout) { Text("Çıkış") }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Eşitleme", style = MaterialTheme.typography.titleSmall)
                val last = syncMeta?.lastPullAtMillis
                Text(
                    if (last == null) "Henüz eşitlenmedi."
                    else "Son eşitleme: " + dateTime.format(Instant.ofEpochMilli(last).atZone(ZoneId.systemDefault())),
                )
                Text("$products ürün · $customers müşteri · ${vanStock.size} lot araçta")
                ui.message?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                ui.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Button(onClick = viewModel::refresh, enabled = !ui.syncing) {
                    Text(if (ui.syncing) "Eşitleniyor…" else "Verileri güncelle")
                }
            }
        }

        Text("Araç deposu stoku", style = MaterialTheme.typography.titleMedium)
        if (vanStock.isEmpty()) {
            Text(
                "Araç deposunda stok yok. Ana depodan araca yükleme yapıldığında burada görünür.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(vanStock, key = { it.lotNo }) { VanStockItem(it) }
        }
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
                Text(Quantity.format(row.qtyMilli, row.baseUnit), style = MaterialTheme.typography.titleSmall)
                if (row.status == "BLOKE") {
                    Text("BLOKE — satılamaz", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}
