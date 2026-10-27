package com.synera.avatar.ui.sale

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.data.local.Payment
import com.synera.avatar.ui.main.paymentLabel
import com.synera.avatar.ui.theme.Badge
import com.synera.avatar.ui.theme.Banner
import com.synera.avatar.ui.theme.Panel
import com.synera.avatar.ui.theme.SectionTitle
import com.synera.avatar.ui.theme.Tone
import com.synera.avatar.util.Dates
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.t

private fun stepTitle(step: Step): String = when (step) {
    Step.CUSTOMER -> t("1/4 · Müşteri")
    Step.PRODUCTS -> t("2/4 · Ürünler")
    Step.PAYMENT -> t("3/4 · Ödeme")
    Step.SUMMARY -> t("4/4 · Özet ve kayıt")
}

@Composable
fun SaleScreen(viewModel: SaleViewModel, onClose: () -> Unit) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    LaunchedEffect(ui.saved) { if (ui.saved) onClose() }
    // Geri tuşu bir önceki adıma döner; ilk adımda satıştan çıkar.
    BackHandler {
        when {
            ui.editingProductId != null -> viewModel.cancelEdit()
            ui.step == Step.CUSTOMER -> onClose()
            else -> viewModel.goTo(Step.entries[ui.step.ordinal - 1])
        }
    }

    Column(Modifier.fillMaxSize().imePadding()) {
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, top = 12.dp, end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(t("Yeni satış"), style = MaterialTheme.typography.titleLarge)
                Text(stepTitle(ui.step), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            TextButton(onClick = onClose) { Text(t("Vazgeç")) }
        }
        LinearProgressIndicator(
            progress = { (ui.step.ordinal + 1) / Step.entries.size.toFloat() },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        )
        Column(Modifier.weight(1f)) {
            when (ui.step) {
                Step.CUSTOMER -> CustomerStep(viewModel)
                Step.PRODUCTS -> ProductStep(viewModel)
                Step.PAYMENT -> PaymentStep(viewModel)
                Step.SUMMARY -> SummaryStep(viewModel)
            }
        }
        BottomBar(viewModel)
    }
}

@Composable
private fun BottomBar(viewModel: SaleViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    Surface(tonalElevation = 3.dp) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            ui.error?.let { Banner(it, Tone.DANGER) }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(t("Toplam"), style = MaterialTheme.typography.bodySmall)
                    Text(Money.format(ui.totalCents), style = MaterialTheme.typography.titleLarge)
                }
                when (ui.step) {
                    Step.CUSTOMER -> {}
                    Step.PRODUCTS -> Button(
                        onClick = { viewModel.goTo(Step.PAYMENT) },
                        enabled = ui.lines.isNotEmpty() && ui.editingProductId == null,
                        modifier = Modifier.height(52.dp),
                    ) { Text(t("Ödemeye geç")) }
                    Step.PAYMENT -> {}
                    Step.SUMMARY -> Button(onClick = viewModel::save, enabled = !ui.saving, modifier = Modifier.height(52.dp)) {
                        Text(if (ui.saving) t("Kaydediliyor…") else t("Satışı kaydet"))
                    }
                }
            }
        }
    }
}

