package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Test

class I18nTest {
    @Test
    fun interpolatesNamedAndFormatSpecs() {
        val out = I18n.interpolate(
            "In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)",
            mapOf("lo" to "1.2", "hi" to "8.0"),
        )
        assertEquals("In 1.2s → out 8.0s (logical, original file unchanged)", out)
    }

    @Test
    fun englishCatalogFallsBackToKey() {
        val json = """{"strings":{"Camera":{"zh":"拍摄"}}}"""
        val catalog = I18n.loadCatalogJson(json)
        assertEquals("拍摄", catalog["Camera"]?.get("zh"))
    }
}
