package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayerExportTest {
    @Test
    fun downloadNameSanitizesAndAddsJpg() {
        assertEquals("overlay.jpg", PlayerExport.downloadFileName(null, null))
        assertEquals("clip-1.jpg", PlayerExport.downloadFileName("clip-1", "abc"))
        assertEquals("a_b.jpg", PlayerExport.downloadFileName("a/b", "abc"))
        assertEquals("ready.jpg", PlayerExport.downloadFileName("ready.jpg", "abc"))
    }

    @Test
    fun shareTargetsMatchDesktopUrls() {
        val byName = PlayerExport.SHARE_TARGETS.toMap()
        assertEquals("https://www.youtube.com/upload", byName["YouTube"])
        assertEquals("https://www.tiktok.com/upload", byName["TikTok"])
        assertTrue(byName["X"]!!.contains("{text}"))
        assertEquals(
            "https://twitter.com/intent/tweet?text=Visual%20Pose",
            PlayerExport.shareUrl(byName["X"]!!, "Visual Pose"),
        )
    }
}