@Composable
private fun CustomerStep(viewModel: SaleViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val customers by viewModel.customers.collectAsStateWithLifecycle()
    val query = ui.customerQuery.trim()
    val shown = customers.filter { query.isEmpty() || it.name.contains(query, ignoreCase = true) || it.code.contains(query, ignoreCase = true) }
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            OutlinedTextField(
                value = ui.customerQuery,
                onValueChange = viewModel::onCustomerQuery,
                label = { Text(t("Müşteri ara")) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (customers.isEmpty()) item { Banner(t("Müşteri listesi boş. Önce verileri güncelleyin."), Tone.WARNING) }
        items(shown, key = { "c-${it.id}" }) { customer ->
            Panel(selected = ui.customerId == customer.id, onClick = { viewModel.selectCustomer(customer.id) }) {
                Text(customer.name, style = MaterialTheme.typography.titleSmall)
                val detail = listOfNotNull(customer.contactPerson, customer.phone).joinToString(" · ")
                if (detail.isNotEmpty()) Text(detail, style = MaterialTheme.typography.bodySmall)
            }
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun ProductStep(viewModel: SaleViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val stock by viewModel.stock.collectAsStateWithLifecycle()
    val choices = viewModel.productChoices(stock, ui.lines)
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (ui.lines.isNotEmpty()) {
            item { SectionTitle(t("Sepet")) }
            itemsIndexed(ui.lines) { index, line ->
                Panel {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(line.productName, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "${Quantity.format(line.qtyMilli, line.baseUnit)} × ${Money.format(line.unitPriceCents)}",
                                style = MaterialTheme.typography.bodySmall,
                            )
                            Text(
                                line.picks.joinToString(" · ") { "${it.lot.lotNo}: ${Quantity.format(it.qtyMilli, line.baseUnit)}" },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(Money.format(line.amountCents), style = MaterialTheme.typography.titleSmall)
                            TextButton(onClick = { viewModel.removeLine(index) }) { Text(t("Çıkar")) }
                        }
                    }
                }
            }
        }
        item { SectionTitle(t("Ürün ekle")) }
        item {
            Text(
                t("Ürüne dokunun, miktarı yazın. Lot kendiliğinden seçilir: son kullanma tarihi en yakın olan önce satılır."),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (choices.isEmpty()) item { Banner(t("Araçta satılabilir ürün kalmadı."), Tone.WARNING) }
        items(choices, key = { "p-${it.productId}" }) { choice ->
            val editing = ui.editingProductId == choice.productId
            Panel(selected = editing, onClick = if (editing) null else ({ viewModel.editProduct(choice) })) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(choice.name, style = MaterialTheme.typography.titleSmall)
                        Text(
                            t("Araçta {qty} · en yakın SKT {date}", "qty" to Quantity.format(choice.sellableMilli, choice.baseUnit), "date" to Dates.date(choice.nearestExpiry)),
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    choice.priceCents?.let { Text(Money.format(it), style = MaterialTheme.typography.titleSmall) }
                }
                if (editing) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = ui.qtyText,
                            onValueChange = viewModel::onQtyChange,
                            label = { Text(t("Miktar ({unit})", "unit" to Quantity.unitLabel(choice.baseUnit))) },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.weight(1f),
                        )
                        OutlinedTextField(
                            value = ui.priceText,
                            onValueChange = viewModel::onPriceChange,
                            label = { Text(t("Birim fiyat (€)")) },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.weight(1f),
                        )
                    }
                    ui.lineError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = viewModel::cancelEdit, modifier = Modifier.weight(1f)) { Text(t("Vazgeç")) }
                        Button(onClick = viewModel::addLine, modifier = Modifier.weight(1f)) { Text(t("Sepete ekle")) }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun PaymentStep(viewModel: SaleViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(t("Müşteri nasıl ödedi?"), style = MaterialTheme.typography.titleMedium)
        for (method in Payment.ALL) {
            Panel(selected = ui.payment == method, onClick = { viewModel.selectPayment(method) }) {
                Text(paymentLabel(method), style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 6.dp))
                if (method == Payment.CREDIT) Text(t("Müşterinin hesabına yazılır."), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun SummaryStep(viewModel: SaleViewModel) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val customers by viewModel.customers.collectAsStateWithLifecycle()
    val customer = customers.firstOrNull { it.id == ui.customerId }
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Panel(onClick = { viewModel.goTo(Step.CUSTOMER) }) {
                Text(t("Müşteri"), style = MaterialTheme.typography.bodySmall)
                Text(customer?.name ?: "—", style = MaterialTheme.typography.titleMedium)
            }
        }
        item {
            Panel(onClick = { viewModel.goTo(Step.PAYMENT) }) {
                Text(t("Ödeme"), style = MaterialTheme.typography.bodySmall)
                Text(paymentLabel(ui.payment), style = MaterialTheme.typography.titleMedium)
            }
        }
        item { SectionTitle(t("Ürünler")) }
        items(ui.lines, key = { "l-${it.productId}-${it.qtyMilli}-${it.unitPriceCents}" }) { line ->
            Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Row {
                    Text(line.productName, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                    Text(Money.format(line.amountCents), style = MaterialTheme.typography.titleSmall)
                }
                Text("${Quantity.format(line.qtyMilli, line.baseUnit)} × ${Money.format(line.unitPriceCents)}", style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    line.picks.forEach { Badge("${it.lot.lotNo} · ${Quantity.format(it.qtyMilli, line.baseUnit)}", Tone.NORMAL) }
                }
                HorizontalDivider(Modifier.padding(top = 8.dp))
            }
        }
        item {
            Text(
                t("Satış önce telefona kaydedilir; bağlantı varsa hemen, yoksa bağlantı gelince sunucuya gönderilir."),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
