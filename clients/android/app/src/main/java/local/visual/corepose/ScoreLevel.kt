package local.visual.corepose

data class ScoredMetric(
    val report: MetricReport,
    val isGate: Boolean,
) {
    val measured: Boolean
        get() = report.state == MetricState.OK && report.score != null
}

object ScoreLevel {
    const val RELIABILITY_FLOOR = 0.15
    const val CONF_GATE = 0.35

    private val GROUP_NAMES = mapOf(
        "stance" to "Stance and balance",
        "edging" to "Edging and steering",
        "rhythm" to "Rhythm and turn shape",
        "faults" to "Turn faults",
        "poles" to "Poles and hands",
        "quality" to "Filming quality",
    )

    fun scoreLevel(
        pack: MetricPack,
        level: LevelSpec,
        knowledge: KnowledgePack?,
        lang: String,
    ): List<ScoredMetric> {
        val ids = (level.coreMetrics + level.gateMetrics).distinct()
        val gates = level.gateMetrics.toSet()
        val ageBand = pack.ageBand
        return ids.map { metricId ->
            val def = knowledge?.metrics?.get(metricId)
            val item = pack.get(metricId)
            val band = LevelBands.bandFor(level.id, metricId, ageBand)
            val eval = evaluateBand(band, item)
            val isGate = metricId in gates
            val state = when {
                item == null || item.state == "unknown" -> MetricState.UNKNOWN
                item.state == "not_applicable" -> MetricState.NOT_APPLICABLE
                else -> MetricState.OK
            }
            val reason = when (state) {
                MetricState.UNKNOWN -> I18n.t("Not measured in this clip.", lang = lang)
                MetricState.NOT_APPLICABLE -> I18n.t("Not applicable at this age.", lang = lang)
                else -> ""
            }
            val groupKey = def?.group.orEmpty()
            val unit = def?.unit.orEmpty()
            val form = item?.form ?: def?.forms?.firstOrNull() ?: "A"
            val display = formatDisplay(item, unit, lang)
            val reliability = if (state == MetricState.OK) {
                (item?.reliability ?: 0.55).coerceAtLeast(RELIABILITY_FLOOR)
            } else {
                0.0
            }
            ScoredMetric(
                report = MetricReport(
                    id = metricId,
                    name = MetricsBridge.displayName(metricId, lang),
                    group = groupLabel(groupKey, lang),
                    state = state,
                    reason = reason,
                    value = item?.value,
                    unit = unit,
                    display = display,
                    score = if (state == MetricState.OK) eval.score else null,
                    rubric = Rubric.fromWire(if (state == MetricState.OK) eval.rubric else "not_rated"),
                    reliability = reliability,
                    isGate = isGate,
                    standard = if (state == MetricState.OK) eval.standard else "",
                    form = form,
                    faultyTurns = item?.faultyTurns,
                    totalTurns = item?.totalTurns,
                ),
                isGate = isGate,
            )
        }
    }

    fun groupLabel(groupKey: String, lang: String): String {
        val key = GROUP_NAMES[groupKey] ?: groupKey
        return I18n.t(key, lang = lang)
    }

    fun stageScore(rows: List<ScoredMetric>, confidence: Double): Double {
        val gates = rows.filter { it.isGate && it.measured }
        if (gates.isEmpty()) return 0.0
        var num = 0.0
        var den = 0.0
        for (row in gates) {
            val w = row.report.reliability.coerceAtLeast(RELIABILITY_FLOOR)
            num += (row.report.score ?: 0.0) * w
            den += w
        }
        if (den <= 0.0) return 0.0
        val raw = num / den
        return kotlin.math.round(raw * (0.8 + 0.2 * confidence.coerceIn(0.0, 1.0)) * 10.0) / 10.0
    }

    fun readyForNextStage(
        rows: List<ScoredMetric>,
        confidence: Double,
        score: Double,
        passScore: Double,
    ): Boolean {
        if (confidence < CONF_GATE || score < passScore) return false
        val measuredGates = rows.filter { it.isGate && it.measured }
        if (measuredGates.isEmpty()) return false
        return measuredGates.all {
            it.report.rubric == Rubric.PASS || it.report.rubric == Rubric.STRONG
        }
    }

    fun weakest(rows: List<ScoredMetric>): ScoredMetric? {
        val measured = rows.filter { it.measured }
        if (measured.isEmpty()) return null
        return measured.minBy { it.report.score ?: 100.0 }
    }

    private fun formatDisplay(item: MetricValue?, unit: String, lang: String): String {
        if (item == null || item.state != "ok" || item.value == null) {
            if (item?.text?.isNotBlank() == true) return item.text
            return ""
        }
        if (item.form == "C" && item.totalTurns != null) {
            return I18n.t(
                "{n} of {total} turns",
                mapOf(
                    "n" to (item.faultyTurns ?: 0).toString(),
                    "total" to item.totalTurns.toString(),
                ),
                lang = lang,
            )
        }
        val v = item.value
        return when (unit.lowercase()) {
            "deg" -> "${v.toInt()}°"
            "hz" -> String.format("%.2f Hz", v)
            "s" -> String.format("%.2f s", v)
            "fraction", "ratio" -> String.format("%.2f", v)
            "turns" -> "${v.toInt()}"
            else -> String.format("%.2f", v)
        }
    }
}
