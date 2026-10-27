package com.synera.avatar.util

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.edit

/**
 * Dil seçeneği (web arayüzüyle aynı yaklaşım): ekrandaki her metin Türkçe yazılır ve t() ile çevrilir;
 * İngilizce sözlükte karşılığı yoksa Türkçesi görünür. Dil Compose durumu olduğu için seçim değişince
 * ekran hemen yeniden çizilir. Seçim cihazda saklanır.
 */
object L {
    const val TR = "tr"
    const val EN = "en"

    var lang by mutableStateOf(TR)
        private set

    private var prefs: android.content.SharedPreferences? = null

    fun init(context: Context) {
        prefs = context.getSharedPreferences("ayarlar", Context.MODE_PRIVATE)
        lang = prefs?.getString(KEY, TR).takeIf { it == TR || it == EN } ?: TR
    }

    fun select(value: String) {
        if (value != TR && value != EN) return
        lang = value
        prefs?.edit { putString(KEY, value) }
    }

    /** Testlerde dil doğrudan seçilir (SharedPreferences olmadan). */
    internal fun setForTest(value: String) {
        lang = value
    }

    private const val KEY = "dil"
}

/** Türkçe metnin seçili dildeki karşılığı; {ad} yer tutucuları verilen değerlerle doldurulur. */
fun t(text: String, vararg params: Pair<String, Any?>): String {
    var result = if (L.lang == L.EN) EN[text] ?: text else text
    for ((name, value) in params) result = result.replace("{$name}", value?.toString().orEmpty())
    return result
}
