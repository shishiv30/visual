package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PoseTimelineTest {
    private fun frame(t: Long) = PoseFrame(t, emptyList(), 10, 10)

    @Test
    fun emptyTimeline() {
        assertNull(PoseTimeline.nearest(emptyList(), 0))
    }

    @Test
    fun exactMatch() {
        val frames = listOf(frame(0), frame(100), frame(200))
        assertEquals(100L, PoseTimeline.nearest(frames, 100)?.tMs)
    }

    @Test
    fun picksCloserNeighbor() {
        val frames = listOf(frame(0), frame(100), frame(200))
        assertEquals(100L, PoseTimeline.nearest(frames, 130)?.tMs)
        assertEquals(200L, PoseTimeline.nearest(frames, 180)?.tMs)
    }
}
