package com.synera.avatar.ui.dayend

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.ui.main.paymentLabel
import com.synera.avatar.ui.theme.Banner
import com.synera.avatar.ui.theme.Panel
import com.synera.avatar.ui.theme.SectionTitle
import com.synera.avatar.ui.theme.StatBox
import com.synera.avatar.ui.theme.Tone
import com.synera.avatar.util.Dates
import com.synera.avatar.util.Money
import com.synera.avatar.util.Quantity
import com.synera.avatar.util.t

@Composable
fun DayEndTab(viewModel: DayEndViewModel, padding: PaddingValues) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val stock by viewModel.stock.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { if (ui.report == null) viewModel.load() }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { Spacer(Modifier.height(4.dp)) }
        if (ui.counting) {
            item { SectionTitle(t("Araç sayımı")) }
            item {
                Text(
                    t("Araçta saydığınız miktarı yazın. Saymadığınız lotu boş bırakın. Eksik çıkan mal fire olarak düşülür."),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            items(stock, key = { "c-${it.lotId}" }) { row ->
                Panel {
                    Text(row.productName, style = MaterialTheme.typography.titleSmall)
                    Text(t("Lot {lot} · SKT {date}", "lot" to row.lotNo, "date" to Dates.date(row.expiryDate)), style = MaterialTheme.typography.bodySmall)
                    OutlinedTextField(
                        value = ui.counted[row.lotNo].orEmpty(),
                        onValueChange = { viewModel.onCounted(row.lotNo, it) },
                        label = { Text(t("Sayılan ({unit})", "unit" to Quantity.unitLabel(row.baseUnit))) },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
            item { ui.countError?.let { Banner(it, Tone.DANGER) } }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(onClick = viewModel::cancelCount, modifier = Modifier.weight(1f).height(52.dp)) { Text(t("Vazgeç")) }
                    Button(onClick = viewModel::saveCount, enabled = !ui.saving, modifier = Modifier.weight(1f).height(52.dp)) {
                        Text(if (ui.saving) t("Gönderiliyor…") else t("Sayımı gönder"))
                    }
                }
            }
        } else {
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    SectionTitle(t("Bugünün özeti"), Modifier.weight(1f))
                    OutlinedButton(onClick = viewModel::load, enabled = !ui.loading) { Text(if (ui.loading) t("Yükleniyor…") else t("Yenile")) }
                }
            }
            ui.error?.let { item { Banner(t("Gün sonu için bağlantı gerekli. {error}", "error" to it), Tone.WARNING) } }
            ui.countResult?.let { result ->
                item {
                    val short = result.lines.count { it.difference.startsWith("-") }
                    Banner(
                        t("Sayım kaydedildi: {no}. Eksik lot: {short}, fazla lot: {surplus}.", "no" to result.countNo, "short" to short, "surplus" to result.surplusLines),
                        if (short > 0 || result.surplusLines > 0) Tone.WARNING else Tone.SUCCESS,
                    )
                }
            }
            ui.report?.let { report ->
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatBox(t("Satış"), Money.format(Money.toCents(report.salesAmount)), Modifier.weight(1f), Tone.SUCCESS, t("{n} belge", "n" to report.saleCount))
                        StatBox(t("İade"), Money.format(Money.toCents(report.refundAmount)), Modifier.weight(1f), Tone.WARNING)
                    }
                }
                item { StatBox(t("Net (satış − iade)"), Money.format(Money.toCents(report.netAmount)), Modifier.fillMaxWidth(), Tone.BRAND) }
                item { SectionTitle(t("Ödeme türüne göre")) }
                if (report.byPayment.isEmpty()) item { Text(t("Bugün satış yok."), style = MaterialTheme.typography.bodyMedium) }
                items(report.byPayment, key = { "p-${it.key}" }) { row ->
                    Panel {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(paymentLabel(row.key), style = MaterialTheme.typography.titleSmall)
                                Text(t("{n} belge", "n" to row.saleCount), style = MaterialTheme.typography.bodySmall)
                            }
                            Text(Money.format(Money.toCents(row.amount)), style = MaterialTheme.typography.titleMedium)
                        }
                    }
                }
                if (report.returns.isNotEmpty()) {
                    item { SectionTitle(t("İadeler")) }
                    items(report.returns, key = { "r-${it.returnNo}" }) { row ->
                        Panel(tone = Tone.WARNING) {
                            Text("${row.customerName} · ${row.lotNo}", style = MaterialTheme.typography.titleSmall)
                            Text(t("Geri ödenecek: {amount}", "amount" to Money.format(Money.toCents(row.refundAmount))))
                        }
                    }
                }
                item { SectionTitle(t("Araçta kalan mal (sunucuya göre)")) }
                if (report.stockLeft.isEmpty()) item { Text(t("Araçta mal kalmadı."), style = MaterialTheme.typography.bodyMedium) }
                items(report.stockLeft, key = { "l-${it.lotNo}" }) { row ->
                    Panel {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(row.productName, style = MaterialTheme.typography.titleSmall)
                                Text(t("Lot {lot} · SKT {date}", "lot" to row.lotNo, "date" to Dates.date(row.expiryDate)), style = MaterialTheme.typography.bodySmall)
                            }
                            Text(Quantity.format(Quantity.toMilli(row.qty), row.baseUnit), style = MaterialTheme.typography.titleSmall)
                        }
                    }
                }
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Spacer(Modifier.width(1.dp))
                    Button(onClick = viewModel::startCount, enabled = stock.isNotEmpty(), modifier = Modifier.fillMaxWidth().height(56.dp)) {
                        Text(t("Araç sayımı yap"))
                    }
                    Text(
                        t("Sayım ve gün sonu bağlantı ister; satış istemez."),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}
