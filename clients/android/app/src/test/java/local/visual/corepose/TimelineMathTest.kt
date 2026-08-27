package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TimelineMathTest {
    @Test
    fun clampsZoom() {
        assertEquals(1.0, TimelineMath.clampZoom(0.2), 0.0)
        assertEquals(5.0, TimelineMath.clampZoom(9.0), 0.0)
        assertEquals(2.5, TimelineMath.clampZoom(2.5), 0.0)
    }

    @Test
    fun mapsTimeToXAndBack() {
        val x = TimelineMath.msToX(500.0, 1000.0, 200, 1.0, 0.0)
        assertEquals(100.0, x, 0.001)
        val t = TimelineMath.xToMs(100.0, 1000.0, 200, 1.0, 0.0)
        assertEquals(500.0, t, 0.001)
    }

    @Test
    fun clampRangeEnforcesMinimum() {
        val (start, end) = TimelineMath.clampRange(0, 50, 10_000)
        assertEquals(0, start)
        assertEquals(200, end)
    }

    @Test
    fun zoomKeepsAnchorTime() {
        val tBefore = TimelineMath.xToMs(80.0, 10_000.0, 200, 1.0, 0.0)
        val (zoom, scroll) = TimelineMath.zoomKeepingMs(2.0, 80.0, 10_000.0, 200, 1.0, 0.0)
        val tAfter = TimelineMath.xToMs(80.0, 10_000.0, 200, zoom, scroll)
        assertEquals(2.0, zoom, 0.0)
        assertEquals(tBefore, tAfter, 0.001)
    }

    @Test
    fun formatRulerTime() {
        assertEquals("0:05", TimelineMath.formatRulerTime(5300.0, false))
        assertEquals("0:05.3", TimelineMath.formatRulerTime(5300.0, true))
        assertEquals("1:07", TimelineMath.formatRulerTime(67_000.0, false))
    }

    @Test
    fun nearestKeyframe() {
        val hit = TimelineMath.nearestKeyframeMs(50.0, listOf(0, 500, 900), 1000.0, 100, 1.0, 0.0)
        assertEquals(500, hit)
        assertNull(TimelineMath.nearestKeyframeMs(10.0, listOf(500), 1000.0, 100, 1.0, 0.0))
    }
}
