package com.synera.avatar

import com.synera.avatar.util.LocalNetwork
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalNetworkTest {
    @Test
    fun `emulator ve yerel ag adresleri yerel sayilir`() {
        listOf(
            "http://10.0.2.2:8000",
            "http://192.168.1.20:8000",
            "http://172.20.0.5:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://sunucu.local:8000",
            "http://[::1]:8000",
        ).forEach { assertTrue(it, LocalNetwork.isLocalAddress(it)) }
    }

    @Test
    fun `internetteki sunucu yerel sayilmaz`() {
        listOf(
            "https://api.example.com",
            "http://8.8.8.8",
            "http://172.32.0.1:8000",
            "bozuk adres",
        ).forEach { assertFalse(it, LocalNetwork.isLocalAddress(it)) }
    }
}
