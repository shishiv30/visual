package local.visual.corepose

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

enum class KeypointStatus {
    PASS,
    FAIL,
    UNKNOWN,
}

enum class MetricState(val wire: String) {
    OK("ok"),
    UNKNOWN("unknown"),
    NOT_APPLICABLE("not_applicable"),
    ;

    companion object {
        fun fromWire(raw: String): MetricState =
            entries.firstOrNull { it.wire == raw } ?: UNKNOWN
    }
}

enum class Rubric(val wire: String) {
    NOT_YET("not_yet"),
    PASS("pass"),
    STRONG("strong"),
    NOT_RATED("not_rated"),
    ;

    companion object {
        fun fromWire(raw: String): Rubric =
            entries.firstOrNull { it.wire == raw } ?: NOT_RATED
    }
}

enum class NodeState(val wire: String) {
    COMPLETED("completed"),
    CURRENT("current"),
    INFERRED("inferred"),
    AVAILABLE("available"),
    LOCKED("locked"),
    NOT_APPLICABLE("not_applicable"),
    ;

    companion object {
        fun fromWire(raw: String): NodeState =
            entries.firstOrNull { it.wire == raw } ?: LOCKED
    }
}

data class DrillPayload(
    val id: String = "",
    val title: String = "",
    val name: String = "",
    val desc: String = "",
    val steps: List<String> = emptyList(),
    val training: List<String> = emptyList(),
    val venues: List<VenuePayload> = emptyList(),
)

data class VenuePayload(
    val id: String = "",
    val name: String = "",
    val desc: String = "",
    val tips: String = "",
    val terrain: String = "",
)

data class LevelPlan(
    val levelId: String = "",
    val levelName: String = "",
    val drills: List<DrillPayload> = emptyList(),
    val venues: List<VenuePayload> = emptyList(),
)

data class KeypointResult(
    val id: String,
    val name: String = "",
    val status: KeypointStatus,
    val score: Double? = null,
    val value: Double? = null,
    val evidenceMs: Double? = null,
    val good: String,
    val bad: String,
    val drills: List<DrillPayload> = emptyList(),
    val metricId: String = "",
    val faultyTurns: Int? = null,
    val totalTurns: Int? = null,
    val allowance: Int? = null,
)

/** One stage the classifier considered (desktop ``Candidate``). */
data class Candidate(
    val stageId: String = "",
    val stageName: String = "",
    val score: Double = 0.0,
    val fit: Double = 0.0,
    val gateRatio: Double = 0.0,
    val prior: Double = 0.0,
    val tier: String = "full",
    val separatingMetricId: String = "",
    val separatingMetricName: String = "",
    val rejectedReason: String = "",
)

/** Why this stage, and how sure (desktop ``Classification``). */
data class Classification(
    val method: String = "scored_candidates",
    val chosenId: String = "",
    val confidence: Double = 0.0,
    val separation: Double = 0.0,
    val qualityFactor: Double = 1.0,
    val candidates: List<Candidate> = emptyList(),
    val ambiguous: Boolean = false,
    val unusableReason: String = "",
)

data class SceneSummary(
    val snowSurface: String = "",
    val slopeBand: String = "",
    val viewClass: String = "",
    val viewAzimuthDeg: Double? = null,
    val cameraMotion: String = "",
    val fpsEffective: Double? = null,
    val missing: List<String> = emptyList(),
    /** Android prepare convenience; not in desktop SceneSummary. */
    val terrainType: String = "",
)

data class TurnRecord(
    val index: Int = 0,
    val side: String = "",
    val tStartMs: Double = 0.0,
    val tEndMs: Double = 0.0,
    val durationS: Double = 0.0,
    val amplitudeDeg: Double = 0.0,
    val flags: List<String> = emptyList(),
)

data class TurnSummary(
    val count: Int = 0,
    val leftCount: Int = 0,
    val rightCount: Int = 0,
    val meanDurationS: Double? = null,
    val durationCv: Double? = null,
    val turns: List<TurnRecord> = emptyList(),
    val faultCounts: Map<String, Int> = emptyMap(),
)

/** Knowledge-pack pointer only — no embedded tutorial lines. */
data class KnowledgeRef(
    val kbStage: String = "",
    val packVersion: String = "",
    val levelId: String = "",
)

data class KnowledgeFocus(
    val faultIds: List<String> = emptyList(),
    val drillIds: List<String> = emptyList(),
    val skillIds: List<String> = emptyList(),
    val weakestMetricId: String = "",
    val weakestMetricName: String = "",
)

