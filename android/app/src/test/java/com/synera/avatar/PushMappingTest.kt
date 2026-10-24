package com.synera.avatar

import com.synera.avatar.data.local.SaleEntity
import com.synera.avatar.data.local.SaleLineEntity
import com.synera.avatar.data.local.SyncState
import com.synera.avatar.data.remote.ApiClient
import com.synera.avatar.data.remote.PushRequest
import com.synera.avatar.data.remote.PushResponse
import com.synera.avatar.data.repo.toOutcome
import com.synera.avatar.data.repo.toPushRequest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.ZoneId

class PushMappingTest {
    private val sale = SaleEntity(
        clientUuid = "6f1c2a52-6a0e-4c8e-9d7c-1b0e9b1f0a01",
        customerId = 6,
        soldAtMillis = 1_793_085_120_000, // 2026-10-27 07:12 UTC = 10:12 Türkiye
        syncState = SyncState.PENDING,
    )
    private val lines = listOf(
        SaleLineEntity(sale.clientUuid, 2, 5, 9, "SUC-2026-046", 4_000, 2490, 9960),
        SaleLineEntity(sale.clientUuid, 1, 5, 8, "SUC-2026-045", 30_000, 2490, 74700),
    )

    @Test
    fun `bekleyen satis sunucu bicimine kayipsiz cevrilir`() {
        val request = toPushRequest("arac-01-pixel", 3, listOf(sale), lines, ZoneId.of("Europe/Istanbul"))
        val json = ApiClient.json.encodeToString(PushRequest.serializer(), request)
        assertEquals(
            """{"device_id":"arac-01-pixel","sales":[{"client_uuid":"6f1c2a52-6a0e-4c8e-9d7c-1b0e9b1f0a01",""" +
                """"customer_id":6,"warehouse_id":3,"sold_at":"2026-10-27T10:12+03:00","lines":[""" +
                """{"lot_no":"SUC-2026-045","qty":"30.000","unit_price":"24.90"},""" +
                """{"lot_no":"SUC-2026-046","qty":"4.000","unit_price":"24.90"}]}]}""",
            json,
        )
    }

    @Test
    fun `sunucu sonuclari cihaz durumuna cevrilir`() {
        val body = """
            {"results": [
              {"client_uuid": "a", "status": "ACCEPTED", "sale_no": "SAT-2026-0101", "warnings": [], "error": null},
              {"client_uuid": "b", "status": "DUPLICATE", "sale_no": "SAT-2026-0100", "warnings": [], "error": null},
              {"client_uuid": "c", "status": "ACCEPTED_WITH_WARNING", "sale_no": "SAT-2026-0102",
               "warnings": ["Geri çağrılmış lot satıldı (ET-2026-001)."], "error": null},
              {"client_uuid": "d", "status": "REJECTED", "sale_no": null, "warnings": [],
               "error": {"code": "INSUFFICIENT_STOCK", "message": "ET-2026-001 lotunda bu depoda yeterli stok yok."}}
            ]}
        """.trimIndent()
        val outcomes = ApiClient.json.decodeFromString<PushResponse>(body).results.map { it.toOutcome() }

        assertEquals(listOf(SyncState.SENT, SyncState.SENT, SyncState.SENT, SyncState.FAILED), outcomes.map { it.state })
        assertEquals("SAT-2026-0100", outcomes[1].saleNo) // tekrar gönderimde ilk numara korunur
        assertNull(outcomes[0].message)
        assertEquals("Geri çağrılmış lot satıldı (ET-2026-001).", outcomes[2].message)
        assertEquals("ET-2026-001 lotunda bu depoda yeterli stok yok.", outcomes[3].message)
    }
}
