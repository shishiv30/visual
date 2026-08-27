package local.visual.corepose

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

enum class KeypointStatus {
    PASS,
    FAIL,
    UNKNOWN,
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
)

data class TreeNode(
    val id: String,
    val name: String,
    val current: Boolean = false,
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

data class StageReport(
    val schemaVersion: String = "2.1.0",
    val clipId: String,
    val categoryId: String,
    val stageId: String,
    val categoryName: String,
    val stageName: String,
    val confidence: Double,
    val readyForNextStage: Boolean,
    val disclaimer: String,
    val stageFocus: String = "",
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
            .put("score_0_100", report.score0100)
            .put("terrain_id", report.terrainId)
            .put("terrain_name", report.terrainName)
            .put("terrain_desc", report.terrainDesc)
            .put("weakest_checkpoint_id", report.weakestCheckpointId)
            .put("heuristic_not_fis_carve", report.heuristicNotFisCarve)
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
        val tree = JSONArray()
        for (node in report.treePath) {
            tree.put(
                JSONObject()
                    .put("id", node.id)
                    .put("name", node.name)
                    .put("current", node.current),
            )
        }
        obj.put("tree_path", tree)
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
        val treeArr = obj.optJSONArray("tree_path") ?: JSONArray()
        val tree = ArrayList<TreeNode>(treeArr.length())
        for (i in 0 until treeArr.length()) {
            val item = treeArr.optJSONObject(i) ?: continue
            tree.add(
                TreeNode(
                    id = item.optString("id"),
                    name = item.optString("name"),
                    current = item.optBoolean("current"),
                ),
            )
        }
        val postureObj = obj.optJSONObject("posture")
        return StageReport(
            schemaVersion = obj.optString("schema_version", "2.1.0"),
            clipId = obj.optString("clip_id"),
            categoryId = obj.optString("category_id"),
            stageId = obj.optString("stage_id"),
            categoryName = obj.optString("category_name"),
            stageName = obj.optString("stage_name"),
            confidence = obj.optDouble("confidence"),
            readyForNextStage = obj.optBoolean("ready_for_next_stage"),
            disclaimer = obj.optString("disclaimer"),
            stageFocus = obj.optString("stage_focus"),
            score0100 = obj.optDouble("score_0_100"),
            terrainId = obj.optString("terrain_id"),
            terrainName = obj.optString("terrain_name"),
            terrainDesc = obj.optString("terrain_desc"),
            weakestCheckpointId = obj.optString("weakest_checkpoint_id"),
            nextLevelIds = strList(obj.optJSONArray("next_level_ids")),
            nextLevelNames = strList(obj.optJSONArray("next_level_names")),
            nextPlans = planList(obj.optJSONArray("next_plans")),
            sessionPlan = drillList(obj.optJSONArray("session_plan")),
            treePath = tree,
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
        )
    }

    private fun keypointJson(item: KeypointResult): JSONObject {
        val obj = JSONObject()
            .put("id", item.id)
            .put("name", item.name)
            .put("status", item.status.name.lowercase())
            .put("good", item.good)
            .put("bad", item.bad)
        if (item.score == null) obj.put("score", JSONObject.NULL) else obj.put("score", item.score)
        if (item.value == null) obj.put("value", JSONObject.NULL) else obj.put("value", item.value)
        if (item.evidenceMs == null) {
            obj.put("evidence_ms", JSONObject.NULL)
        } else {
            obj.put("evidence_ms", item.evidenceMs)
        }
        val drills = JSONArray()
        for (drill in item.drills) {
            drills.put(drillJson(drill))
        }
        obj.put("drills", drills)
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
            score = if (obj.isNull("score")) null else obj.optDouble("score"),
            value = if (obj.isNull("value")) null else obj.optDouble("value"),
            evidenceMs = if (obj.isNull("evidence_ms")) null else obj.optDouble("evidence_ms"),
            good = obj.optString("good"),
            bad = obj.optString("bad"),
            drills = drillList(obj.optJSONArray("drills")),
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
}
