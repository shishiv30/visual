package local.visual.corepose

/**
 * Expand KnowledgePack loading for structured stage entities (desktop report_knowledge).
 * Flat LocText lists remain as display projections for simple call sites.
 */

data class KnowledgeSkill(
    val id: String,
    val name: LocText = LocText(""),
    val description: LocText = LocText(""),
    val why: LocText = LocText(""),
    val cues: List<LocText> = emptyList(),
)

data class KnowledgeDrill(
    val id: String,
    val name: LocText = LocText(""),
    val purpose: LocText = LocText(""),
    val setup: LocText = LocText(""),
    val steps: List<LocText> = emptyList(),
    val fixesFaults: List<String> = emptyList(),
    val dose: String = "",
)

data class KnowledgeFault(
    val id: String,
    val name: LocText = LocText(""),
    val looksLike: LocText = LocText(""),
    val symptom: LocText = LocText(""),
    val injuryRisk: LocText = LocText(""),
    val fixDrills: List<String> = emptyList(),
    val cues: List<LocText> = emptyList(),
)

data class KnowledgeTerrain(
    val id: String = "",
    val name: LocText = LocText(""),
    val desc: LocText = LocText(""),
)

data class KnowledgeEquipment(
    val id: String = "",
    val name: LocText = LocText(""),
    val desc: LocText = LocText(""),
)

object KnowledgeFocusBuilder {
    private val METRIC_ALIASES = listOf(
        "stance_width", "stance_width_var", "wedge_angle", "shin_angle_fore_aft",
        "hip_over_foot", "com_vertical_travel", "edge_angle_proxy", "inclination",
        "angulation", "banking_index", "separation_angle", "upper_body_quiet",
        "knee_valgus", "turn_rate", "turn_duration_var", "turn_amplitude",
        "turn_shape_index", "edge_change_duration", "flexion_range", "flexion_rate",
        "pressure_peak_phase", "stem_count", "backseat_count", "rotation_count",
        "braking_count", "asymmetry_index", "hands_in_view", "pole_touch_rate",
        "pole_touch_timing",
    )

    fun build(
        pack: KnowledgePack?,
        kbStage: String,
        rows: List<ScoredMetric>,
        weakestRow: ScoredMetric?,
        lang: String,
    ): KnowledgeFocus? {
        if (pack == null || kbStage.isBlank()) return null
        val stage = pack.stages[kbStage] ?: return null
        val scores = rows.filter { it.measured && it.report.score != null }
            .associate { it.report.id to (it.report.score ?: 100.0) }
        val gateScores = rows.filter { it.measured && it.isGate && it.report.score != null }
            .associate { it.report.id to (it.report.score ?: 100.0) }

        val ranked = ArrayList<Triple<Double, Int, String>>()
        stage.faultEntities.forEachIndexed { index, fault ->
            val metricId = matchMetric(fault)
            val score = scores[metricId]
            val rank = score ?: (1000.0 + index)
            ranked.add(Triple(rank, index, fault.id))
        }
        ranked.sortWith(compareBy({ it.first }, { it.second }))
        val faultIds = ranked.map { it.third }

        var weakMetric = ""
        if (gateScores.isNotEmpty()) {
            weakMetric = gateScores.minBy { it.value }.key
        } else if (weakestRow != null) {
            weakMetric = weakestRow.report.id
        }

        val weakFaults = stage.faultEntities
            .filter { weakMetric.isNotBlank() && matchMetric(it) == weakMetric }
            .map { it.id }
        val drillOrder = ArrayList<String>()
        for (faultId in weakFaults + faultIds.filter { it !in weakFaults }) {
            val fault = stage.faultEntities.firstOrNull { it.id == faultId }
            for (drillId in fault?.fixDrills.orEmpty()) {
                if (drillId !in drillOrder) drillOrder.add(drillId)
            }
            for (drill in stage.drillEntities) {
                if (faultId in drill.fixesFaults && drill.id !in drillOrder) {
                    drillOrder.add(drill.id)
                }
            }
        }
        for (drill in stage.drillEntities) {
            if (drill.id !in drillOrder) drillOrder.add(drill.id)
        }
        var skillIds = stage.skillEntities
            .filter { weakMetric.isNotBlank() && matchMetricText(it.name.en + " " + it.description.en) == weakMetric }
            .map { it.id }
        if (skillIds.isEmpty()) {
            skillIds = stage.skillEntities.take(1).map { it.id }
        }
        return KnowledgeFocus(
            faultIds = faultIds,
            drillIds = drillOrder,
            skillIds = skillIds,
            weakestMetricId = weakMetric,
            weakestMetricName = if (weakMetric.isNotBlank()) {
                MetricsBridge.displayName(weakMetric, lang)
            } else {
                ""
            },
        )
    }

    private fun matchMetric(fault: KnowledgeFault): String {
        val byName = matchMetricText(fault.name.en)
        if (byName.isNotBlank()) return byName
        return matchMetricText(
            listOf(fault.looksLike.en, fault.symptom.en).joinToString(" "),
        )
    }

    private fun matchMetricText(haystack: String): String {
        val lower = haystack.lowercase()
        for (id in METRIC_ALIASES) {
            val token = id.replace('_', ' ')
            if (token in lower || id in lower) return id
        }
        // Soft aliases
        if ("back seat" in lower || "backseat" in lower) return "backseat_count"
        if ("stem" in lower) return "stem_count"
        if ("rotation" in lower || "shoulder" in lower) return "rotation_count"
        if ("brak" in lower) return "braking_count"
        if ("stance" in lower) return "stance_width"
        if ("wedge" in lower || "pizza" in lower) return "wedge_angle"
        if ("edge" in lower) return "edge_angle_proxy"
        if ("rhythm" in lower) return "turn_duration_var"
        return ""
    }
}
