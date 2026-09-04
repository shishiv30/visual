package local.visual.corepose

import android.content.Context
import org.json.JSONObject
import java.io.File

data class LocText(val en: String, val zh: String = "")

data class Threshold(
    val op: String,
    val value: Double,
    val hi: Double? = null,
)

data class DrillSpec(
    val id: String,
    val name: LocText,
    val desc: LocText,
    val training: List<LocText>,
    val venueIds: List<String>,
)

data class CheckpointSpec(
    val id: String,
    val name: LocText,
    val desc: LocText,
    val body: List<String> = emptyList(),
    val required: Boolean,
    /** v2 / many v3 rows: whole-clip signal name. */
    val signal: String? = null,
    /** v3 metric-backed gates. */
    val metric: String? = null,
    val threshold: Threshold,
    val heuristicNotFisCarve: Boolean,
    val drills: List<String>,
)

data class Prerequisites(
    val levels: List<String> = emptyList(),
    val checkpoints: List<String> = emptyList(),
)

data class ProfileNote(
    val id: String,
    val status: String,
    val note: LocText? = null,
)

data class KbRefs(
    val tutorial: String? = null,
    val drills: List<String> = emptyList(),
    val faults: List<String> = emptyList(),
    val venue: String? = null,
    val equipment: String? = null,
)

data class ExclusionRule(
    val whenMetrics: Map<String, Double>,
    val rejectLevels: List<String>,
    val reason: String,
)

data class LevelSpec(
    val id: String,
    val categoryId: String,
    val inScope: Boolean,
    val heuristicNotFisCarve: Boolean,
    val name: LocText,
    val desc: LocText,
    val checkpoints: List<String>,
    val nextLevels: List<String>,
    val sessionDrills: List<String>,
    val terrain: String,
    val venueIds: List<String>,
    val kbStage: String = "",
    val tier: String? = null,
    val requiresScene: List<String> = emptyList(),
    val coreMetrics: List<String> = emptyList(),
    val gateMetrics: List<String> = emptyList(),
    val prerequisites: Prerequisites = Prerequisites(),
    val profileNotes: List<ProfileNote> = emptyList(),
    val kbRefs: KbRefs = KbRefs(),
)

data class TerrainSpec(
    val id: String,
    val name: LocText,
    val desc: LocText,
)

data class VenueSpec(
    val id: String,
    val terrain: String,
    val name: LocText,
    val desc: LocText,
    val tips: LocText,
)

data class Curriculum(
    val schemaVersion: String,
    val disclaimer: LocText,
    val passScore: Double,
    val checkpointPass: Double,
    val sysDrill: String,
    val categories: Map<String, LocText>,
    val terrains: Map<String, TerrainSpec>,
    val venues: Map<String, VenueSpec>,
    val drills: Map<String, DrillSpec>,
    val checkpoints: Map<String, CheckpointSpec>,
    val levels: Map<String, LevelSpec>,
    val levelIds: List<String> = emptyList(),
    val catalogLevelIds: List<String> = emptyList(),
    val exclusionRules: List<ExclusionRule> = emptyList(),
)

object CurriculumLoader {
    const val ASSET_NAME = "curriculum.v3.json"
    const val REQUIRED_SCHEMA = "3.0.0"

