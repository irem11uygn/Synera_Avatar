package com.synera.avatar.ui.main

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.data.local.Payment
import com.synera.avatar.data.local.SaleSummaryRow
import com.synera.avatar.data.local.SyncState
import com.synera.avatar.data.local.VanStockRow
import com.synera.avatar.data.repo.SaleRules
import com.synera.avatar.ui.dayend.DayEndTab
import com.synera.avatar.ui.dayend.DayEndViewModel
import com.synera.avatar.ui.theme.AppIcons
import com.synera.avatar.ui.theme.Badge
import com.synera.avatar.ui.theme.Banner
import com.synera.avatar.ui.theme.Brand
import com.synera.avatar.ui.theme.Panel
import com.synera.avatar.ui.theme.SectionTitle
import com.synera.avatar.ui.theme.StatBox
import com.synera.avatar.ui.theme.Tone
import com.synera.avatar.util.Dates
import com.synera.avatar.util.L
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.expiryLabel
import com.synera.avatar.util.t
import java.time.LocalDate

enum class Tab { SALES, STOCK, HISTORY, DAY_END }

fun paymentLabel(method: String?): String = when (method) {
    Payment.CASH -> t("Nakit")
    Payment.CARD -> t("Kredi kartı")
    Payment.TRANSFER -> t("Havale / EFT")
    Payment.CREDIT -> t("Veresiye")
    else -> t("Belirtilmedi")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: MainViewModel,
    dayEnd: DayEndViewModel,
    onNewSale: () -> Unit,
    onSignedOut: () -> Unit,
    onOpenSettings: () -> Unit,
    onPasswordRequired: () -> Unit,
) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableStateOf(Tab.SALES) }
    var menu by remember { mutableStateOf(false) }
    LaunchedEffect(ui.signedOut) { if (ui.signedOut) onSignedOut() }
    LaunchedEffect(ui.passwordRequired) { if (ui.passwordRequired) onPasswordRequired() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(viewModel.session?.fullName.orEmpty(), style = MaterialTheme.typography.titleMedium)
                        Text(
                            t("Araç {code}", "code" to viewModel.session?.warehouseCode.orEmpty()),
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White.copy(alpha = 0.82f),
                        )
                    }
                },
                // Web'deki turkuaz menüyle aynı kimlik: turkuaz üst çubuk, beyaz yazı.
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Brand.Primary,
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White,
                ),
                actions = {
                    IconButton(onClick = viewModel::refresh, enabled = !ui.syncing) {
                        Icon(AppIcons.Sync, contentDescription = t("Verileri güncelle"))
                    }
                    IconButton(onClick = { menu = true }) { Icon(AppIcons.More, contentDescription = t("Menü")) }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text(t("Ayarlar")) }, onClick = { menu = false; onOpenSettings() })
                        HorizontalDivider()
                        DropdownMenuItem(
                            text = { Text(if (L.lang == L.TR) "✓ Türkçe" else "Türkçe") },
                            onClick = { L.select(L.TR); menu = false },
                        )
                        DropdownMenuItem(
                            text = { Text(if (L.lang == L.EN) "✓ English" else "English") },
                            onClick = { L.select(L.EN); menu = false },
                        )
                        HorizontalDivider()
                        DropdownMenuItem(text = { Text(t("Çıkış yap")) }, onClick = { menu = false; viewModel.logout() })
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(tab == Tab.SALES, { tab = Tab.SALES }, { Icon(AppIcons.Sale, null) }, label = { Text(t("Satış")) })
                NavigationBarItem(tab == Tab.STOCK, { tab = Tab.STOCK }, { Icon(AppIcons.Stock, null) }, label = { Text(t("Stok")) })
                NavigationBarItem(tab == Tab.HISTORY, { tab = Tab.HISTORY }, { Icon(AppIcons.History, null) }, label = { Text(t("Geçmiş")) })
                NavigationBarItem(tab == Tab.DAY_END, { tab = Tab.DAY_END }, { Icon(AppIcons.DayEnd, null) }, label = { Text(t("Gün sonu")) })
            }
        },
    ) { padding ->
        when (tab) {
            Tab.SALES -> SalesTab(viewModel, onNewSale, padding)
            Tab.STOCK -> StockTab(viewModel, padding)
            Tab.HISTORY -> HistoryTab(viewModel, padding)
            Tab.DAY_END -> DayEndTab(dayEnd, padding)
        }
    }
}

