package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SkiStageTest {
    private val curriculum: Curriculum by lazy { CurriculumLoader.loadFile(findCurriculum()) }

    @Test
    fun curriculumLoads() {
        assertEquals("2.1.0", curriculum.schemaVersion)
        assertTrue(curriculum.categories.containsKey("alpine_piste"))
        assertTrue(curriculum.categories.containsKey("alpine_moguls"))
        assertEquals("green", curriculum.levels["pizza_glide"]?.terrain)
        assertEquals(listOf("skid_short", "carve_long"), curriculum.levels["parallel"]?.nextLevels)
        assertTrue(curriculum.venues.containsKey("venue_green_groomer"))
        assertTrue(curriculum.checkpoints["cp_sk_hockey"]?.drills?.contains("drill_hockey") == true)
    }

    @Test
    fun pizzaGlideFromWideStance() {
        val seq = List(8) { joints(stance = 1.8, kneeDrop = 50.0) }
        val pack = SportsSignals.extractFeatures(assessFrames(seq), 15.0)
        val (cat, stage, conf) = Assess.classify(pack)
        assertEquals("alpine_piste", cat)
        assertEquals("pizza_glide", stage)
        assertTrue(conf >= 0.35)
        val report = Assess.assessClip("glide", assessFrames(seq), 15.0, curriculum, "en")
        assertEquals("pizza_glide", report.stageId)
        assertTrue(report.stageFocus.isNotBlank())
        assertTrue(report.sessionPlan.isNotEmpty())
        assertTrue(report.score0100 in 0.0..100.0)
        assertTrue(report.keypoints.any { it.id == "cp_pg_stance" })
        val duration = 8 * 66.0
        for (item in report.keypoints) {
            val evidence = item.evidenceMs ?: continue
            assertTrue(evidence in 0.0..duration)
        }
        assertEquals("green", report.terrainId)
        assertTrue(report.scoreSeries.isNotEmpty())
        assertTrue(report.scoreSeries[0].tMs >= 0.0)
        assertTrue(report.scoreSeries[0].score in 0.0..100.0)
    }

    @Test
    fun pizzaTurnsFromWideStanceWithPath() {
        val seq = List(12) { i ->
            joints(stance = 1.8, kneeDrop = 50.0, hipX = 180.0 + (i % 6) * 8.0)
        }
        val (cat, stage, _) = Assess.classify(SportsSignals.extractFeatures(assessFrames(seq), 15.0))
        assertEquals("alpine_piste", cat)
        assertEquals("pizza", stage)
        val report = Assess.assessClip("pizza", assessFrames(seq), 15.0, curriculum, "en")
        assertEquals("pizza", report.stageId)
        assertTrue(report.keypoints.any { it.id == "cp_pz_stance" })
    }

    @Test
    fun parallelNotPizza() {
        val seq = List(8) { joints(stance = 0.8, kneeDrop = 45.0) }
        val (cat, stage, _) = Assess.classify(SportsSignals.extractFeatures(assessFrames(seq), 15.0))
        assertEquals("alpine_piste", cat)
        assertEquals("parallel", stage)
    }

    @Test
    fun parallelPassOffersSkidAndCarve() {
        val seq = List(8) { joints(stance = 0.8, kneeDrop = 45.0) }
        val report = Assess.assessClip("par", assessFrames(seq), 15.0, curriculum, "en")
        assertEquals("parallel", report.stageId)
        assertTrue(report.readyForNextStage)
        assertEquals(listOf("skid_short", "carve_long"), report.nextLevelIds)
        assertTrue(report.nextPlans.isNotEmpty())
        assertTrue(report.nextPlans[0].venues.isNotEmpty())
        assertTrue(report.nextPlans.any { it.drills.isNotEmpty() })
    }

    private fun assessFrames(seq: List<List<BlazeJoint>>): List<AssessFrame> {
        return seq.mapIndexed { i, joints ->
            AssessFrame(tMs = i * 66.0, blaze33 = joints)
        }
    }

    private fun joints(
        hipW: Double = 40.0,
        stance: Double = 1.5,
        kneeDrop: Double = 40.0,
        kneeIn: Double = 0.0,
        lean: Double = 0.0,
        hipX: Double = 200.0,
    ): List<BlazeJoint> {
        val mid = hipX
        val lh = mid - hipW / 2
        val rh = mid + hipW / 2
        val ankleSpan = hipW * stance
        val la = mid - ankleSpan / 2
        val ra = mid + ankleSpan / 2
        val ls = lh + lean * hipW
        val rs = rh + lean * hipW
        val pts = Array(33) { 0.0 to 0.0 }
        pts[0] = mid to 40.0
        pts[11] = ls to 80.0
        pts[12] = rs to 80.0
        pts[15] = ls to 140.0
        pts[16] = rs to 140.0
        pts[23] = lh to 160.0
        pts[24] = rh to 160.0
        pts[25] = (lh + kneeIn) to (160.0 + kneeDrop)
        pts[26] = (rh - kneeIn) to (160.0 + kneeDrop)
        pts[27] = la to 280.0
        pts[28] = ra to 280.0
        pts[31] = la to 300.0
        pts[32] = ra to 300.0
        return pts.map { (x, y) ->
            BlazeJoint(x.toFloat(), y.toFloat(), 0f, 0.95f)
        }
    }

    companion object {
        fun findCurriculum(): File {
            var dir = File(System.getProperty("user.dir") ?: ".").absoluteFile
            repeat(10) {
                val candidate = File(dir, "content/ski/curriculum.v2.json")
                if (candidate.isFile) {
                    return candidate
                }
                dir = dir.parentFile ?: return@repeat
            }
            throw IllegalStateException("curriculum.v2.json not found from ${System.getProperty("user.dir")}")
        }
    }
}
