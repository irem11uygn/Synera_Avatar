package com.synera.avatar.ui.theme

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

/** Durum tonu: renk anlam taşır, ama yanında her zaman yazı da vardır. */
enum class Tone { NORMAL, BRAND, DANGER, SUCCESS, WARNING }

private fun toneColor(tone: Tone): Color? = when (tone) {
    Tone.NORMAL -> null
    Tone.BRAND -> Brand.Primary
    Tone.DANGER -> Brand.Danger
    Tone.SUCCESS -> Brand.Success
    Tone.WARNING -> Brand.Warning
}

private fun toneSoft(tone: Tone): Color = when (tone) {
    Tone.DANGER -> Brand.DangerSoft
    Tone.SUCCESS -> Brand.SuccessSoft
    Tone.WARNING -> Brand.WarningSoft
    else -> Brand.PrimarySoft
}

/** Düz kart: ince kenarlık; tonlu kartta solda renk şeridi. Tıklanabilirse en az 48 dp yükseklikte. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    tone: Tone = Tone.NORMAL,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) Brand.Primary else MaterialTheme.colorScheme.outlineVariant)
    val colors = CardDefaults.outlinedCardColors(containerColor = if (selected) Brand.PrimarySoft else MaterialTheme.colorScheme.surface)
    val body: @Composable ColumnScope.() -> Unit = {
        Row(Modifier.height(IntrinsicSize.Min)) {
            toneColor(tone)?.let { Box(Modifier.width(4.dp).fillMaxHeight().background(it)) }
            Column(Modifier.padding(14.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp), content = content)
        }
    }
    val shape = RoundedCornerShape(10.dp)
    if (onClick != null) {
        OutlinedCard(onClick = onClick, modifier = modifier.fillMaxWidth(), shape = shape, border = border, colors = colors, content = body)
    } else {
        OutlinedCard(modifier = modifier.fillMaxWidth(), shape = shape, border = border, colors = colors, content = body)
    }
}

/** Özet kutusu: etiket, büyük değer, kısa açıklama. */
@Composable
fun StatBox(label: String, value: String, modifier: Modifier = Modifier, tone: Tone = Tone.NORMAL, hint: String? = null) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = if (tone == Tone.NORMAL) MaterialTheme.colorScheme.surface else toneSoft(tone)),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleLarge, color = toneColor(tone) ?: MaterialTheme.colorScheme.onSurface)
            hint?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
    }
}

/** Küçük durum etiketi (ör. "Satışa kapalı", "2 gün kaldı"). */
@Composable
fun Badge(text: String, tone: Tone) {
    Text(
        text,
        style = MaterialTheme.typography.labelMedium,
        color = toneColor(tone) ?: MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.clip(RoundedCornerShape(6.dp)).background(toneSoft(tone)).padding(horizontal = 8.dp, vertical = 3.dp),
    )
}

/** Sayfanın üstündeki bilgi şeridi (bekleyen satış, bağlantı hatası, eşitleme sonucu). */
@Composable
fun Banner(text: String, tone: Tone, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(toneSoft(tone)).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, style = MaterialTheme.typography.bodyMedium, color = toneColor(tone) ?: MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        modifier = modifier.padding(top = 12.dp, bottom = 2.dp).semantics { heading() },
    )
}