/** Sekmelerin ortak kaydırılabilir gövdesi. */
@Composable
private fun TabBody(padding: PaddingValues, content: LazyListScope.() -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = {
            item { Spacer(Modifier.height(4.dp)) }
            content()
            item { Spacer(Modifier.height(16.dp)) }
        },
    )
}

@Composable
private fun SyncBanner(viewModel: MainViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val pending by viewModel.pendingCount.collectAsStateWithLifecycle()
    val meta by viewModel.syncMeta.collectAsStateWithLifecycle()
    when {
        ui.syncing -> Banner(t("Eşitleniyor…"), Tone.BRAND)
        ui.error != null -> Banner(ui.error.orEmpty(), Tone.DANGER)
        ui.offline && pending > 0 -> Banner(t("Bağlantı yok. {n} satış telefonda bekliyor; bağlantı gelince kendiliğinden gönderilir.", "n" to pending), Tone.WARNING)
        ui.offline -> Banner(t("Bağlantı yok. Satış yapabilirsiniz; bağlantı gelince gönderilir."), Tone.WARNING)
        pending > 0 -> Banner(t("{n} satış gönderilmeyi bekliyor.", "n" to pending), Tone.WARNING)
        ui.report != null -> Banner(describe(ui.report!!), Tone.SUCCESS)
        else -> {
            val last = meta?.lastPullAtMillis
            Banner(
                if (last == null) t("Henüz eşitlenmedi.") else t("Güncel · son eşitleme {at}", "at" to Dates.dateTime(last)),
                Tone.SUCCESS,
            )
        }
    }
}

@Composable
private fun SalesTab(viewModel: MainViewModel, onNewSale: () -> Unit, padding: PaddingValues) {
    val today by viewModel.todaySales.collectAsStateWithLifecycle()
    val stock by viewModel.vanStock.collectAsStateWithLifecycle()
    val date = LocalDate.now()
    val expired = stock.filter { SaleRules.isExpired(it, date) }
    val expiring = stock.filter { !SaleRules.isExpired(it, date) && expiryLabel(it.expiryDate, date) != null }
    val blocked = stock.filter { it.status == "BLOKE" }
    TabBody(padding) {
        item { SyncBanner(viewModel) }
        item {
            Button(onClick = onNewSale, modifier = Modifier.fillMaxWidth().height(64.dp)) {
                Text(t("Yeni satış"), style = MaterialTheme.typography.titleMedium)
            }
        }
        item { SectionTitle(t("Bugün")) }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatBox(t("Satış"), Money.format(today.sumOf { it.totalCents }), Modifier.weight(1f), Tone.SUCCESS, t("{n} belge", "n" to today.size))
                val cash = today.filter { it.paymentMethod == Payment.CASH }.sumOf { it.totalCents }
                StatBox(t("Nakit"), Money.format(cash), Modifier.weight(1f), hint = t("kasada olmalı"))
            }
        }
        if (blocked.isNotEmpty() || expired.isNotEmpty() || expiring.isNotEmpty()) item { SectionTitle(t("Dikkat")) }
        items(blocked, key = { "b-${it.lotId}" }) {
            Panel(tone = Tone.DANGER) {
                Text("${it.productName} · ${it.lotNo}", style = MaterialTheme.typography.titleSmall)
                Text(t("Geri çağrıldı: satmayın, ana depoya iade edin."), color = MaterialTheme.colorScheme.error)
            }
        }
        items(expired, key = { "x-${it.lotId}" }) {
            Panel(tone = Tone.DANGER) {
                Text("${it.productName} · ${it.lotNo}", style = MaterialTheme.typography.titleSmall)
                Text(t("Son kullanma tarihi geçti ({date}): satmayın, depoya iade edin.", "date" to Dates.date(it.expiryDate)), color = MaterialTheme.colorScheme.error)
            }
        }
        items(expiring, key = { "e-${it.lotId}" }) {
            Panel(tone = Tone.WARNING) {
                Text("${it.productName} · ${it.lotNo}", style = MaterialTheme.typography.titleSmall)
                Text(t("{label} — önce bunu satın.", "label" to expiryLabel(it.expiryDate, date)!!.first))
            }
        }
    }
}

