package local.visual.corepose

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SportsSignalsTest {
    @Test
    fun frameIsReliableWhenAllCoreLandmarksAreConfident() {
        val frame = AssessFrame(tMs = 0.0, blaze33 = joints(coreConf = 0.9f))
        val pack = SportsSignals.extractFeatures(listOf(frame, frame.copy(tMs = 66.0)), 15.0)
        assertTrue(pack.series.all { it.reliable })
    }

    @Test
    fun frameIsUnreliableWhenOneCoreLandmarkIsWeak() {
        // Ankle above CONF_MIN (0.25, still contributes to the computed value)
        // but below EVIDENCE_CORE_CONF_MIN (0.5) -- exactly the snow-spray case
        // evidence selection needs to steer away from.
        val weakAnkle = joints(coreConf = 0.9f).toMutableList()
        weakAnkle[SportsSignals.L_ANKLE] = BlazeJoint(weakAnkle[SportsSignals.L_ANKLE].x, weakAnkle[SportsSignals.L_ANKLE].y, 0f, 0.4f)
        val frame = AssessFrame(tMs = 0.0, blaze33 = weakAnkle)
        val pack = SportsSignals.extractFeatures(listOf(frame, frame.copy(tMs = 66.0)), 15.0)
        assertFalse(pack.series.all { it.reliable })
    }

    private fun joints(coreConf: Float): List<BlazeJoint> {
        val pts = MutableList(33) { BlazeJoint(20f, 20f, 0f, 0.9f) }
        val core = intArrayOf(
            SportsSignals.L_SHOULDER, SportsSignals.R_SHOULDER,
            SportsSignals.L_HIP, SportsSignals.R_HIP,
            SportsSignals.L_KNEE, SportsSignals.R_KNEE,
            SportsSignals.L_ANKLE, SportsSignals.R_ANKLE,
        )
        var x = 0f
        for (idx in core) {
            pts[idx] = BlazeJoint(x, 40f + idx, 0f, coreConf)
            x += 10f
        }
        return pts
    }
}
