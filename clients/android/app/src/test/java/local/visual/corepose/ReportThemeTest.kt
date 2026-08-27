package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class ReportThemeTest {
    @Test
    fun spacingTokensMatchDesktop() {
        assertEquals(36, ReportTheme.SPACE_CHAPTER)
        assertEquals(24, ReportTheme.SPACE_PANEL)
        assertEquals(16, ReportTheme.SPACE_TEXT)
        assertEquals(12, ReportTheme.PAGE_INSET)
        assertEquals(8, ReportTheme.REPORT_INSET)
    }

    @Test
    fun zeroAndMissingScoresUseOpaqueGray() {
        assertEquals(ReportTheme.TITLE, ReportTheme.scorePurple(null))
        assertEquals(ReportTheme.TITLE, ReportTheme.scorePurple(0.0))
        assertEquals(0xFF9E9E9E.toInt(), ReportTheme.TITLE)
        assertEquals(0xFF2A3544.toInt(), ReportTheme.RING_TRACK)
    }

    @Test
    fun positiveScoreUsesPurpleRamp() {
        assertNotEquals(ReportTheme.TITLE, ReportTheme.scorePurple(1.0))
        assertNotEquals(ReportTheme.TITLE, ReportTheme.scorePurple(100.0))
    }

    @Test
    fun blackTerrainDiamondsUseWhiteStroke() {
        assertEquals(0xFF000000.toInt(), ReportTheme.TERRAIN_BLACK)
        assertEquals(listOf(ReportTheme.TERRAIN_BLACK), ReportTheme.terrainDiamondColors("black"))
        assertEquals(
            listOf(ReportTheme.TERRAIN_BLACK, ReportTheme.TERRAIN_BLACK),
            ReportTheme.terrainDiamondColors("double_black"),
        )
    }
}
