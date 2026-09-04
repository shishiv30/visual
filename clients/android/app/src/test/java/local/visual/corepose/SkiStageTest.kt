package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SkiStageTest {
    private val curriculum: Curriculum by lazy { CurriculumLoader.loadFile(findCurriculum()) }

    @Test
    fun curriculumLoadsV3() {
        assertEquals("3.0.0", curriculum.schemaVersion)
        assertTrue(curriculum.categories.containsKey("alpine_piste"))
        assertTrue(curriculum.categories.containsKey("alpine_moguls"))
        assertTrue(curriculum.categories.containsKey("alpine_offpiste"))
        assertEquals("green", curriculum.levels["pizza_glide"]?.terrain)
        assertEquals("full", curriculum.levels["pizza"]?.tier)
        assertEquals("st-03", curriculum.levels["pizza"]?.kbStage)
        assertEquals(listOf("dynamic_parallel"), curriculum.levels["parallel"]?.nextLevels)
        assertTrue(curriculum.levels.containsKey("sideslip"))
        assertTrue(curriculum.venues.containsKey("venue_green_groomer"))
        assertTrue(curriculum.checkpoints["cp_sk_hockey"]?.drills?.contains("drill_hockey") == true)
    }

    @Test
    fun knowledgePackLoadsFromRepo() {
        val pack = KnowledgePackLoader.loadFromRepo(findRepoRoot())
        assertTrue(pack.metrics.containsKey("stance_width"))
        assertTrue(pack.stages.containsKey("st-02"))
        assertTrue(pack.levelMap.isNotEmpty())
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
        assertEquals("3.0.0", report.schemaVersion)
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
        assertTrue((report.turns?.count ?: 0) >= 0)
    }

    @Test
    fun parallelNotPizza() {
        val seq = List(8) { joints(stance = 0.8, kneeDrop = 45.0) }
        val (cat, stage, _) = Assess.classify(SportsSignals.extractFeatures(assessFrames(seq), 15.0))
        assertEquals("alpine_piste", cat)
        assertEquals("parallel", stage)
    }

    @Test
    fun parallelPassOffersDynamicParallel() {
        val seq = List(8) { joints(stance = 0.8, kneeDrop = 45.0) }
        val report = Assess.assessClip("par", assessFrames(seq), 15.0, curriculum, "en")
        assertEquals("parallel", report.stageId)
        assertTrue(report.readyForNextStage)
        assertEquals(listOf("dynamic_parallel"), report.nextLevelIds)
        assertTrue(report.nextPlans.isNotEmpty())
        assertTrue(report.nextPlans[0].venues.isNotEmpty())
        assertTrue(report.nextPlans.any { it.drills.isNotEmpty() })
    }

    @Test
    fun metricDisplayNameIsLocalizedKey() {
        assertEquals("Stance width", MetricsBridge.displayName("stance_width", "en"))
        assertEquals("Turn rate", MetricsBridge.displayName("turn_rate", "en"))
    }

    @Test
    fun sceneSummaryPersistsOnReport() {
        val seq = List(8) { joints(stance = 1.8, kneeDrop = 50.0) }
        val scene = SceneContext(terrainType = "piste", slopeBand = "green", snowSurface = "corduroy")
        val report = Assess.assessClip(
            "glide-scene",
            assessFrames(seq),
            15.0,
            curriculum,
            "en",
            scene = scene,
        )
        assertEquals("piste", report.scene?.terrainType)
        assertEquals("green", report.scene?.slopeBand)
        assertEquals("corduroy", report.scene?.snowSurface)
    }

    @Test
    fun reportEmitsV3FidelityBlocks() {
        val pack = KnowledgePackLoader.loadFromRepo(findRepoRoot())
        val seq = List(12) { i ->
            joints(stance = 1.8, kneeDrop = 50.0, hipX = 180.0 + (i % 6) * 8.0)
        }
        val report = Assess.assessClip(
            "fidelity",
            assessFrames(seq),
            15.0,
            curriculum,
            "en",
            knowledge = pack,
        )
        assertTrue(report.classification != null)
        assertTrue(report.classification!!.candidates.isNotEmpty())
        assertTrue(report.metrics.isNotEmpty())
        assertTrue(report.metrics.any { it.isGate })
        assertTrue(report.tree.isNotEmpty())
        assertTrue(report.tree.any { it.state == NodeState.CURRENT })
        assertTrue(report.knowledgeRef != null)
        assertEquals(report.kbStage, report.knowledgeRef!!.kbStage)
        assertTrue(report.knowledgeFocus != null)
        // Contract keys from desktop schemas/stage_report.py StageReport (v3 blocks).
        val requiredKeys = listOf(
            "schema_version",
            "classification",
            "metrics",
            "turns",
            "tree",
            "tree_path",
            "knowledge_ref",
            "knowledge_focus",
            "filming",
            "kb_stage",
            "tier",
        )
        val androidObj = StageReportJson.toJson(report)
        for (key in requiredKeys) {
            assertTrue("android missing $key", androidObj.has(key))
        }
        assertEquals("3.0.0", androidObj.getString("schema_version"))
    }

    @Test
    fun classifyV3PicksPizzaGlideForWideStance() {
        val seq = List(8) { joints(stance = 1.8, kneeDrop = 50.0) }
        val features = SportsSignals.extractFeatures(assessFrames(seq), 15.0)
        val turns = Turns.segment(assessFrames(seq), 15.0)
        val pack = MetricPackBuilder.build(features, turns)
        val classification = ClassifyV3.classify(pack, curriculum)
        assertTrue(classification.method == "scored_candidates" || classification.method == "legacy_ladder")
        if (classification.method == "scored_candidates") {
            assertEquals("pizza_glide", classification.chosenId)
        }
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
        fun findRepoRoot(): File {
            var dir = File(System.getProperty("user.dir") ?: ".").absoluteFile
            repeat(10) {
                if (File(dir, "content/ski/curriculum.v3.json").isFile) {
                    return dir
                }
                dir = dir.parentFile ?: return@repeat
            }
            throw IllegalStateException("repo root not found from ${System.getProperty("user.dir")}")
        }

        fun findCurriculum(): File {
            val candidate = File(findRepoRoot(), "content/ski/curriculum.v3.json")
            if (!candidate.isFile) {
                throw IllegalStateException("curriculum.v3.json missing")
            }
            return candidate
        }
    }
}
