package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PoseTrackTest {
    @Test
    fun fillsGapFromNeighbors() {
        val good = skier(0, 0.9f)
        val bad = PoseFrame(80, emptyList(), 100, 100)
        val later = skier(160, 0.9f)
        val out = PoseTrack.fillLowScore(listOf(good, bad, later))
        assertEquals(1, out[1].poses.size)
        assertTrue(out[1].poses[0].keypoints[5].x in 20f..60f)
    }

    private fun skier(tMs: Long, vis: Float): PoseFrame {
        val kps = MutableList(17) { CocoKeypoint(40f, 40f, vis) }
        kps[5] = CocoKeypoint(30f, 50f, vis)
        kps[6] = CocoKeypoint(50f, 50f, vis)
        return PoseFrame(tMs, listOf(CocoPose(kps)), 100, 100, bbox = BBox(20f, 20f, 60f, 90f))
    }
}
