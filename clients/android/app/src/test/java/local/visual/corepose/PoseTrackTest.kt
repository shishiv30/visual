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

    @Test
    fun stabilizeWeakJointsInterpolatesSingleWeakAnkle() {
        // Ankle (27) is weak for two mid frames while every other joint (and
        // the frame overall) stays well-tracked -- the snow-spray/occlusion
        // case fillLowScore never catches because the pose's overall score
        // never drops.
        val frames = listOf(
            blazeFrame(0, ankleX = 10f, ankleConf = 0.9f),
            blazeFrame(100, ankleX = 10f, ankleConf = 0.1f),
            blazeFrame(200, ankleX = 10f, ankleConf = 0.1f),
            blazeFrame(300, ankleX = 40f, ankleConf = 0.9f),
        )
        val out = PoseTrack.stabilizeWeakJoints(frames)
        // Interpolated between x=10 (t=0) and x=40 (t=300).
        assertEquals(20f, out[1].blaze33[27].x, 0.01f)
        assertEquals(30f, out[2].blaze33[27].x, 0.01f)
        assertTrue(out[1].blaze33[27].confidence > PoseTrack.JOINT_CONF_MIN.toFloat())
        // Every other joint (e.g. the other ankle) is untouched.
        assertEquals(0.9f, out[1].blaze33[28].confidence, 0.001f)
    }

    @Test
    fun stabilizeWeakJointsHoldsFromOneSidedAnchor() {
        // No right-side anchor within HOLD_MS -- the run should hold the left
        // anchor's position, discounted, rather than interpolate to nothing.
        val frames = listOf(
            blazeFrame(0, ankleX = 10f, ankleConf = 0.9f),
            blazeFrame(100, ankleX = 999f, ankleConf = 0.1f),
        )
        val out = PoseTrack.stabilizeWeakJoints(frames)
        assertEquals(10f, out[1].blaze33[27].x, 0.01f)
        assertEquals(0.9f * PoseTrack.INTERP_CONF, out[1].blaze33[27].confidence, 0.001f)
    }

    @Test
    fun stabilizeWeakJointsLeavesLongGapAlone() {
        // Gap wider than MAX_GAP_MS on both sides: nothing to interpolate
        // from safely, so the raw (noisy) sample is left as-is.
        val frames = listOf(
            blazeFrame(0, ankleX = 10f, ankleConf = 0.9f),
            blazeFrame(1000, ankleX = 999f, ankleConf = 0.1f),
            blazeFrame(2000, ankleX = 40f, ankleConf = 0.9f),
        )
        val out = PoseTrack.stabilizeWeakJoints(frames)
        assertEquals(999f, out[1].blaze33[27].x, 0.01f)
        assertEquals(0.1f, out[1].blaze33[27].confidence, 0.001f)
    }

    private fun blazeFrame(tMs: Long, ankleX: Float, ankleConf: Float): PoseFrame {
        val joints = MutableList(33) { BlazeJoint(20f, 20f, 0f, 0.9f) }
        joints[27] = BlazeJoint(ankleX, 20f, 0f, ankleConf)
        joints[28] = BlazeJoint(50f, 20f, 0f, 0.9f)
        return PoseFrame(tMs, emptyList(), 100, 100, blaze33 = joints)
    }
}
