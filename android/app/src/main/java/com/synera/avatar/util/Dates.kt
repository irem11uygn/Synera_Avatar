package com.synera.avatar.util

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/** Tarih biçimleri seçili dile göre: Türkçe 28.10.2026, İngilizce 28/10/2026. */
object Dates {
    private fun datePattern() = if (L.lang == L.EN) "dd/MM/yyyy" else "dd.MM.yyyy"

    fun date(iso: String?): String = iso?.let { LocalDate.parse(it).format(DateTimeFormatter.ofPattern(datePattern())) } ?: "—"

    fun dateTime(millis: Long, zone: ZoneId = ZoneId.systemDefault()): String =
        DateTimeFormatter.ofPattern(datePattern() + " HH:mm").format(Instant.ofEpochMilli(millis).atZone(zone))

    fun time(millis: Long, zone: ZoneId = ZoneId.systemDefault()): String =
        DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli(millis).atZone(zone))

    /** Son kullanma tarihine kalan gün; eksi: geçmiş. */
    fun daysLeft(expiryIso: String, today: LocalDate): Long = ChronoUnit.DAYS.between(today, LocalDate.parse(expiryIso))
}

/** Son kullanma durumu metni ve tonu için: null = tarih yok ya da uzak. */
fun expiryLabel(expiryIso: String?, today: LocalDate, warnDays: Long = 3): Pair<String, Boolean>? {
    val days = expiryIso?.let { Dates.daysLeft(it, today) } ?: return null
    return when {
        days < 0 -> t("Süresi geçti") to true
        days == 0L -> t("Bugün son gün") to true
        days <= warnDays -> t("{n} gün kaldı", "n" to days) to false
        else -> null
    }
}
