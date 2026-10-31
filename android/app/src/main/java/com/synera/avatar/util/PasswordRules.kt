package com.synera.avatar.util

/**
 * Sunucudaki şifre kuralının telefondaki eşi (backend/app/services/auth.py): en az 8 karakter, harf ve
 * rakam birlikte, eskisiyle aynı değil. Telefonda denetlemek gereksiz istek ve bekleme olmasın diye;
 * son söz yine sunucunundur.
 */
object PasswordRules {
    const val MIN_LENGTH = 8

    /** Sorun yoksa null; varsa kullanıcıya gösterilecek metin (seçili dilde). */
    fun problem(current: String, new: String, repeat: String): String? = when {
        current.isEmpty() -> t("Mevcut şifrenizi yazın.")
        new.length < MIN_LENGTH -> t("Yeni şifre en az {n} karakter olmalı.", "n" to MIN_LENGTH)
        new.all { it.isDigit() } || new.all { it.isLetter() } -> t("Yeni şifrede hem harf hem rakam olmalı.")
        new == current -> t("Yeni şifre eskisiyle aynı olamaz.")
        new != repeat -> t("Yeni şifre ile tekrarı aynı değil.")
        else -> null
    }
}