data class MetricReport(
    val id: String,
    val name: String = "",
    val group: String = "",
    val state: MetricState = MetricState.UNKNOWN,
    val reason: String = "",
    val value: Double? = null,
    val unit: String = "",
    val display: String = "",
    val score: Double? = null,
    val rubric: Rubric = Rubric.NOT_RATED,
    val reliability: Double = 0.0,
    val isGate: Boolean = false,
    val standard: String = "",
    val form: String = "A",
    val perTurn: List<Double?> = emptyList(),
    val faultyTurns: Int? = null,
    val totalTurns: Int? = null,
    val evidenceMs: Double? = null,
    val side: String = "",
    val leftValue: Double? = null,
    val rightValue: Double? = null,
)

/** 2.1.0 path projection of ``StageReport.tree``. */
data class TreeNode(
    val id: String,
    val name: String,
    val current: Boolean = false,
)

data class TreeNodeV3(
    val id: String,
    val name: String,
    val kbStage: String = "",
    val tier: String = "full",
    val branch: String = "piste",
    val state: NodeState = NodeState.LOCKED,
    val scoreBest: Double? = null,
    val gatesPassed: String = "",
    val lockedReason: String = "",
    val inferredReason: String = "",
    val depth: Int = 0,
    val parents: List<String> = emptyList(),
    val children: List<String> = emptyList(),
)

data class FrameScorePoint(
    val tMs: Double,
    val score: Double,
)

data class PostureScores(
    val stability: Double = 0.0,
    val coordination: Double = 0.0,
    val control: Double = 0.0,
    val balance: Double = 0.0,
)

data class ProfileSummary(
    val ageBand: String = "",
    val ageYears: Double? = null,
    val sex: String = "",
    val heightCm: Double? = null,
    val weightKg: Double? = null,
    val skiCm: Double? = null,
    val isComplete: Boolean = false,
    val effects: List<String> = emptyList(),
    val overlays: List<String> = emptyList(),
)

data class FilmingIssue(
    val code: String,
    val message: String = "",
    val severity: String = "info",
)

data class StageReport(
    val schemaVersion: String = "3.0.0",
    val clipId: String,
    val categoryId: String,
    val stageId: String,
    val categoryName: String,
    val stageName: String,
    val confidence: Double,
    val readyForNextStage: Boolean,
    val disclaimer: String,
    val stageFocus: String = "",
    val trainingFocus: String = "",
    val howToAdvance: String = "",
    val score0100: Double = 0.0,
    val terrainId: String = "",
    val terrainName: String = "",
    val terrainDesc: String = "",
    val weakestCheckpointId: String = "",
    val nextLevelIds: List<String> = emptyList(),
    val nextLevelNames: List<String> = emptyList(),
    val nextPlans: List<LevelPlan> = emptyList(),
    val sessionPlan: List<DrillPayload> = emptyList(),
    val treePath: List<TreeNode> = emptyList(),
    val filmSteps: List<String> = emptyList(),
    val keypoints: List<KeypointResult>,
    val scoreSeries: List<FrameScorePoint> = emptyList(),
    val heuristicNotFisCarve: Boolean = false,
    val posture: PostureScores? = null,
    val kbStage: String = "",
    val tier: String = "full",
    val classification: Classification? = null,
    val metrics: List<MetricReport> = emptyList(),
    val turns: TurnSummary? = null,
    val tree: List<TreeNodeV3> = emptyList(),
    val knowledgeRef: KnowledgeRef? = null,
    val knowledgeFocus: KnowledgeFocus? = null,
    val scene: SceneSummary? = null,
    val profileSummary: ProfileSummary? = null,
    val filming: List<FilmingIssue> = emptyList(),
)

object StageReportJson {
    fun save(file: File, report: StageReport) {
        file.parentFile?.mkdirs()
        file.writeText(toJson(report).toString(2), Charsets.UTF_8)
    }

    fun load(file: File): StageReport? {
        if (!file.isFile) {
            return null
        }
        return try {
            fromJson(JSONObject(file.readText(Charsets.UTF_8)))
        } catch (_: Exception) {
            null
        }
    }

