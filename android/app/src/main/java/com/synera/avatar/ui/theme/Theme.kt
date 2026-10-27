package com.synera.avatar.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** Web arayüzüyle aynı marka renkleri; telefonun duvar kâğıdı rengine göre değişmez. */
object Brand {
    val Primary = Color(0xFF2563EB)
    val Danger = Color(0xFFDC2626)
    val Success = Color(0xFF16A34A)
    val Warning = Color(0xFFD97706)
}

private val light = lightColorScheme(
    primary = Brand.Primary,
    secondary = Color(0xFF475569),
    secondaryContainer = Color(0xFFDBEAFE),
    onSecondaryContainer = Color(0xFF0B1D3A),
    background = Color(0xFFEEF2F8),
    surface = Color(0xFFFFFFFF),
    error = Brand.Danger,
)

private val dark = darkColorScheme(
    primary = Color(0xFF60A5FA),
    secondaryContainer = Color(0xFF1E3A8A),
    background = Color(0xFF0B1220),
    surface = Color(0xFF111A2E),
    error = Color(0xFFF87171),
)

@Composable
fun AvatarTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) dark else light, content = content)
}
