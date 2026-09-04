package local.visual.corepose

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class MetricDef(
    val id: String,
    val group: String = "",
    val unit: String = "",
    val forms: List<String> = emptyList(),
    val body: List<String> = emptyList(),
    val scored: Boolean = true,
    val proxy: Boolean = false,
    val proxyNote: String = "",
)

data class KnowledgeStageSlice(
    val id: String,
    val oneLine: LocText = LocText(""),
    val goal: LocText = LocText(""),
    val why: LocText = LocText(""),
    val drills: List<LocText> = emptyList(),
    val faults: List<LocText> = emptyList(),
    val terrain: List<LocText> = emptyList(),
    val equipment: List<LocText> = emptyList(),
    val skillEntities: List<KnowledgeSkill> = emptyList(),
    val drillEntities: List<KnowledgeDrill> = emptyList(),
    val faultEntities: List<KnowledgeFault> = emptyList(),
    val terrainEntities: List<KnowledgeTerrain> = emptyList(),
    val equipmentEntities: List<KnowledgeEquipment> = emptyList(),
    val tactics: List<LocText> = emptyList(),
)

data class KnowledgePack(
    val metrics: Map<String, MetricDef>,
    val stages: Map<String, KnowledgeStageSlice>,
    val levelMap: Map<String, String> = emptyMap(),
    val packVersion: String = "1",
)

object KnowledgePackLoader {
    fun loadMetrics(json: String): Map<String, MetricDef> {
        val root = JSONObject(json)
        val out = HashMap<String, MetricDef>()
        val keys = root.keys()
        while (keys.hasNext()) {
            val id = keys.next()
            val item = root.getJSONObject(id)
            out[id] = MetricDef(
                id = id,
                group = item.optString("group"),
                unit = item.optString("unit"),
                forms = strList(item.optJSONArray("forms")),
                body = strList(item.optJSONArray("body")),
                scored = item.optBoolean("scored", true),
                proxy = item.optBoolean("proxy", false),
                proxyNote = item.optString("proxy_note"),
            )
        }
        return out
    }

    fun loadKb(json: String): Triple<Map<String, KnowledgeStageSlice>, Map<String, String>, String> {
        val root = JSONObject(json)
        val version = root.optString("pack_version", root.optString("version", "1"))
        val stagesObj = root.optJSONObject("stages") ?: JSONObject()
        val out = HashMap<String, KnowledgeStageSlice>()
        val keys = stagesObj.keys()
        while (keys.hasNext()) {
            val id = keys.next()
            val item = stagesObj.optJSONObject(id) ?: continue
            val en = item.optJSONObject("en") ?: JSONObject()
            val zh = item.optJSONObject("zh") ?: JSONObject()
            val skills = parseSkills(en, zh)
            val drills = parseDrills(en, zh)
            val faults = parseFaults(en, zh)
            val terrain = parseTerrain(en, zh)
            val equipment = parseEquipment(en, zh)
            out[id] = KnowledgeStageSlice(
                id = id,
                oneLine = bilingual(en, zh, "one_line"),
                goal = bilingual(en, zh, "goal"),
                why = bilingual(en, zh, "why_it_matters"),
                drills = drills.map { it.name },
                faults = faults.map { it.name },
                terrain = terrain.map { it.name.ifBlankLoc(it.desc) },
                equipment = equipment.map { it.name.ifBlankLoc(it.desc) },
                skillEntities = skills,
                drillEntities = drills,
                faultEntities = faults,
                terrainEntities = terrain,
                equipmentEntities = equipment,
                tactics = bilingualList(en, zh, "tactics"),
            )
        }
        val levelMap = HashMap<String, String>()
        val mapObj = root.optJSONObject("level_map")
        if (mapObj != null) {
            val mk = mapObj.keys()
            while (mk.hasNext()) {
                val lid = mk.next()
                levelMap[lid] = mapObj.optString(lid)
            }
        }
        return Triple(out, levelMap, version.ifBlank { "1" })
    }

    fun loadFromAssets(context: Context): KnowledgePack {
        val metricsJson = context.assets.open("knowledge/metrics.json").bufferedReader().use { it.readText() }
        val kbJson = context.assets.open("knowledge/kb.v1.json").bufferedReader().use { it.readText() }
        val (stages, levelMap, version) = loadKb(kbJson)
        return KnowledgePack(
            metrics = loadMetrics(metricsJson),
            stages = stages,
            levelMap = levelMap,
            packVersion = version,
        )
    }

