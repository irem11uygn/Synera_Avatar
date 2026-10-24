package com.synera.avatar

import com.synera.avatar.data.remote.ApiClient
import com.synera.avatar.data.remote.PullResponse
import com.synera.avatar.data.repo.toChanges
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PullMappingTest {
    // Sunucunun /api/v1/sync/pull yanıtı biçiminde örnek (docs/api.md §4.4); bilinmeyen alanlar yok sayılır.
    private val body = """
        {
          "next_since": 52,
          "products": [
            {"id": 5, "code": "NARIN-SUCUK", "name": "Narin Sucuk 1 kg", "base_unit": "ADET",
             "unit_weight_kg": "1.000", "sale_price": "24.90", "active": true, "yeni_alan": 1},
            {"id": 1, "code": "ET", "name": "Sucukluk et", "base_unit": "KG",
             "unit_weight_kg": null, "sale_price": null, "active": true}
          ],
          "customers": [{"id": 6, "code": "M-A", "name": "Market A", "contact_person": "Ayşe Demir",
                         "phone": "+90 000 000 03 01", "email": "market-a@example.com", "address": "İzmir"}],
          "lots": [{"id": 9, "lot_no": "SUC-2026-045", "product_id": 5, "expiry_date": "2026-12-20", "status": "BLOKE"}],
          "stock": [{"lot_id": 9, "qty": "85.000"}]
        }
    """.trimIndent()

    @Test
    fun `sunucu yaniti cihaz tablolarina kayipsiz cevrilir`() {
        val changes = ApiClient.json.decodeFromString<PullResponse>(body).toChanges()

        assertEquals(52L, changes.nextSince)
        val sucuk = changes.products.first { it.code == "NARIN-SUCUK" }
        assertEquals(2490L, sucuk.salePriceCents)
        assertEquals(1_000L, sucuk.unitWeightMilli)
        assertNull(changes.products.first { it.code == "ET" }.salePriceCents)
        assertEquals("Market A", changes.customers.single().name)
        assertEquals("BLOKE", changes.lots.single().status)
        assertEquals(85_000L, changes.stock.single().qtyMilli)
    }
}