    fun toJson(report: StageReport): JSONObject {
        val obj = JSONObject()
            .put("schema_version", report.schemaVersion)
            .put("clip_id", report.clipId)
            .put("category_id", report.categoryId)
            .put("stage_id", report.stageId)
            .put("category_name", report.categoryName)
            .put("stage_name", report.stageName)
            .put("confidence", report.confidence)
            .put("ready_for_next_stage", report.readyForNextStage)
            .put("disclaimer", report.disclaimer)
            .put("stage_focus", report.stageFocus)
            .put("training_focus", report.trainingFocus)
            .put("how_to_advance", report.howToAdvance)
            .put("score_0_100", report.score0100)
            .put("terrain_id", report.terrainId)
            .put("terrain_name", report.terrainName)
            .put("terrain_desc", report.terrainDesc)
            .put("weakest_checkpoint_id", report.weakestCheckpointId)
            .put("heuristic_not_fis_carve", report.heuristicNotFisCarve)
            .put("kb_stage", report.kbStage)
            .put("tier", report.tier)
        obj.put("next_level_ids", JSONArray(report.nextLevelIds))
        obj.put("next_level_names", JSONArray(report.nextLevelNames))
        obj.put("film_steps", JSONArray(report.filmSteps))
        val kps = JSONArray()
        for (item in report.keypoints) {
            kps.put(keypointJson(item))
        }
        obj.put("keypoints", kps)
        val series = JSONArray()
        for (pt in report.scoreSeries) {
            series.put(JSONObject().put("t_ms", pt.tMs).put("score", pt.score))
        }
        obj.put("score_series", series)
        val treePath = JSONArray()
        for (node in report.treePath) {
            treePath.put(
                JSONObject()
                    .put("id", node.id)
                    .put("name", node.name)
                    .put("current", node.current),
            )
        }
        obj.put("tree_path", treePath)
        val plans = JSONArray()
        for (plan in report.nextPlans) {
            plans.put(planJson(plan))
        }
        obj.put("next_plans", plans)
        val session = JSONArray()
        for (drill in report.sessionPlan) {
            session.put(drillJson(drill))
        }
        obj.put("session_plan", session)
        if (report.posture != null) {
            obj.put(
                "posture",
                JSONObject()
                    .put("stability", report.posture.stability)
                    .put("coordination", report.posture.coordination)
                    .put("control", report.posture.control)
                    .put("balance", report.posture.balance),
            )
        } else {
            obj.put("posture", JSONObject.NULL)
        }
        if (report.classification != null) {
            obj.put("classification", classificationJson(report.classification))
        } else {
            obj.put("classification", JSONObject.NULL)
        }
        val metrics = JSONArray()
        for (m in report.metrics) {
            metrics.put(metricJson(m))
        }
        obj.put("metrics", metrics)
        if (report.turns != null) {
            obj.put("turns", turnsJson(report.turns))
        } else {
            obj.put("turns", JSONObject.NULL)
        }
        val tree = JSONArray()
        for (node in report.tree) {
            tree.put(treeNodeV3Json(node))
        }
        obj.put("tree", tree)
        if (report.knowledgeRef != null) {
            obj.put("knowledge_ref", knowledgeRefJson(report.knowledgeRef))
        } else {
            obj.put("knowledge_ref", JSONObject.NULL)
        }
        if (report.knowledgeFocus != null) {
            obj.put("knowledge_focus", knowledgeFocusJson(report.knowledgeFocus))
        } else {
            obj.put("knowledge_focus", JSONObject.NULL)
        }
        if (report.scene != null) {
            obj.put("scene", sceneJson(report.scene))
        } else {
            obj.put("scene", JSONObject.NULL)
        }
        if (report.profileSummary != null) {
            obj.put("profile_summary", profileJson(report.profileSummary))
        } else {
            obj.put("profile_summary", JSONObject.NULL)
        }
        val filming = JSONArray()
        for (issue in report.filming) {
            filming.put(
                JSONObject()
                    .put("code", issue.code)
                    .put("message", issue.message)
                    .put("severity", issue.severity),
            )
        }
        obj.put("filming", filming)
        return obj
    }

