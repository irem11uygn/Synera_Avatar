package com.synera.avatar.ui.theme

import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathBuilder
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Color

/** Alt menü simgeleri: ek simge paketi yerine basit çizgi çizimleri (24 × 24). */
object AppIcons {
    private fun icon(name: String, block: PathBuilder.() -> Unit): ImageVector =
        ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f)
            .path(
                stroke = SolidColor(Color.Black),
                strokeLineWidth = 2f,
                strokeLineCap = StrokeCap.Round,
                strokeLineJoin = StrokeJoin.Round,
                pathBuilder = block,
            )
            .build()

    /** Alışveriş sepeti. */
    val Sale = icon("satis") {
        moveTo(3f, 4f); lineTo(5.5f, 4f); lineTo(7.5f, 15f); lineTo(18f, 15f); lineTo(20f, 7f); lineTo(6.2f, 7f)
        moveTo(9f, 19.5f); lineTo(9.01f, 19.5f)
        moveTo(17f, 19.5f); lineTo(17.01f, 19.5f)
    }

    /** Koli. */
    val Stock = icon("stok") {
        moveTo(3f, 7.5f); lineTo(12f, 3f); lineTo(21f, 7.5f); lineTo(21f, 16.5f); lineTo(12f, 21f); lineTo(3f, 16.5f); close()
        moveTo(3f, 7.5f); lineTo(12f, 12f); lineTo(21f, 7.5f)
        moveTo(12f, 12f); lineTo(12f, 21f)
    }

    /** Liste. */
    val History = icon("gecmis") {
        moveTo(8f, 6f); lineTo(20f, 6f)
        moveTo(8f, 12f); lineTo(20f, 12f)
        moveTo(8f, 18f); lineTo(20f, 18f)
        moveTo(4f, 6f); lineTo(4.01f, 6f)
        moveTo(4f, 12f); lineTo(4.01f, 12f)
        moveTo(4f, 18f); lineTo(4.01f, 18f)
    }

    /** Hesap makinesi. */
    val DayEnd = icon("gunsonu") {
        moveTo(6f, 3f); lineTo(18f, 3f); lineTo(18f, 21f); lineTo(6f, 21f); close()
        moveTo(9f, 7f); lineTo(15f, 7f)
        moveTo(9f, 12f); lineTo(9.01f, 12f)
        moveTo(12f, 12f); lineTo(12.01f, 12f)
        moveTo(15f, 12f); lineTo(15.01f, 12f)
        moveTo(9f, 16f); lineTo(9.01f, 16f)
        moveTo(12f, 16f); lineTo(12.01f, 16f)
        moveTo(15f, 16f); lineTo(15.01f, 16f)
    }

    /** Yenile (eşitle). */
    val Sync = icon("esitle") {
        moveTo(20f, 11f); arcTo(8f, 8f, 0f, false, false, 5.5f, 7f)
        moveTo(4f, 13f); arcTo(8f, 8f, 0f, false, false, 18.5f, 17f)
        moveTo(5.5f, 3f); lineTo(5.5f, 7f); lineTo(9.5f, 7f)
        moveTo(18.5f, 21f); lineTo(18.5f, 17f); lineTo(14.5f, 17f)
    }

    /** Geri oku (üst çubuk). */
    val Back = icon("geri") {
        moveTo(15f, 5f); lineTo(8f, 12f); lineTo(15f, 19f)
    }

    /** Üç nokta (menü). */
    val More = icon("menu") {
        moveTo(12f, 5f); lineTo(12.01f, 5f)
        moveTo(12f, 12f); lineTo(12.01f, 12f)
        moveTo(12f, 19f); lineTo(12.01f, 19f)
    }
}
