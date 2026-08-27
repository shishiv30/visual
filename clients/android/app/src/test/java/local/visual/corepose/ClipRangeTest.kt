package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ClipRangeTest {
    @Test
    fun seedAtHitsNearbyMark() {
        val seeds = listOf(
            SeedMark(0.0, NormBox(0.1f, 0.1f, 0.4f, 0.8f)),
            SeedMark(2000.0, NormBox(0.2f, 0.2f, 0.5f, 0.9f)),
        )
        val hit = ClipRange.seedAt(2010.0, seeds, halfMs = 33.0)
        assertEquals(0.2f, hit!!.box.x1, 0.001f)
        assertNull(ClipRange.seedAt(1000.0, seeds, 33.0))
    }

    @Test
    fun collectSeedsFallsBackToSeedBox() {
        val seeds = ClipRange.collectSeeds(
            emptyList(),
            NormBox(0.1f, 0.1f, 0.3f, 0.7f),
        )
        assertEquals(1, seeds.size)
        assertEquals(0.0, seeds[0].tMs, 0.0)
        assertEquals(0.1f, seeds[0].box.x1, 0.001f)
    }

    @Test
    fun collectSeedsPrefersTimedList() {
        val timed = listOf(SeedMark(500.0, NormBox(0.2f, 0.2f, 0.4f, 0.8f)))
        val seeds = ClipRange.collectSeeds(timed, NormBox(0.1f, 0.1f, 0.3f, 0.7f))
        assertEquals(1, seeds.size)
        assertEquals(500.0, seeds[0].tMs, 0.0)
    }

    @Test
    fun playRangeAndStrideMatchDesktop() {
        assertTrue(ClipRange.inPlayRange(2500.0, 1000.0, 4000.0))
        assertFalse(ClipRange.inPlayRange(50.0, 1000.0, 4000.0))
        assertEquals(2, ClipRange.FRAME_STRIDE)
        assertEquals(67L, ClipRange.strideMs(30.0))
        assertEquals(33.333, ClipRange.halfMs(30.0), 0.01)
    }

    @Test
    fun clampPlayheadStaysInsideTrimWindow() {
        assertEquals(10_000L, ClipRange.clampPlayheadMs(0L, 10_000L, 18_000L))
        assertEquals(17_999L, ClipRange.clampPlayheadMs(20_000L, 10_000L, 18_000L))
        assertEquals(14_000L, ClipRange.clampPlayheadMs(14_000L, 10_000L, 18_000L))
        assertEquals(10_000L, ClipRange.clampPlayheadMs(10_000L, 10_000L, 10_001L))
    }

    @Test
    fun tickerMustNotReseekWhileStartSeekIsPending() {
        assertFalse(ClipRange.shouldReseekToStart(0L, 10_000L, seekPending = true))
        assertTrue(ClipRange.shouldReseekToStart(0L, 10_000L, seekPending = false))
        assertFalse(ClipRange.shouldReseekToStart(10_000L, 10_000L, seekPending = false))
        assertFalse(ClipRange.shouldReseekToStart(10_100L, 10_000L, seekPending = false))
    }

    @Test
    fun pastPlayEndStopsAtOutPoint() {
        assertTrue(ClipRange.pastPlayEnd(18_000L, 18_000L))
        assertFalse(ClipRange.pastPlayEnd(17_999L, 18_000L))
    }
}
