package local.visual.corepose

/** Auto-generated from core/sports/bands.py — do not hand-edit the table. */
data class Band(
    val kind: String,
    val failLo: Double = Double.NEGATIVE_INFINITY,
    val passLo: Double = Double.NEGATIVE_INFINITY,
    val passHi: Double = Double.POSITIVE_INFINITY,
    val failHi: Double = Double.POSITIVE_INFINITY,
    val strongLo: Double = Double.NEGATIVE_INFINITY,
    val strongHi: Double = Double.POSITIVE_INFINITY,
    val allowRatio: Double = 0.10,
    val minAllowance: Int = 2,
    val reading: String = "signed",
) {
    companion object {
        fun gte(fail: Double, pass: Double, strong: Double, reading: String = "signed") =
            Band("gte", failLo = fail, passLo = pass, strongLo = strong, reading = reading)
        fun lte(strong: Double, pass: Double, fail: Double, reading: String = "signed") =
            Band("lte", passHi = pass, failHi = fail, strongHi = strong, reading = reading)
        fun between(failLo: Double, passLo: Double, passHi: Double, failHi: Double, reading: String = "signed"): Band {
            val mid = 0.5 * (passLo + passHi)
            val quarter = 0.25 * (passHi - passLo)
            return Band("between", failLo, passLo, passHi, failHi, mid - quarter, mid + quarter, reading = reading)
        }
        fun count(allowRatio: Double = 0.10, minAllowance: Int = 2) =
            Band("count", allowRatio = allowRatio, minAllowance = minAllowance)
    }

    fun read(value: Double?): Double? {
        if (value == null) return null
        return if (reading == "magnitude") kotlin.math.abs(value) else value
    }

    fun allowance(total: Int): Int {
        if (total <= 0) return minAllowance
        return maxOf(minAllowance, kotlin.math.ceil(allowRatio * total).toInt())
    }

    fun membership(value: Double?, faulty: Int? = null, total: Int? = null): Double? {
        if (kind == "count") {
            if (faulty == null || total == null || total <= 0) return null
            val allowed = allowance(total)
            val ratio = faulty.toDouble() / total.toDouble()
            val edge = (allowed / total.toDouble()) + 0.35
            if (faulty == 0) return 1.0
            if (ratio >= edge) return 0.0
            return ramp(ratio, edge, 0.0)
        }
        val raw = read(value) ?: return null
        if (raw in strongLo..strongHi) return 1.0
        if (raw < strongLo) {
            if (raw <= failLo) return 0.0
            return ramp(raw, failLo, strongLo)
        }
        if (raw >= failHi) return 0.0
        return ramp(raw, failHi, strongHi)
    }

    fun rubric(value: Double?, faulty: Int? = null, total: Int? = null): String {
        if (kind == "count") {
            if (faulty == null || total == null || total <= 0) return "not_rated"
            if (faulty == 0) return "strong"
            return if (faulty <= allowance(total)) "pass" else "not_yet"
        }
        val raw = read(value) ?: return "not_rated"
        if (raw in strongLo..strongHi) return "strong"
        if (raw in passLo..passHi) return "pass"
        return "not_yet"
    }

    fun score(value: Double?, faulty: Int? = null, total: Int? = null): Double? {
        if (kind == "count") {
            if (faulty == null || total == null || total <= 0) return null
            val allowed = allowance(total)
            val base = 100.0 * (1.0 - faulty.toDouble() / total.toDouble())
            if (faulty > allowed) return kotlin.math.round(minOf(base, 55.0) * 10.0) / 10.0
            return if (faulty == 0) 100.0 else kotlin.math.round(maxOf(base, 65.0) * 10.0) / 10.0
        }
        val raw = read(value) ?: return null
        if (kind == "gte") return piecewise(raw, failLo, passLo, strongLo)
        if (kind == "lte") return piecewise(-raw, -failHi, -passHi, -strongHi)
        val lo = passLo
        val hi = passHi
        if (raw in lo..hi) {
            val mid = 0.5 * (lo + hi)
            val span = maxOf((hi - lo) / 2.0, 1e-6)
            return kotlin.math.round((100.0 - 40.0 * kotlin.math.abs(raw - mid) / span) * 10.0) / 10.0
        }
        if (raw < lo) {
            val width = maxOf(lo - failLo, 1e-6)
            return kotlin.math.round(maxOf(0.0, 60.0 * (1.0 - (lo - raw) / width)) * 10.0) / 10.0
        }
        val width = maxOf(failHi - hi, 1e-6)
        return kotlin.math.round(maxOf(0.0, 60.0 * (1.0 - (raw - hi) / width)) * 10.0) / 10.0
    }

    fun standard(total: Int? = null): String {
        if (kind == "count") return "at most ${allowance(total ?: 0)} of ${total ?: 0}"
        if (kind == "gte") return "at least ${num(passLo)}"
        if (kind == "lte") return "at most ${num(passHi)}"
        return "${num(passLo)} to ${num(passHi)}"
    }

    fun widenedHigh(delta: Double): Band {
        if (delta <= 0.0 || kind == "count") return this
        return copy(
            passHi = if (passHi.isFinite()) passHi + delta else passHi,
            failHi = if (failHi.isFinite()) failHi + delta else failHi,
            strongHi = if (strongHi.isFinite()) strongHi + delta else strongHi,
        )
    }

    private fun ramp(value: Double, zeroAt: Double, oneAt: Double): Double {
        val span = oneAt - zeroAt
        if (!span.isFinite() || kotlin.math.abs(span) < 1e-12) return 0.0
        return ((value - zeroAt) / span).coerceIn(0.0, 1.0)
    }

    private fun piecewise(value: Double, lo: Double, mid: Double, hi: Double): Double {
        if (value <= lo) return 0.0
        if (value >= hi) return 100.0
        if (value < mid) {
            return kotlin.math.round(60.0 * (value - lo) / maxOf(mid - lo, 1e-6) * 10.0) / 10.0
        }
        return kotlin.math.round((60.0 + 40.0 * (value - mid) / maxOf(hi - mid, 1e-6)) * 10.0) / 10.0
    }

    private fun num(v: Double): String {
        return if (kotlin.math.abs(v - v.toInt()) < 1e-9) v.toInt().toString() else "%.2f".format(v)
    }
}