    fun loadFromRepo(repoRoot: File): KnowledgePack {
        val metrics = File(repoRoot, "content/ski/knowledge/metrics.json")
        val kb = File(repoRoot, "content/ski/knowledge/kb.v1.json")
        val (stages, levelMap, version) = loadKb(kb.readText(Charsets.UTF_8))
        return KnowledgePack(
            metrics = loadMetrics(metrics.readText(Charsets.UTF_8)),
            stages = stages,
            levelMap = levelMap,
            packVersion = version,
        )
    }

    fun stageForLevel(pack: KnowledgePack, levelId: String, kbStage: String): KnowledgeStageSlice? {
        if (kbStage.isNotBlank()) {
            pack.stages[kbStage]?.let { return it }
        }
        val mapped = pack.levelMap[levelId] ?: return null
        return pack.stages[mapped]
    }

    fun resolveKbStage(pack: KnowledgePack?, levelId: String, kbStage: String): String {
        if (pack == null) return kbStage
        return stageForLevel(pack, levelId, kbStage)?.id.orEmpty()
    }

    fun text(item: LocText, lang: String): String {
        return if (lang == "zh" && item.zh.isNotBlank()) item.zh else item.en
    }

    private fun LocText.ifBlankLoc(other: LocText): LocText {
        return if (en.isBlank() && zh.isBlank()) other else this
    }

    private fun bilingual(en: JSONObject, zh: JSONObject, key: String): LocText {
        return LocText(en = en.optString(key), zh = zh.optString(key))
    }

    private fun bilingualList(en: JSONObject, zh: JSONObject, key: String): List<LocText> {
        val enArr = en.optJSONArray(key)
        val zhArr = zh.optJSONArray(key)
        val n = maxOf(enArr?.length() ?: 0, zhArr?.length() ?: 0)
        if (n == 0) return emptyList()
        val out = ArrayList<LocText>(n)
        for (i in 0 until n) {
            out.add(
                LocText(
                    en = arrayItemText(enArr, i),
                    zh = arrayItemText(zhArr, i),
                ),
            )
        }
        return out.filter { it.en.isNotBlank() || it.zh.isNotBlank() }
    }

    private fun parseSkills(en: JSONObject, zh: JSONObject): List<KnowledgeSkill> {
        val enArr = en.optJSONArray("skills") ?: return emptyList()
        val zhArr = zh.optJSONArray("skills")
        val out = ArrayList<KnowledgeSkill>()
        for (i in 0 until enArr.length()) {
            val e = enArr.optJSONObject(i) ?: continue
            val z = zhArr?.optJSONObject(i)
            out.add(
                KnowledgeSkill(
                    id = e.optString("id"),
                    name = LocText(e.optString("name"), z?.optString("name").orEmpty()),
                    description = LocText(e.optString("description"), z?.optString("description").orEmpty()),
                    why = LocText(e.optString("why"), z?.optString("why").orEmpty()),
                    cues = stringListLoc(e.optJSONArray("cues"), z?.optJSONArray("cues")),
                ),
            )
        }
        return out
    }

    private fun parseDrills(en: JSONObject, zh: JSONObject): List<KnowledgeDrill> {
        val enArr = en.optJSONArray("drills") ?: return emptyList()
        val zhArr = zh.optJSONArray("drills")
        val out = ArrayList<KnowledgeDrill>()
        for (i in 0 until enArr.length()) {
            val e = enArr.optJSONObject(i) ?: continue
            val z = zhArr?.optJSONObject(i)
            val doseObj = e.optJSONObject("dose")
            val dose = if (doseObj != null) {
                val sets = doseObj.optInt("sets", 0)
                val reps = doseObj.optInt("reps", 0)
                if (sets > 0 || reps > 0) "${sets}×${reps}" else ""
            } else {
                e.optString("dose")
            }
            out.add(
                KnowledgeDrill(
                    id = e.optString("id"),
                    name = LocText(e.optString("name"), z?.optString("name").orEmpty()),
                    purpose = LocText(e.optString("purpose"), z?.optString("purpose").orEmpty()),
                    setup = LocText(e.optString("setup"), z?.optString("setup").orEmpty()),
                    steps = stringListLoc(e.optJSONArray("steps"), z?.optJSONArray("steps")),
                    fixesFaults = strList(e.optJSONArray("fixes_faults")),
                    dose = dose,
                ),
            )
        }
        return out
    }