    fun fromJson(obj: JSONObject): StageReport {
        val kpsArr = obj.optJSONArray("keypoints") ?: JSONArray()
        val keypoints = ArrayList<KeypointResult>(kpsArr.length())
        for (i in 0 until kpsArr.length()) {
            val item = kpsArr.optJSONObject(i) ?: continue
            keypoints.add(keypointFrom(item))
        }
        val seriesArr = obj.optJSONArray("score_series") ?: JSONArray()
        val series = ArrayList<FrameScorePoint>(seriesArr.length())
        for (i in 0 until seriesArr.length()) {
            val item = seriesArr.optJSONObject(i) ?: continue
            series.add(FrameScorePoint(item.optDouble("t_ms"), item.optDouble("score")))
        }
        val treePathArr = obj.optJSONArray("tree_path") ?: JSONArray()
        val treePath = ArrayList<TreeNode>(treePathArr.length())
        for (i in 0 until treePathArr.length()) {
            val item = treePathArr.optJSONObject(i) ?: continue
            treePath.add(
                TreeNode(
                    id = item.optString("id"),
                    name = item.optString("name"),
                    current = item.optBoolean("current"),
                ),
            )
        }
        val metricsArr = obj.optJSONArray("metrics") ?: JSONArray()
        val metrics = ArrayList<MetricReport>(metricsArr.length())
        for (i in 0 until metricsArr.length()) {
            val item = metricsArr.optJSONObject(i) ?: continue
            metrics.add(metricFrom(item))
        }
        val treeArr = obj.optJSONArray("tree") ?: JSONArray()
        val tree = ArrayList<TreeNodeV3>(treeArr.length())
        for (i in 0 until treeArr.length()) {
            val item = treeArr.optJSONObject(i) ?: continue
            tree.add(treeNodeV3From(item))
        }
        val filmingArr = obj.optJSONArray("filming") ?: JSONArray()
        val filming = ArrayList<FilmingIssue>(filmingArr.length())
        for (i in 0 until filmingArr.length()) {
            val item = filmingArr.optJSONObject(i) ?: continue
            filming.add(
                FilmingIssue(
                    code = item.optString("code"),
                    message = item.optString("message"),
                    severity = item.optString("severity", "info"),
                ),
            )
        }
        val postureObj = obj.optJSONObject("posture")
        val classObj = obj.optJSONObject("classification")
        val sceneObj = obj.optJSONObject("scene")
        val turnsObj = obj.optJSONObject("turns")
        val knowledgeRefObj = obj.optJSONObject("knowledge_ref")
        val knowledgeFocusObj = obj.optJSONObject("knowledge_focus")
        val profileObj = obj.optJSONObject("profile_summary")
        return StageReport(
            schemaVersion = obj.optString("schema_version", "3.0.0"),
            clipId = obj.optString("clip_id"),
            categoryId = obj.optString("category_id"),
            stageId = obj.optString("stage_id"),
            categoryName = obj.optString("category_name"),
            stageName = obj.optString("stage_name"),
            confidence = obj.optDouble("confidence"),
            readyForNextStage = obj.optBoolean("ready_for_next_stage"),
            disclaimer = obj.optString("disclaimer"),
            stageFocus = obj.optString("stage_focus"),
            trainingFocus = obj.optString("training_focus"),
            howToAdvance = obj.optString("how_to_advance"),
            score0100 = obj.optDouble("score_0_100"),
            terrainId = obj.optString("terrain_id"),
            terrainName = obj.optString("terrain_name"),
            terrainDesc = obj.optString("terrain_desc"),
            weakestCheckpointId = obj.optString("weakest_checkpoint_id"),
            nextLevelIds = strList(obj.optJSONArray("next_level_ids")),
            nextLevelNames = strList(obj.optJSONArray("next_level_names")),
            nextPlans = planList(obj.optJSONArray("next_plans")),
            sessionPlan = drillList(obj.optJSONArray("session_plan")),
            treePath = treePath,
            filmSteps = strList(obj.optJSONArray("film_steps")),
            keypoints = keypoints,
            scoreSeries = series,
            heuristicNotFisCarve = obj.optBoolean("heuristic_not_fis_carve"),
            posture = postureObj?.let {
                PostureScores(
                    stability = it.optDouble("stability"),
                    coordination = it.optDouble("coordination"),
                    control = it.optDouble("control"),
                    balance = it.optDouble("balance"),
                )
            },
            kbStage = obj.optString("kb_stage"),
            tier = obj.optString("tier", "full"),
            classification = classObj?.let { classificationFrom(it) },
            metrics = metrics,
            turns = turnsObj?.let { turnsFrom(it) },
            tree = tree,
            knowledgeRef = knowledgeRefObj?.let { knowledgeRefFrom(it) },
            knowledgeFocus = knowledgeFocusObj?.let { knowledgeFocusFrom(it) },
            scene = sceneObj?.let { sceneFrom(it) },
            profileSummary = profileObj?.let { profileFrom(it) },
            filming = filming,
        )
    }