data class BandEvaluation(
    val membership: Double? = null,
    val rubric: String = "not_rated",
    val score: Double? = null,
    val passing: Boolean = false,
    val standard: String = "",
)

fun evaluateBand(band: Band?, item: MetricValue?): BandEvaluation {
    if (band == null || item == null || item.state != "ok") {
        return BandEvaluation()
    }
    val membership = band.membership(item.value, item.faultyTurns, item.totalTurns)
    val rubric = band.rubric(item.value, item.faultyTurns, item.totalTurns)
    val score = band.score(item.value, item.faultyTurns, item.totalTurns)
    val passing = rubric == "pass" || rubric == "strong"
    return BandEvaluation(membership, rubric, score, passing, band.standard(item.totalTurns))
}

object LevelBands {
    private val defaults: Map<String, Band> = mapOf(
        "stance_width" to Band.between(0.14, 0.22, 0.4, 0.58),
        "stance_width_var" to Band.lte(0.03, 0.1, 0.22),
        "wedge_angle" to Band.lte(3.0, 8.0, 20.0),
        "ski_wedge_angle" to Band.lte(3.0, 8.0, 20.0),
        "ski_parallelism" to Band.gte(0.7, 0.85, 1.0),
        "shin_angle_fore_aft" to Band.between(-2.0, 5.0, 25.0, 38.0),
        "hip_over_foot" to Band.between(-0.15, -0.05, 0.12, 0.25),
        "com_vertical_travel" to Band.gte(0.02, 0.06, 0.16),
        "edge_angle_proxy" to Band.gte(5.0, 12.0, 28.0),
        "inclination" to Band.gte(3.0, 8.0, 22.0),
        "angulation" to Band.gte(3.0, 8.0, 20.0),
        "banking_index" to Band.lte(0.35, 0.6, 0.85),
        "separation_angle" to Band.gte(4.0, 10.0, 26.0, reading = "magnitude"),
        "upper_body_quiet" to Band.lte(2.5, 7.0, 14.0),
        "knee_valgus" to Band.lte(0.1, 0.3, 0.6),
        "turn_rate" to Band.gte(0.08, 0.18, 0.4),
        "turn_duration_var" to Band.lte(0.08, 0.25, 0.5),
        "turn_amplitude" to Band.gte(5.0, 10.0, 28.0),
        "turn_shape_index" to Band.gte(0.22, 0.35, 0.58),
        "edge_change_duration" to Band.lte(0.15, 0.35, 0.7),
        "flexion_range" to Band.gte(6.0, 15.0, 32.0),
        "flexion_rate" to Band.gte(0.2, 0.45, 0.95),
        "pressure_peak_phase" to Band.between(0.15, 0.32, 0.7, 0.88),
        "stem_count" to Band.count(0.1, 2),
        "backseat_count" to Band.count(0.15, 2),
        "rotation_count" to Band.count(0.15, 2),
        "braking_count" to Band.count(0.1, 2),
        "asymmetry_index" to Band.lte(0.3, 0.8, 2.0, reading = "magnitude"),
        "hands_in_view" to Band.gte(0.3, 0.55, 0.85),
        "pole_touch_rate" to Band.gte(0.3, 0.7, 0.95),
        "pole_touch_timing" to Band.lte(0.1, 0.25, 0.5, reading = "magnitude"),
    )