    private fun parseFaults(en: JSONObject, zh: JSONObject): List<KnowledgeFault> {
        val enArr = en.optJSONArray("faults") ?: return emptyList()
        val zhArr = zh.optJSONArray("faults")
        val out = ArrayList<KnowledgeFault>()
        for (i in 0 until enArr.length()) {
            val e = enArr.optJSONObject(i) ?: continue
            val z = zhArr?.optJSONObject(i)
            val fix = e.optJSONObject("fix")
            val zFix = z?.optJSONObject("fix")
            out.add(
                KnowledgeFault(
                    id = e.optString("id"),
                    name = LocText(
                        e.optString("name").ifBlank { e.optString("looks_like").take(48) },
                        z?.optString("name").orEmpty(),
                    ),
                    looksLike = LocText(e.optString("looks_like"), z?.optString("looks_like").orEmpty()),
                    symptom = LocText(e.optString("symptom"), z?.optString("symptom").orEmpty()),
                    injuryRisk = LocText(
                        e.optString("injury_risk").ifBlank { fix?.optString("equipment_check").orEmpty() },
                        z?.optString("injury_risk").orEmpty(),
                    ),
                    fixDrills = strList(fix?.optJSONArray("drills")),
                    cues = stringListLoc(fix?.optJSONArray("cues"), zFix?.optJSONArray("cues")),
                ),
            )
        }
        return out
    }

    private fun parseTerrain(en: JSONObject, zh: JSONObject): List<KnowledgeTerrain> {
        val enArr = en.optJSONArray("terrain") ?: return emptyList()
        val zhArr = zh.optJSONArray("terrain")
        val out = ArrayList<KnowledgeTerrain>()
        for (i in 0 until enArr.length()) {
            val raw = enArr.opt(i)
            val zRaw = zhArr?.opt(i)
            if (raw is JSONObject) {
                val z = zRaw as? JSONObject
                out.add(
                    KnowledgeTerrain(
                        id = raw.optString("id"),
                        name = LocText(raw.optString("name"), z?.optString("name").orEmpty()),
                        desc = LocText(
                            raw.optString("desc").ifBlank { raw.optString("description") },
                            z?.optString("desc").orEmpty(),
                        ),
                    ),
                )
            } else if (raw is String) {
                out.add(KnowledgeTerrain(name = LocText(raw, (zRaw as? String).orEmpty())))
            }
        }
        return out
    }

    private fun parseEquipment(en: JSONObject, zh: JSONObject): List<KnowledgeEquipment> {
        val enArr = en.optJSONArray("equipment") ?: return emptyList()
        val zhArr = zh.optJSONArray("equipment")
        val out = ArrayList<KnowledgeEquipment>()
        for (i in 0 until enArr.length()) {
            val raw = enArr.opt(i)
            val zRaw = zhArr?.opt(i)
            if (raw is JSONObject) {
                val z = zRaw as? JSONObject
                out.add(
                    KnowledgeEquipment(
                        id = raw.optString("id"),
                        name = LocText(raw.optString("name"), z?.optString("name").orEmpty()),
                        desc = LocText(
                            raw.optString("desc").ifBlank { raw.optString("description") },
                            z?.optString("desc").orEmpty(),
                        ),
                    ),
                )
            } else if (raw is String) {
                out.add(KnowledgeEquipment(name = LocText(raw, (zRaw as? String).orEmpty())))
            }
        }
        return out
    }

    private fun stringListLoc(enArr: JSONArray?, zhArr: JSONArray?): List<LocText> {
        val n = maxOf(enArr?.length() ?: 0, zhArr?.length() ?: 0)
        if (n == 0) return emptyList()
        val out = ArrayList<LocText>(n)
        for (i in 0 until n) {
            out.add(
                LocText(
                    en = enArr?.optString(i).orEmpty(),
                    zh = zhArr?.optString(i).orEmpty(),
                ),
            )
        }
        return out.filter { it.en.isNotBlank() || it.zh.isNotBlank() }
    }

    private fun arrayItemText(arr: JSONArray?, index: Int): String {
        if (arr == null || index >= arr.length()) return ""
        return when (val raw = arr.opt(index)) {
            is JSONObject -> raw.optString("en").ifBlank {
                raw.optString("name").ifBlank { raw.optString("title").ifBlank { raw.optString("one_line") } }
            }
            is String -> raw
            else -> ""
        }
    }

    private fun strList(arr: JSONArray?): List<String> {
        if (arr == null) return emptyList()
        val out = ArrayList<String>(arr.length())
        for (i in 0 until arr.length()) out.add(arr.optString(i))
        return out
    }
}
