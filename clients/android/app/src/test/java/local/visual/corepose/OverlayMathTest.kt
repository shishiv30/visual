package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OverlayMathTest {
    @Test
    fun fillCenterIdentityWhenSizesMatch() {
        val (x, y) = OverlayMath.mapFillCenter(10f, 20f, 100, 200, 100, 200)
        assertEquals(10f, x, 0.01f)
        assertEquals(20f, y, 0.01f)
    }

    @Test
    fun fillCenterScalesToCover() {
        val (x, y) = OverlayMath.mapFillCenter(50f, 50f, 100, 100, 200, 100)
        assertEquals(100f, x, 0.01f)
        assertEquals(50f, y, 0.01f)
    }

    @Test
    fun hidesLowVisibilityBones() {
        val kps = (0 until 17).map { i ->
            CocoKeypoint(i.toFloat(), 0f, if (i == 0 || i == 1) 0.9f else 0.1f)
        }
        val segs = OverlayMath.visibleSegments(CocoPose(kps), 100, 100, 100, 100)
        assertEquals(1, segs.size)
        assertEquals(0f, segs[0].x1, 0.01f)
        assertEquals(1f, segs[0].x2, 0.01f)
    }

    @Test
    fun unmapReversesFillCenter() {
        val (x, y) = OverlayMath.mapFillCenter(50f, 50f, 100, 100, 200, 100)
        val (ux, uy) = OverlayMath.unmapFillCenter(x, y, 100, 100, 200, 100)
        assertEquals(50f, ux, 0.01f)
        assertEquals(50f, uy, 0.01f)
    }

    @Test
    fun containLetterboxesWideView() {
        val box = OverlayMath.contain(100, 100, 200, 100)
        assertEquals(1f, box.scale, 0.01f)
        assertEquals(50f, box.dx, 0.01f)
        assertEquals(0f, box.dy, 0.01f)
        val (x, y) = OverlayMath.mapContain(50f, 50f, 100, 100, 200, 100)
        assertEquals(100f, x, 0.01f)
        assertEquals(50f, y, 0.01f)
        val (ux, uy) = OverlayMath.unmapContain(x, y, 100, 100, 200, 100)
        assertEquals(50f, ux, 0.01f)
        assertEquals(50f, uy, 0.01f)
    }

    @Test
    fun emptyWhenTooFewKeypoints() {
        val pose = CocoPose(listOf(CocoKeypoint(0f, 0f, 1f)))
        assertTrue(OverlayMath.visibleSegments(pose, 10, 10, 10, 10).isEmpty())
    }

    @Test
    fun containSegmentsLetterboxWideView() {
        val kps = (0 until 17).map { CocoKeypoint(50f, 50f, 1f) }
        val segs = OverlayMath.visibleSegments(CocoPose(kps), 100, 100, 200, 100, letterbox = true)
        assertTrue(segs.isNotEmpty())
        assertEquals(100f, segs[0].x1, 0.01f)
        assertEquals(50f, segs[0].y1, 0.01f)
    }

    @Test
    fun bboxFromVisibleJoints() {
        val kps = (0 until 17).map { i ->
            CocoKeypoint(i.toFloat(), i.toFloat() + 2f, 1f)
        }
        val box = OverlayMath.bboxFromPose(CocoPose(kps))
        assertEquals(0f, box!!.x1, 0.01f)
        assertEquals(2f, box.y1, 0.01f)
        assertEquals(16f, box.x2, 0.01f)
        assertEquals(18f, box.y2, 0.01f)
    }
}