    private val overrides: Map<String, Map<String, Band>> = mapOf(
        "pizza_glide" to mapOf(
            "stance_width" to Band.between(0.3, 0.4, 0.85, 1.1),
            "wedge_angle" to Band.gte(2.0, 10.0, 25.0),
            "ski_wedge_angle" to Band.gte(2.0, 10.0, 25.0),
            "knee_valgus" to Band.lte(0.15, 0.4, 0.75),
        ),
        "pizza" to mapOf(
            "stance_width" to Band.between(0.28, 0.38, 0.8, 1.05),
            "wedge_angle" to Band.gte(5.0, 12.0, 22.0),
            "ski_wedge_angle" to Band.gte(5.0, 12.0, 22.0),
            "turn_rate" to Band.gte(0.06, 0.15, 0.32),
            "turn_amplitude" to Band.gte(5.0, 10.0, 26.0),
            "turn_shape_index" to Band.gte(0.2, 0.32, 0.55),
            "separation_angle" to Band.lte(6.0, 16.0, 34.0, reading = "magnitude"),
            "asymmetry_index" to Band.lte(0.35, 1.0, 2.2, reading = "magnitude"),
        ),
        "sideslip" to mapOf(
            "edge_angle_proxy" to Band.between(2.0, 5.0, 25.0, 40.0),
            "upper_body_quiet" to Band.lte(2.5, 6.0, 12.0),
            "com_vertical_travel" to Band.lte(0.03, 0.08, 0.18),
            "flexion_range" to Band.gte(4.0, 10.0, 25.0),
        ),
        "wedge_christie" to mapOf(
            "wedge_angle" to Band.between(1.0, 3.0, 16.0, 30.0),
            "ski_wedge_angle" to Band.between(1.0, 3.0, 16.0, 30.0),
            "stance_width_var" to Band.gte(0.02, 0.06, 0.14),
            "knee_valgus" to Band.lte(0.12, 0.35, 0.68),
        ),
        "parallel" to mapOf(
            "stance_width" to Band.between(0.14, 0.22, 0.37, 0.55),
            "turn_shape_index" to Band.gte(0.25, 0.38, 0.6),
            "banking_index" to Band.lte(0.4, 0.7, 0.95),
        ),
        "dynamic_parallel" to mapOf(
            "flexion_range" to Band.gte(8.0, 18.0, 35.0),
            "com_vertical_travel" to Band.gte(0.03, 0.07, 0.18),
            "pressure_peak_phase" to Band.between(0.15, 0.35, 0.7, 0.88),
            "pole_touch_rate" to Band.gte(0.35, 0.8, 0.95),
            "turn_duration_var" to Band.lte(0.08, 0.2, 0.45),
        ),
        "firm_snow" to mapOf(
            "edge_angle_proxy" to Band.gte(6.0, 12.0, 26.0),
            "edge_change_duration" to Band.lte(0.14, 0.35, 0.7),
            "turn_shape_index" to Band.gte(0.3, 0.42, 0.65),
        ),
        "skid_short" to mapOf(
            "turn_rate" to Band.gte(0.35, 0.55, 0.85),
            "separation_angle" to Band.gte(6.0, 14.0, 30.0, reading = "magnitude"),
            "flexion_range" to Band.gte(8.0, 15.0, 30.0),
            "pole_touch_rate" to Band.gte(0.2, 0.5, 0.85),
        ),
        "carve_long" to mapOf(
            "edge_angle_proxy" to Band.gte(8.0, 15.0, 30.0),
            "turn_shape_index" to Band.gte(0.35, 0.48, 0.7),
            "asymmetry_index" to Band.lte(0.3, 0.8, 1.8, reading = "magnitude"),
        ),
        "carve_medium" to mapOf(
            "edge_angle_proxy" to Band.gte(10.0, 18.0, 34.0),
            "banking_index" to Band.lte(0.32, 0.55, 0.82),
            "angulation" to Band.gte(4.0, 10.0, 22.0),
            "turn_shape_index" to Band.gte(0.35, 0.48, 0.7),
            "turn_rate" to Band.between(0.25, 0.33, 0.55, 0.75),
            "asymmetry_index" to Band.lte(0.3, 0.8, 1.8, reading = "magnitude"),
        ),
        "carve_short" to mapOf(
            "edge_angle_proxy" to Band.gte(12.0, 22.0, 38.0),
            "banking_index" to Band.lte(0.3, 0.52, 0.8),
            "angulation" to Band.gte(5.0, 12.0, 24.0),
            "turn_shape_index" to Band.gte(0.35, 0.48, 0.7),
            "turn_rate" to Band.gte(0.45, 0.6, 0.9),
            "edge_change_duration" to Band.lte(0.1, 0.25, 0.55),
            "separation_angle" to Band.gte(6.0, 14.0, 30.0, reading = "magnitude"),
            "asymmetry_index" to Band.lte(0.3, 0.8, 1.8, reading = "magnitude"),
        ),
        "steeps" to mapOf(
            "turn_rate" to Band.gte(0.35, 0.5, 0.8),
            "edge_change_duration" to Band.lte(0.12, 0.3, 0.6),
            "separation_angle" to Band.gte(10.0, 25.0, 38.0, reading = "magnitude"),
            "braking_count" to Band.count(0.15, 3),
        ),
        "mogul_absorb" to mapOf(
            "flexion_range" to Band.gte(15.0, 30.0, 55.0),
            "flexion_rate" to Band.gte(0.2, 0.4, 0.9),
            "com_vertical_travel" to Band.gte(0.04, 0.1, 0.22),
            "upper_body_quiet" to Band.lte(3.0, 8.0, 16.0),
        ),
        "mogul_fallline" to mapOf(
            "flexion_range" to Band.gte(15.0, 30.0, 55.0),
            "flexion_rate" to Band.gte(0.25, 0.5, 1.0),
            "com_vertical_travel" to Band.gte(0.04, 0.1, 0.22),
            "upper_body_quiet" to Band.lte(3.0, 8.0, 16.0),
            "turn_rate" to Band.gte(0.45, 0.7, 1.1),
            "pressure_peak_phase" to Band.between(0.1, 0.25, 0.65, 0.85),
        ),
        "powder" to mapOf(
            "stance_width" to Band.between(0.08, 0.13, 0.34, 0.5),
            "com_vertical_travel" to Band.gte(0.04, 0.1, 0.2),
            "flexion_rate" to Band.between(0.15, 0.25, 0.7, 1.0),
            "turn_shape_index" to Band.between(0.3, 0.4, 0.75, 0.92),
            "asymmetry_index" to Band.lte(0.3, 0.9, 2.0, reading = "magnitude"),
        ),
    )

    private val ageWidenings = mapOf(
        "age-3-6" to mapOf("stance_width" to 0.18),
        "age-7-12" to mapOf("stance_width" to 0.12),
    )

    fun bandFor(levelId: String, metricId: String, ageBand: String? = null): Band? {
        val base = overrides[levelId]?.get(metricId) ?: defaults[metricId] ?: return null
        val delta = ageWidenings[ageBand.orEmpty()]?.get(metricId) ?: return base
        return base.widenedHigh(delta)
    }
}