    private fun classificationJson(info: Classification): JSONObject {
        val cand = JSONArray()
        for (c in info.candidates) {
            cand.put(
                JSONObject()
                    .put("stage_id", c.stageId)
                    .put("stage_name", c.stageName)
                    .put("score", c.score)
                    .put("fit", c.fit)
                    .put("gate_ratio", c.gateRatio)
                    .put("prior", c.prior)
                    .put("tier", c.tier)
                    .put("separating_metric_id", c.separatingMetricId)
                    .put("separating_metric_name", c.separatingMetricName)
                    .put("rejected_reason", c.rejectedReason),
            )
        }
        return JSONObject()
            .put("method", info.method)
            .put("chosen_id", info.chosenId)
            .put("confidence", info.confidence)
            .put("separation", info.separation)
            .put("quality_factor", info.qualityFactor)
            .put("candidates", cand)
            .put("ambiguous", info.ambiguous)
            .put("unusable_reason", info.unusableReason)
    }

    private fun classificationFrom(obj: JSONObject): Classification {
        val arr = obj.optJSONArray("candidates") ?: JSONArray()
        val candidates = ArrayList<Candidate>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            candidates.add(
                Candidate(
                    stageId = item.optString("stage_id"),
                    stageName = item.optString("stage_name"),
                    score = item.optDouble("score"),
                    fit = item.optDouble("fit"),
                    gateRatio = item.optDouble("gate_ratio"),
                    prior = item.optDouble("prior"),
                    tier = item.optString("tier", "full"),
                    separatingMetricId = item.optString("separating_metric_id"),
                    separatingMetricName = item.optString("separating_metric_name"),
                    rejectedReason = item.optString("rejected_reason"),
                ),
            )
        }
        return Classification(
            method = obj.optString("method", "scored_candidates"),
            chosenId = obj.optString("chosen_id"),
            confidence = obj.optDouble("confidence"),
            separation = obj.optDouble("separation"),
            qualityFactor = if (obj.has("quality_factor")) obj.optDouble("quality_factor") else 1.0,
            candidates = candidates,
            ambiguous = obj.optBoolean("ambiguous"),
            unusableReason = obj.optString("unusable_reason"),
        )
    }

    private fun metricJson(m: MetricReport): JSONObject {
        val perTurn = JSONArray()
        for (v in m.perTurn) {
            if (v == null) perTurn.put(JSONObject.NULL) else perTurn.put(v)
        }
        val obj = JSONObject()
            .put("id", m.id)
            .put("name", m.name)
            .put("group", m.group)
            .put("state", m.state.wire)
            .put("reason", m.reason)
            .put("unit", m.unit)
            .put("display", m.display)
            .put("rubric", m.rubric.wire)
            .put("reliability", m.reliability)
            .put("is_gate", m.isGate)
            .put("standard", m.standard)
            .put("form", m.form)
            .put("per_turn", perTurn)
            .put("side", m.side)
        putNullable(obj, "value", m.value)
        putNullable(obj, "score", m.score)
        putNullableInt(obj, "faulty_turns", m.faultyTurns)
        putNullableInt(obj, "total_turns", m.totalTurns)
        putNullable(obj, "evidence_ms", m.evidenceMs)
        putNullable(obj, "left_value", m.leftValue)
        putNullable(obj, "right_value", m.rightValue)
        return obj
    }

    private fun metricFrom(obj: JSONObject): MetricReport {
        val perTurnArr = obj.optJSONArray("per_turn") ?: JSONArray()
        val perTurn = ArrayList<Double?>(perTurnArr.length())
        for (i in 0 until perTurnArr.length()) {
            perTurn.add(if (perTurnArr.isNull(i)) null else perTurnArr.optDouble(i))
        }
        return MetricReport(
            id = obj.optString("id"),
            name = obj.optString("name"),
            group = obj.optString("group"),
            state = MetricState.fromWire(obj.optString("state", "unknown")),
            reason = obj.optString("reason"),
            value = optDoubleOrNull(obj, "value"),
            unit = obj.optString("unit"),
            display = obj.optString("display"),
            score = optDoubleOrNull(obj, "score"),
            rubric = Rubric.fromWire(obj.optString("rubric", "not_rated")),
            reliability = obj.optDouble("reliability"),
            isGate = obj.optBoolean("is_gate"),
            standard = obj.optString("standard"),
            form = obj.optString("form", "A"),
            perTurn = perTurn,
            faultyTurns = optIntOrNull(obj, "faulty_turns"),
            totalTurns = optIntOrNull(obj, "total_turns"),
            evidenceMs = optDoubleOrNull(obj, "evidence_ms"),
            side = obj.optString("side"),
            leftValue = optDoubleOrNull(obj, "left_value"),
            rightValue = optDoubleOrNull(obj, "right_value"),
        )
    }

    private fun turnsJson(summary: TurnSummary): JSONObject {
        val turns = JSONArray()
        for (t in summary.turns) {
            turns.put(
                JSONObject()
                    .put("index", t.index)
                    .put("side", t.side)
                    .put("t_start_ms", t.tStartMs)
                    .put("t_end_ms", t.tEndMs)
                    .put("duration_s", t.durationS)
                    .put("amplitude_deg", t.amplitudeDeg)
                    .put("flags", JSONArray(t.flags)),
            )
        }
        val faults = JSONObject()
        for ((k, v) in summary.faultCounts) {
            faults.put(k, v)
        }
        val obj = JSONObject()
            .put("count", summary.count)
            .put("left_count", summary.leftCount)
            .put("right_count", summary.rightCount)
            .put("turns", turns)
            .put("fault_counts", faults)
        putNullable(obj, "mean_duration_s", summary.meanDurationS)
        putNullable(obj, "duration_cv", summary.durationCv)
        return obj
    }

    private fun turnsFrom(obj: JSONObject): TurnSummary {
        val arr = obj.optJSONArray("turns") ?: JSONArray()
        val turns = ArrayList<TurnRecord>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            turns.add(
                TurnRecord(
                    index = item.optInt("index"),
                    side = item.optString("side"),
                    tStartMs = item.optDouble("t_start_ms"),
                    tEndMs = item.optDouble("t_end_ms"),
                    durationS = item.optDouble("duration_s"),
                    amplitudeDeg = item.optDouble("amplitude_deg"),
                    flags = strList(item.optJSONArray("flags")),
                ),
            )
        }
        val faultObj = obj.optJSONObject("fault_counts")
        val faultCounts = LinkedHashMap<String, Int>()
        if (faultObj != null) {
            val keys = faultObj.keys()
            while (keys.hasNext()) {
                val key = keys.next()
                faultCounts[key] = faultObj.optInt(key)
            }
        }
        return TurnSummary(
            count = obj.optInt("count", turns.size),
            leftCount = obj.optInt("left_count"),
            rightCount = obj.optInt("right_count"),
            meanDurationS = optDoubleOrNull(obj, "mean_duration_s"),
            durationCv = optDoubleOrNull(obj, "duration_cv"),
            turns = turns,
            faultCounts = faultCounts,
        )
    }

    private fun treeNodeV3Json(node: TreeNodeV3): JSONObject {
        val obj = JSONObject()
            .put("id", node.id)
            .put("name", node.name)
            .put("kb_stage", node.kbStage)
            .put("tier", node.tier)
            .put("branch", node.branch)
            .put("state", node.state.wire)
            .put("gates_passed", node.gatesPassed)
            .put("locked_reason", node.lockedReason)
            .put("inferred_reason", node.inferredReason)
            .put("depth", node.depth)
            .put("parents", JSONArray(node.parents))
            .put("children", JSONArray(node.children))
        putNullable(obj, "score_best", node.scoreBest)
        return obj
    }

    private fun treeNodeV3From(obj: JSONObject): TreeNodeV3 =
        TreeNodeV3(
            id = obj.optString("id"),
            name = obj.optString("name"),
            kbStage = obj.optString("kb_stage"),
            tier = obj.optString("tier", "full"),
            branch = obj.optString("branch", "piste"),
            state = NodeState.fromWire(obj.optString("state", "locked")),
            scoreBest = optDoubleOrNull(obj, "score_best"),
            gatesPassed = obj.optString("gates_passed"),
            lockedReason = obj.optString("locked_reason"),
            inferredReason = obj.optString("inferred_reason"),
            depth = obj.optInt("depth"),
            parents = strList(obj.optJSONArray("parents")),
            children = strList(obj.optJSONArray("children")),
        )

    private fun knowledgeRefJson(ref: KnowledgeRef): JSONObject =
        JSONObject()
            .put("kb_stage", ref.kbStage)
            .put("pack_version", ref.packVersion)
            .put("level_id", ref.levelId)

    private fun knowledgeRefFrom(obj: JSONObject): KnowledgeRef =
        KnowledgeRef(
            kbStage = obj.optString("kb_stage"),
            packVersion = obj.optString("pack_version"),
            levelId = obj.optString("level_id"),
        )

    private fun knowledgeFocusJson(focus: KnowledgeFocus): JSONObject =
        JSONObject()
            .put("fault_ids", JSONArray(focus.faultIds))
            .put("drill_ids", JSONArray(focus.drillIds))
            .put("skill_ids", JSONArray(focus.skillIds))
            .put("weakest_metric_id", focus.weakestMetricId)
            .put("weakest_metric_name", focus.weakestMetricName)

    private fun knowledgeFocusFrom(obj: JSONObject): KnowledgeFocus =
        KnowledgeFocus(
            faultIds = strList(obj.optJSONArray("fault_ids")),
            drillIds = strList(obj.optJSONArray("drill_ids")),
            skillIds = strList(obj.optJSONArray("skill_ids")),
            weakestMetricId = obj.optString("weakest_metric_id"),
            weakestMetricName = obj.optString("weakest_metric_name"),
        )

    private fun sceneJson(scene: SceneSummary): JSONObject {
        val obj = JSONObject()
            .put("snow_surface", scene.snowSurface)
            .put("slope_band", scene.slopeBand)
            .put("view_class", scene.viewClass)
            .put("camera_motion", scene.cameraMotion)
            .put("missing", JSONArray(scene.missing))
        putNullable(obj, "view_azimuth_deg", scene.viewAzimuthDeg)
        putNullable(obj, "fps_effective", scene.fpsEffective)
        if (scene.terrainType.isNotBlank()) {
            obj.put("terrain_type", scene.terrainType)
        }
        return obj
    }

    private fun sceneFrom(obj: JSONObject): SceneSummary =
        SceneSummary(
            snowSurface = obj.optString("snow_surface"),
            slopeBand = obj.optString("slope_band"),
            viewClass = obj.optString("view_class").ifBlank { obj.optString("view") },
            viewAzimuthDeg = optDoubleOrNull(obj, "view_azimuth_deg"),
            cameraMotion = obj.optString("camera_motion"),
            fpsEffective = optDoubleOrNull(obj, "fps_effective"),
            missing = strList(obj.optJSONArray("missing")).ifEmpty {
                strList(obj.optJSONArray("missing_facts"))
            },
            terrainType = obj.optString("terrain_type"),
        )

    private fun profileJson(profile: ProfileSummary): JSONObject {
        val obj = JSONObject()
            .put("age_band", profile.ageBand)
            .put("sex", profile.sex)
            .put("is_complete", profile.isComplete)
            .put("effects", JSONArray(profile.effects))
            .put("overlays", JSONArray(profile.overlays))
        putNullable(obj, "age_years", profile.ageYears)
        putNullable(obj, "height_cm", profile.heightCm)
        putNullable(obj, "weight_kg", profile.weightKg)
        putNullable(obj, "ski_cm", profile.skiCm)
        return obj
    }

    private fun profileFrom(obj: JSONObject): ProfileSummary =
        ProfileSummary(
            ageBand = obj.optString("age_band"),
            ageYears = optDoubleOrNull(obj, "age_years"),
            sex = obj.optString("sex"),
            heightCm = optDoubleOrNull(obj, "height_cm"),
            weightKg = optDoubleOrNull(obj, "weight_kg"),
            skiCm = optDoubleOrNull(obj, "ski_cm"),
            isComplete = obj.optBoolean("is_complete"),
            effects = strList(obj.optJSONArray("effects")),
            overlays = strList(obj.optJSONArray("overlays")),
        )

    private fun keypointJson(item: KeypointResult): JSONObject {
        val obj = JSONObject()
            .put("id", item.id)
            .put("name", item.name)
            .put("status", item.status.name.lowercase())
            .put("good", item.good)
            .put("bad", item.bad)
        putNullable(obj, "score", item.score)
        putNullable(obj, "value", item.value)
        putNullable(obj, "evidence_ms", item.evidenceMs)
        val drills = JSONArray()
        for (drill in item.drills) {
            drills.put(drillJson(drill))
        }
        obj.put("drills", drills)
        if (item.metricId.isNotBlank()) {
            obj.put("metric_id", item.metricId)
        }
        putNullableInt(obj, "faulty_turns", item.faultyTurns)
        putNullableInt(obj, "total_turns", item.totalTurns)
        putNullableInt(obj, "allowance", item.allowance)
        return obj
    }

    private fun keypointFrom(obj: JSONObject): KeypointResult {
        val status = when (obj.optString("status")) {
            "pass" -> KeypointStatus.PASS
            "fail" -> KeypointStatus.FAIL
            else -> KeypointStatus.UNKNOWN
        }
        return KeypointResult(
            id = obj.optString("id"),
            name = obj.optString("name"),
            status = status,
            score = optDoubleOrNull(obj, "score"),
            value = optDoubleOrNull(obj, "value"),
            evidenceMs = optDoubleOrNull(obj, "evidence_ms"),
            good = obj.optString("good"),
            bad = obj.optString("bad"),
            drills = drillList(obj.optJSONArray("drills")),
            metricId = obj.optString("metric_id"),
            faultyTurns = optIntOrNull(obj, "faulty_turns"),
            totalTurns = optIntOrNull(obj, "total_turns"),
            allowance = optIntOrNull(obj, "allowance"),
        )
    }

    private fun drillJson(drill: DrillPayload): JSONObject {
        val venues = JSONArray()
        for (venue in drill.venues) {
            venues.put(
                JSONObject()
                    .put("id", venue.id)
                    .put("name", venue.name)
                    .put("desc", venue.desc)
                    .put("tips", venue.tips)
                    .put("terrain", venue.terrain),
            )
        }
        return JSONObject()
            .put("id", drill.id)
            .put("title", drill.title)
            .put("name", drill.name)
            .put("desc", drill.desc)
            .put("steps", JSONArray(drill.steps))
            .put("training", JSONArray(drill.training))
            .put("venues", venues)
    }

    private fun planJson(plan: LevelPlan): JSONObject {
        val drills = JSONArray()
        for (drill in plan.drills) {
            drills.put(drillJson(drill))
        }
        val venues = JSONArray()
        for (venue in plan.venues) {
            venues.put(
                JSONObject()
                    .put("id", venue.id)
                    .put("name", venue.name)
                    .put("desc", venue.desc)
                    .put("tips", venue.tips)
                    .put("terrain", venue.terrain),
            )
        }
        return JSONObject()
            .put("level_id", plan.levelId)
            .put("level_name", plan.levelName)
            .put("drills", drills)
            .put("venues", venues)
    }

    private fun drillList(arr: JSONArray?): List<DrillPayload> {
        if (arr == null) {
            return emptyList()
        }
        val out = ArrayList<DrillPayload>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                DrillPayload(
                    id = item.optString("id"),
                    title = item.optString("title"),
                    name = item.optString("name"),
                    desc = item.optString("desc"),
                    steps = strList(item.optJSONArray("steps")),
                    training = strList(item.optJSONArray("training")),
                    venues = venueList(item.optJSONArray("venues")),
                ),
            )
        }
        return out
    }

    private fun planList(arr: JSONArray?): List<LevelPlan> {
        if (arr == null) {
            return emptyList()
        }
        val out = ArrayList<LevelPlan>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                LevelPlan(
                    levelId = item.optString("level_id"),
                    levelName = item.optString("level_name"),
                    drills = drillList(item.optJSONArray("drills")),
                    venues = venueList(item.optJSONArray("venues")),
                ),
            )
        }
        return out
    }

    private fun venueList(arr: JSONArray?): List<VenuePayload> {
        if (arr == null) {
            return emptyList()
        }
        val out = ArrayList<VenuePayload>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                VenuePayload(
                    id = item.optString("id"),
                    name = item.optString("name"),
                    desc = item.optString("desc"),
                    tips = item.optString("tips"),
                    terrain = item.optString("terrain"),
                ),
            )
        }
        return out
    }

    private fun strList(arr: JSONArray?): List<String> {
        if (arr == null) {
            return emptyList()
        }
        val out = ArrayList<String>(arr.length())
        for (i in 0 until arr.length()) {
            out.add(arr.optString(i))
        }
        return out
    }

    private fun putNullable(obj: JSONObject, key: String, value: Double?) {
        if (value == null) obj.put(key, JSONObject.NULL) else obj.put(key, value)
    }

    private fun putNullableInt(obj: JSONObject, key: String, value: Int?) {
        if (value == null) {
            // omit unset optional ints (matches sparse keypoint dumps)
        } else {
            obj.put(key, value)
        }
    }

    private fun optDoubleOrNull(obj: JSONObject, key: String): Double? {
        if (!obj.has(key) || obj.isNull(key)) return null
        return obj.optDouble(key)
    }

    private fun optIntOrNull(obj: JSONObject, key: String): Int? {
        if (!obj.has(key) || obj.isNull(key)) return null
        return obj.optInt(key)
    }
}