@Composable
private fun StockTab(viewModel: MainViewModel, padding: PaddingValues) {
    val stock by viewModel.vanStock.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }
    val date = LocalDate.now()
    val shown = stock.filter {
        query.isBlank() || it.productName.contains(query.trim(), ignoreCase = true) || it.lotNo.contains(query.trim(), ignoreCase = true)
    }
    TabBody(padding) {
        item {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                label = { Text(t("Ürün ya da lot ara")) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        item {
            Text(
                t("Araçtaki mal, son kullanma tarihi en yakın olan üstte. Satarken önce üsttekini verin."),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (stock.isEmpty()) item { Banner(t("Araçta stok yok. Ana depodan yükleme yapılınca burada görünür."), Tone.NORMAL) }
        items(shown, key = { "s-${it.lotId}" }) { StockRowCard(it, date) }
    }
}

@Composable
fun StockRowCard(row: VanStockRow, date: LocalDate) {
    val blocked = row.status == "BLOKE"
    val expiry = expiryLabel(row.expiryDate, date)
    Panel(tone = if (blocked || expiry?.second == true) Tone.DANGER else if (expiry != null) Tone.WARNING else Tone.NORMAL) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(row.productName, style = MaterialTheme.typography.titleSmall)
                Text(t("Lot {lot} · SKT {date}", "lot" to row.lotNo, "date" to Dates.date(row.expiryDate)), style = MaterialTheme.typography.bodySmall)
            }
            Text(Quantity.format(row.availableMilli, row.baseUnit), style = MaterialTheme.typography.titleMedium)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (blocked) Badge(t("Satışa kapalı"), Tone.DANGER)
            expiry?.let { Badge(it.first, if (it.second) Tone.DANGER else Tone.WARNING) }
            if (row.availableMilli != row.qtyMilli) Badge(t("Gönderilmemiş satış var"), Tone.NORMAL)
        }
    }
}

@Composable
private fun HistoryTab(viewModel: MainViewModel, padding: PaddingValues) {
    val sales by viewModel.recentSales.collectAsStateWithLifecycle()
    TabBody(padding) {
        item { SectionTitle(t("Son satışlar")) }
        if (sales.isEmpty()) item { Banner(t("Bu telefonda henüz satış yapılmadı."), Tone.NORMAL) }
        items(sales, key = { "h-${it.clientUuid}" }) { SaleCard(it) }
    }
}

@Composable
private fun SaleCard(sale: SaleSummaryRow) {
    val tone = when (sale.syncState) {
        SyncState.PENDING -> Tone.WARNING
        SyncState.SENT -> if (sale.serverMessage != null) Tone.WARNING else Tone.NORMAL
        else -> Tone.DANGER
    }
    Panel(tone = tone) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(sale.customerName ?: t("Müşteri"), style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
            Text(Money.format(sale.totalCents), style = MaterialTheme.typography.titleSmall)
        }
        Text(
            "${Dates.dateTime(sale.soldAtMillis)} · ${paymentLabel(sale.paymentMethod)} · " + t("{n} kalem", "n" to sale.lineCount),
            style = MaterialTheme.typography.bodySmall,
        )
        when (sale.syncState) {
            SyncState.PENDING -> Badge(t("Gönderilmeyi bekliyor"), Tone.WARNING)
            SyncState.SENT -> Badge(t("Gönderildi · {no}", "no" to sale.serverSaleNo.orEmpty()), Tone.SUCCESS)
            else -> Badge(t("Reddedildi"), Tone.DANGER)
        }
        sale.serverMessage?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = if (sale.syncState == SyncState.FAILED) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
