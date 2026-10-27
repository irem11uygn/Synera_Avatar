package com.synera.avatar.ui.theme

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Kartın anlamı: rengi ve gölgesi buna göre (durum yalnız renkle değil, metinle de yazılır). */
enum class Tone { NORMAL, ACCENT, DANGER, SUCCESS, WARNING }

private val shape = RoundedCornerShape(18.dp)

private fun toneColor(tone: Tone): Color = when (tone) {
    Tone.NORMAL -> Color(0xFF94A3B8)
    Tone.ACCENT -> Brand.Primary
    Tone.DANGER -> Brand.Danger
    Tone.SUCCESS -> Brand.Success
    Tone.WARNING -> Brand.Warning
}

/**
 * Derinlikli kart: katmanlı gölge, ince kenar, hafif yüzey eğimi; dokununca kart içeri doğru eğilir
 * ve küçülür (3D basma hissi). Tıklanmayan kartta animasyon yoktur.
 */
@Composable
fun DepthCard(
    modifier: Modifier = Modifier,
    tone: Tone = Tone.NORMAL,
    selected: Boolean = false,
    enabled: Boolean = true,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val tilt by animateFloatAsState(if (pressed) 7f else 0f, spring(stiffness = 600f), label = "tilt")
    val scale by animateFloatAsState(if (pressed) 0.97f else 1f, spring(stiffness = 600f), label = "scale")
    val accent = toneColor(if (selected) Tone.ACCENT else tone)
    val dark = MaterialTheme.colorScheme.surface.red < 0.5f
    val face = when {
        tone == Tone.DANGER -> if (dark) Color(0xFF3A1D1D) else Color(0xFFFFF5F5)
        selected -> MaterialTheme.colorScheme.secondaryContainer
        else -> MaterialTheme.colorScheme.surface
    }
    val outer = modifier
        .fillMaxWidth()
        .graphicsLayer {
            rotationX = tilt
            scaleX = scale
            scaleY = scale
            cameraDistance = 14f * density
        }
        .shadow(if (pressed) 3.dp else 10.dp, shape, ambientColor = accent.copy(alpha = 0.25f), spotColor = accent.copy(alpha = 0.35f))
        .semantics { this.selected = selected }
    val colors = CardDefaults.cardColors(containerColor = face)
    val border = Modifier.border(1.dp, accent.copy(alpha = if (selected || tone != Tone.NORMAL) 0.55f else 0.18f), shape)
    val body: @Composable ColumnScope.() -> Unit = {
        Box(
            Modifier.fillMaxWidth().background(
                Brush.verticalGradient(listOf(Color.White.copy(alpha = if (dark) 0.04f else 0.55f), Color.Transparent)),
            ),
        ) {
            Column(Modifier.padding(14.dp), content = content)
        }
    }
    if (onClick != null) {
        Card(onClick = onClick, enabled = enabled, modifier = outer.then(border), shape = shape, colors = colors, interactionSource = interaction, content = body)
    } else {
        Card(modifier = outer.then(border), shape = shape, colors = colors, content = body)
    }
}

/** Gösterge kutusu: sol kenarında anlam rengi olan küçük derinlikli kart. */
@Composable
fun StatTile(label: String, value: String, modifier: Modifier = Modifier, tone: Tone = Tone.ACCENT, hint: String? = null) {
    DepthCard(modifier = modifier, tone = Tone.NORMAL) {
        Box(Modifier.size(width = 28.dp, height = 4.dp).background(toneColor(tone), RoundedCornerShape(2.dp)))
        Text(label, style = MaterialTheme.typography.labelMedium, modifier = Modifier.padding(top = 8.dp))
        Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
        hint?.let { Text(it, style = MaterialTheme.typography.labelSmall) }
    }
}

/** Ana ekranın üst bandı: koyu degrade zemin, üç boyutlu "A" logosu. */
@Composable
fun BrandBanner(title: String, subtitle: String, modifier: Modifier = Modifier) {
    Box(
        modifier
            .fillMaxWidth()
            .shadow(14.dp, shape, spotColor = Brand.Primary)
            .background(Brush.linearGradient(listOf(Color(0xFF0B1D3A), Color(0xFF13305F), Brand.Primary)), shape)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier
                    .size(44.dp)
                    .shadow(8.dp, RoundedCornerShape(12.dp))
                    .background(Brush.linearGradient(listOf(Color(0xFF60A5FA), Brand.Primary)), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text("A", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 22.sp)
            }
            Column(Modifier.padding(start = 12.dp)) {
                Text(title, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(subtitle, color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