    fun load(json: String): Curriculum {
        val root = JSONObject(json)
        val schema = root.getString("schema_version")
        if (schema != REQUIRED_SCHEMA) {
            throw IllegalArgumentException("Expected curriculum schema $REQUIRED_SCHEMA, got $schema")
        }
        val categories = HashMap<String, LocText>()
        val catObj = root.getJSONObject("categories")
        val catKeys = catObj.keys()
        while (catKeys.hasNext()) {
            val key = catKeys.next()
            categories[key] = loc(catObj.getJSONObject(key))
        }
        val terrains = HashMap<String, TerrainSpec>()
        val terObj = root.getJSONObject("terrains")
        val terKeys = terObj.keys()
        while (terKeys.hasNext()) {
            val key = terKeys.next()
            val item = terObj.getJSONObject(key)
            terrains[key] = TerrainSpec(
                id = item.optString("id", key),
                name = loc(item.getJSONObject("name")),
                desc = loc(item.getJSONObject("desc")),
            )
        }
        val venues = HashMap<String, VenueSpec>()
        val venObj = root.getJSONObject("venues")
        val venKeys = venObj.keys()
        while (venKeys.hasNext()) {
            val key = venKeys.next()
            val item = venObj.getJSONObject(key)
            venues[key] = VenueSpec(
                id = item.optString("id", key),
                terrain = item.optString("terrain"),
                name = loc(item.getJSONObject("name")),
                desc = loc(item.getJSONObject("desc")),
                tips = loc(item.getJSONObject("tips")),
            )
        }
        val drills = HashMap<String, DrillSpec>()
        val drObj = root.getJSONObject("drills")
        val drKeys = drObj.keys()
        while (drKeys.hasNext()) {
            val key = drKeys.next()
            val item = drObj.getJSONObject(key)
            drills[key] = DrillSpec(
                id = item.optString("id", key),
                name = loc(item.getJSONObject("name")),
                desc = loc(item.getJSONObject("desc")),
                training = locList(item.optJSONArray("training")),
                venueIds = strList(item.optJSONArray("venue_ids")),
            )
        }
        val checkpoints = HashMap<String, CheckpointSpec>()
        val cpObj = root.getJSONObject("checkpoints")
        val cpKeys = cpObj.keys()
        while (cpKeys.hasNext()) {
            val key = cpKeys.next()
            val item = cpObj.getJSONObject(key)
            val thr = item.getJSONObject("threshold")
            val signal = if (item.isNull("signal")) null else item.optString("signal").ifBlank { null }
            val metric = if (item.isNull("metric")) null else item.optString("metric").ifBlank { null }
            checkpoints[key] = CheckpointSpec(
                id = item.optString("id", key),
                name = loc(item.getJSONObject("name")),
                desc = loc(item.getJSONObject("desc")),
                body = strList(item.optJSONArray("body")),
                required = item.optBoolean("required", true),
                signal = signal,
                metric = metric,
                threshold = Threshold(
                    op = thr.getString("op"),
                    value = thr.getDouble("value"),
                    hi = if (thr.has("hi") && !thr.isNull("hi")) thr.getDouble("hi") else null,
                ),
                heuristicNotFisCarve = item.optBoolean("heuristic_not_fis_carve", false),
                drills = strList(item.optJSONArray("drills")),
            )
        }
        val levels = HashMap<String, LevelSpec>()
        val lvObj = root.getJSONObject("levels")
        val lvKeys = lvObj.keys()
        while (lvKeys.hasNext()) {
            val key = lvKeys.next()
            val item = lvObj.getJSONObject(key)
            val prereqObj = item.optJSONObject("prerequisites")
            val kbObj = item.optJSONObject("kb_refs")
            val notesArr = item.optJSONArray("profile_notes")
            val notes = ArrayList<ProfileNote>()
            if (notesArr != null) {
                for (i in 0 until notesArr.length()) {
                    val n = notesArr.optJSONObject(i) ?: continue
                    notes.add(
                        ProfileNote(
                            id = n.optString("id"),
                            status = n.optString("status"),
                            note = n.optJSONObject("note")?.let { loc(it) },
                        ),
                    )
                }
            }
            levels[key] = LevelSpec(
                id = item.optString("id", key),
                categoryId = item.getString("category_id"),
                inScope = item.optBoolean("in_scope", true),
                heuristicNotFisCarve = item.optBoolean("heuristic_not_fis_carve", false),
                name = loc(item.getJSONObject("name")),
                desc = loc(item.getJSONObject("desc")),
                checkpoints = strList(item.optJSONArray("checkpoints")),
                nextLevels = strList(item.optJSONArray("next_levels")),
                sessionDrills = strList(item.optJSONArray("session_drills")),
                terrain = item.optString("terrain", "green"),
                venueIds = strList(item.optJSONArray("venue_ids")),
                kbStage = item.optString("kb_stage"),
                tier = item.optString("tier").ifBlank { null },
                requiresScene = strList(item.optJSONArray("requires_scene")),
                coreMetrics = strList(item.optJSONArray("core_metrics")),
                gateMetrics = strList(item.optJSONArray("gate_metrics")),
                prerequisites = Prerequisites(
                    levels = strList(prereqObj?.optJSONArray("levels")),
                    checkpoints = strList(prereqObj?.optJSONArray("checkpoints")),
                ),
                profileNotes = notes,
                kbRefs = KbRefs(
                    tutorial = kbObj?.optString("tutorial")?.ifBlank { null },
                    drills = strList(kbObj?.optJSONArray("drills")),
                    faults = strList(kbObj?.optJSONArray("faults")),
                    venue = kbObj?.optString("venue")?.ifBlank { null },
                    equipment = kbObj?.optString("equipment")?.ifBlank { null },
                ),
            )
        }
        val exclusion = ArrayList<ExclusionRule>()
        val exArr = root.optJSONArray("exclusion_rules")
        if (exArr != null) {
            for (i in 0 until exArr.length()) {
                val item = exArr.optJSONObject(i) ?: continue
                val whenObj = item.optJSONObject("when") ?: continue
                val whenMap = HashMap<String, Double>()
                val wk = whenObj.keys()
                while (wk.hasNext()) {
                    val k = wk.next()
                    whenMap[k] = whenObj.getDouble(k)
                }
                exclusion.add(
                    ExclusionRule(
                        whenMetrics = whenMap,
                        rejectLevels = strList(item.optJSONArray("reject_levels")),
                        reason = item.optString("reason"),
                    ),
                )
            }
        }
        return Curriculum(
            schemaVersion = schema,
            disclaimer = loc(root.getJSONObject("disclaimer")),
            passScore = root.optDouble("pass_score", 75.0),
            checkpointPass = root.optDouble("checkpoint_pass", 60.0),
            sysDrill = root.getString("sys_drill"),
            categories = categories,
            terrains = terrains,
            venues = venues,
            drills = drills,
            checkpoints = checkpoints,
            levels = levels,
            levelIds = strList(root.optJSONArray("level_ids")),
            catalogLevelIds = strList(root.optJSONArray("catalog_level_ids")),
            exclusionRules = exclusion,
        )
    }

    fun loadFile(file: File): Curriculum = load(file.readText(Charsets.UTF_8))

    fun loadFromAssets(context: Context): Curriculum {
        return context.assets.open(ASSET_NAME).bufferedReader().use { load(it.readText()) }
    }

    fun locText(item: LocText, lang: String): String {
        return if (lang == "zh" && item.zh.isNotBlank()) {
            item.zh
        } else {
            I18n.t(item.en, lang = lang)
        }
    }

    private fun loc(obj: JSONObject): LocText {
        return LocText(en = obj.optString("en"), zh = obj.optString("zh"))
    }

    private fun locList(arr: org.json.JSONArray?): List<LocText> {
        if (arr == null) {
            return emptyList()
        }
        val out = ArrayList<LocText>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(loc(item))
        }
        return out
    }

    private fun strList(arr: org.json.JSONArray?): List<String> {
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
