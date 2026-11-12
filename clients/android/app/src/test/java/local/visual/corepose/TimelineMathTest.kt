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

    @Test
    fun offStripDistanceIsZeroInsideBand() {
        assertEquals(0.0, TimelineMath.offStripPx(40.0, 0.0, 78.0), 0.0)
        assertEquals(22.0, TimelineMath.offStripPx(100.0, 0.0, 78.0), 0.0)
        assertEquals(30.0, TimelineMath.offStripPx(-30.0, 0.0, 78.0), 0.0)
    }

    @Test
    fun scrubRateSlowsWithDistanceFromStrip() {
        assertEquals(1.0, TimelineMath.scrubRate(0.0, 48.0), 0.0)
        assertEquals(1.0, TimelineMath.scrubRate(47.0, 48.0), 0.0)
        assertEquals(0.5, TimelineMath.scrubRate(48.0, 48.0), 0.0)
        assertEquals(0.25, TimelineMath.scrubRate(100.0, 48.0), 0.0)
        assertEquals(0.1, TimelineMath.scrubRate(150.0, 48.0), 0.0)
        assertEquals(0.1, TimelineMath.scrubRate(5000.0, 48.0), 0.0)
    }

    @Test
    fun dxToMsScalesWithZoomAndRate() {
        // 200 px viewport over 10 s: 1 px = 50 ms at zoom 1.
        assertEquals(500.0, TimelineMath.dxToMs(10.0, 10_000.0, 200, 1.0, 1.0), 1e-9)
        assertEquals(250.0, TimelineMath.dxToMs(10.0, 10_000.0, 200, 2.0, 1.0), 1e-9)
        assertEquals(50.0, TimelineMath.dxToMs(10.0, 10_000.0, 200, 1.0, 0.1), 1e-9)
        assertEquals(-500.0, TimelineMath.dxToMs(-10.0, 10_000.0, 200, 1.0, 1.0), 1e-9)
    }

    @Test
    fun edgeAutoScrollOnlyNearEdges() {
        assertEquals(0.0, TimelineMath.edgeAutoScrollPx(100.0, 200, 32.0, 14.0), 0.0)
        assertEquals(-7.0, TimelineMath.edgeAutoScrollPx(16.0, 200, 32.0, 14.0), 1e-9)
        assertEquals(-14.0, TimelineMath.edgeAutoScrollPx(-20.0, 200, 32.0, 14.0), 1e-9)
        assertEquals(7.0, TimelineMath.edgeAutoScrollPx(184.0, 200, 32.0, 14.0), 1e-9)
        assertEquals(14.0, TimelineMath.edgeAutoScrollPx(260.0, 200, 32.0, 14.0), 1e-9)
    }
}
