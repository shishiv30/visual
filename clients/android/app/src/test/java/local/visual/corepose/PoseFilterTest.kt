package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PoseFilterTest {
    @Test
    fun bboxIouIsOneWhenEqual() {
        val box = BBox(10f, 10f, 50f, 80f)
        assertEquals(1.0, PoseFilter.bboxIou(box, box), 0.001)
        assertEquals(0.0, PoseFilter.bboxIou(box, BBox(100f, 100f, 110f, 120f)), 0.001)
    }

    @Test
    fun pickPrimaryPrefersOverlapWithPreviousBox() {
        val left = skier(BBox(20f, 40f, 80f, 200f), score = 0.4f)
        val right = skier(BBox(400f, 40f, 460f, 200f), score = 0.9f)
        val mapped = MappedPeople(
            poses = listOf(left, right),
            blazePeople = listOf(emptyList(), emptyList()),
            bboxes = listOf(BBox(20f, 40f, 80f, 200f), BBox(400f, 40f, 460f, 200f)),
        )
        val picked = PoseFilter.pickPrimary(mapped, BBox(18f, 38f, 82f, 202f))
        assertEquals(1, picked.poses.size)
        assertEquals(20f, picked.bboxes[0].x1, 0.1f)
    }

    @Test
    fun plausibleSkierPasses() {
        val pose = skier(BBox(200f, 80f, 300f, 320f))
        assertTrue(PoseFilter.isPlausible(pose, BBox(200f, 80f, 300f, 320f), 640, 480))
    }

    @Test
    fun extremeAspectFails() {
        val pose = skier(BBox(200f, 10f, 220f, 400f))
        assertFalse(PoseFilter.isPlausible(pose, BBox(200f, 10f, 220f, 400f), 640, 480))
    }

    private fun skier(box: BBox, score: Float = 0.8f): CocoPose {
        val cx = (box.x1 + box.x2) / 2f
        val kps = MutableList(17) { CocoKeypoint(cx, box.y1, score) }
        kps[0] = CocoKeypoint(cx, box.y1 + 10f, 0.9f)
        kps[1] = CocoKeypoint(cx - 4f, box.y1 + 8f, 0.9f)
        kps[2] = CocoKeypoint(cx + 4f, box.y1 + 8f, 0.9f)
        val half = (box.x2 - box.x1) * 0.35f
        kps[5] = CocoKeypoint(cx - half, box.y1 + 40f, 0.9f)
        kps[6] = CocoKeypoint(cx + half, box.y1 + 40f, 0.9f)
        kps[11] = CocoKeypoint(cx - half * 0.8f, box.y1 + 110f, 0.9f)
        kps[12] = CocoKeypoint(cx + half * 0.8f, box.y1 + 110f, 0.9f)
        return CocoPose(kps)
    }
}
