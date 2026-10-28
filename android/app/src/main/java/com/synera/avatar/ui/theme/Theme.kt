package com.synera.avatar.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** Web arayüzüyle aynı turkuaz kimlik; anlam taşıyan renk (kırmızı/turuncu/yeşil) yalnız durumlarda. */
object Brand {
    val Primary = Color(0xFF0D9488)
    val PrimaryDeep = Color(0xFF0F766E)
    val PrimarySoft = Color(0xFFDFF5F1)
    val Danger = Color(0xFFC62828)
    val DangerSoft = Color(0xFFFDECEC)
    val Success = Color(0xFF2E7D32)
    val SuccessSoft = Color(0xFFEAF5EB)
    val Warning = Color(0xFFB45309)
    val WarningSoft = Color(0xFFFDF3E6)
    val Border = Color(0xFFE3E6EA)
    val Muted = Color(0xFF6B7280)
}

private val light = lightColorScheme(
    primary = Brand.Primary,
    onPrimary = Color.White,
    primaryContainer = Brand.PrimarySoft,
    onPrimaryContainer = Brand.PrimaryDeep,
    secondaryContainer = Brand.PrimarySoft,
    onSecondaryContainer = Brand.PrimaryDeep,
    background = Color(0xFFEEF6F5),
    surface = Color.White,
    surfaceContainer = Color.White,
    onSurface = Color(0xFF1F2328),
    onSurfaceVariant = Color(0xFF4B5563),
    outline = Color(0xFFCFD4DA),
    outlineVariant = Brand.Border,
    error = Brand.Danger,
)

private val dark = darkColorScheme(
    primary = Color(0xFF5EC4B6),
    onPrimary = Color(0xFF003731),
    primaryContainer = Color(0xFF0B3B37),
    secondaryContainer = Color(0xFF0B3B37),
    background = Color(0xFF111418),
    surface = Color(0xFF1A1E23),
    surfaceContainer = Color(0xFF1A1E23),
    outlineVariant = Color(0xFF2C3238),
    error = Color(0xFFF2B8B5),
)

// Sahada, güneş altında okunabilsin: bir kademe büyük yazı.
private val typography = Typography(
    titleLarge = TextStyle(fontSize = 22.sp, fontWeight = FontWeight.SemiBold, lineHeight = 28.sp),
    titleMedium = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.SemiBold, lineHeight = 24.sp),
    titleSmall = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontSize = 17.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 15.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontSize = 14.sp, lineHeight = 19.sp),
    labelLarge = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium),
)

@Composable
fun AvatarTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) dark else light, typography = typography, content = content)
}
