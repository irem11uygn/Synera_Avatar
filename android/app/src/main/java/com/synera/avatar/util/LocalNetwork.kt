package com.synera.avatar.util

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import java.net.URI

/**
 * Android 17'den (API 37) itibaren yerel ağ adreslerine erişim ACCESS_LOCAL_NETWORK çalışma anı
 * iznine bağlı; izin yoksa TCP bağlantısı zaman aşımına uğrar. İzin yalnız sunucu yerel ağdaysa istenir.
 */
object LocalNetwork {
    private const val ANDROID_17 = 37
    const val PERMISSION = Manifest.permission.ACCESS_LOCAL_NETWORK

    /** Adres yerel ağda mı: localhost, .local, özel IPv4 blokları, IPv6 döngü/yerel adresleri. */
    fun isLocalAddress(serverUrl: String): Boolean {
        val host = runCatching { URI(serverUrl.trim()).host }.getOrNull()?.lowercase()?.trim('[', ']') ?: return false
        if (host == "localhost" || host.endsWith(".local")) return true
        val octets = host.split('.')
        if (octets.size == 4 && octets.all { it.toIntOrNull() in 0..255 }) {
            val (a, b) = octets.take(2).map(String::toInt)
            return a == 10 || a == 127 || (a == 172 && b in 16..31) || (a == 192 && b == 168) || (a == 169 && b == 254)
        }
        return host == "::1" || host.startsWith("fe80:") || host.startsWith("fc") || host.startsWith("fd")
    }

    fun permissionRequired(context: Context, serverUrl: String): Boolean =
        Build.VERSION.SDK_INT >= ANDROID_17 &&
            isLocalAddress(serverUrl) &&
            context.checkSelfPermission(PERMISSION) != PackageManager.PERMISSION_GRANTED
}
