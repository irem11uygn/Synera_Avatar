package com.synera.avatar

import com.synera.avatar.util.EN
import com.synera.avatar.util.L
import com.synera.avatar.util.t
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

class I18nTest {
    @After
    fun turkish() = L.setForTest(L.TR)

    /** Kaynaktaki bütün t("...") anahtarları (birim testleri modül klasöründe çalışır). */
    private fun usedKeys(): Set<String> {
        val pattern = Regex("""\bt\("((?:\\.|[^"\\])*)"""")
        return File("src/main/java").walkTopDown()
            .filter { it.extension == "kt" && it.name != "I18nEn.kt" }
            .flatMap { file -> pattern.findAll(file.readText()).map { it.groupValues[1].replace("\\\"", "\"") } }
            .toSet()
    }

    @Test
    fun `ekrandaki her metnin Ingilizcesi var ve kullanilmayan ceviri yok`() {
        val used = usedKeys()
        assertEquals(emptyList<String>(), used.filter { it !in EN })
        assertEquals(emptyList<String>(), EN.keys.filter { it !in used })
    }

    @Test
    fun `yer tutucular iki dilde ayni`() {
        val names = { text: String -> Regex("""\{(\w+)\}""").findAll(text).map { it.groupValues[1] }.sorted().toList() }
        assertEquals(emptyList<String>(), EN.filter { (tr, en) -> names(tr) != names(en) }.keys.toList())
    }

    @Test
    fun `secili dile gore cevirir ve yer tutucuyu doldurur`() {
        assertEquals("Araç ARAC-01", t("Araç {code}", "code" to "ARAC-01"))
        L.setForTest(L.EN)
        assertEquals("Van ARAC-01", t("Araç {code}", "code" to "ARAC-01"))
        assertEquals("Sözlükte olmayan", t("Sözlükte olmayan"))
    }
}
