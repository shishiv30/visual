"""Generate LevelBands.kt from core.sports.bands DEFAULTS + OVERRIDES."""
from __future__ import annotations

import math
from pathlib import Path

from core.sports.bands import DEFAULTS, OVERRIDES


def f(x: float) -> str:
    if x == math.inf or x == float("inf"):
        return "Double.POSITIVE_INFINITY"
    if x == -math.inf or x == float("-inf"):
        return "Double.NEGATIVE_INFINITY"
    return repr(float(x))


def emit_band(b) -> str:
    if b.kind == "gte":
        reading = f', reading = "{b.reading}"' if b.reading != "signed" else ""
        return f"Band.gte({f(b.fail_lo)}, {f(b.pass_lo)}, {f(b.strong_lo)}{reading})"
    if b.kind == "lte":
        reading = f', reading = "{b.reading}"' if b.reading != "signed" else ""
        return f"Band.lte({f(b.strong_hi)}, {f(b.pass_hi)}, {f(b.fail_hi)}{reading})"
    if b.kind == "between":
        reading = f', reading = "{b.reading}"' if b.reading != "signed" else ""
        return (
            f"Band.between({f(b.fail_lo)}, {f(b.pass_lo)}, {f(b.pass_hi)}, {f(b.fail_hi)}{reading})"
        )
    if b.kind == "count":
        return f"Band.count({b.allow_ratio}, {b.min_allowance})"
    return "Band.gte(0.0, 0.5, 1.0)"


def emit_map(name: str, table: dict) -> list[str]:
    lines = [f"    private val {name}: Map<String, Band> = mapOf("]
    if isinstance(next(iter(table.values())), dict):
        # OVERRIDES: Map<String, Map<String, Band>>
        lines = [f"    private val {name}: Map<String, Map<String, Band>> = mapOf("]
        for level, metrics in table.items():
            lines.append(f'        "{level}" to mapOf(')
            for mid, b in metrics.items():
                lines.append(f'            "{mid}" to {emit_band(b)},')
            lines.append("        ),")
        lines.append("    )")
        return lines
    for mid, b in table.items():
        lines.append(f'        "{mid}" to {emit_band(b)},')
    lines.append("    )")
    return lines


def main() -> None:
    lines: list[str] = []
    lines.append("package local.visual.corepose")
    lines.append("")
    lines.append("/** Auto-generated from core/sports/bands.py — do not hand-edit the table. */")
    lines.append("data class Band(")
    lines.append("    val kind: String,")
    lines.append("    val failLo: Double = Double.NEGATIVE_INFINITY,")
    lines.append("    val passLo: Double = Double.NEGATIVE_INFINITY,")
    lines.append("    val passHi: Double = Double.POSITIVE_INFINITY,")
    lines.append("    val failHi: Double = Double.POSITIVE_INFINITY,")
    lines.append("    val strongLo: Double = Double.NEGATIVE_INFINITY,")
    lines.append("    val strongHi: Double = Double.POSITIVE_INFINITY,")
    lines.append("    val allowRatio: Double = 0.10,")
    lines.append("    val minAllowance: Int = 2,")
    lines.append('    val reading: String = "signed",')
    lines.append(") {")
    lines.append("    companion object {")
    lines.append(
        '        fun gte(fail: Double, pass: Double, strong: Double, reading: String = "signed") ='
    )
    lines.append(
        '            Band("gte", failLo = fail, passLo = pass, strongLo = strong, reading = reading)'
    )
    lines.append(
        '        fun lte(strong: Double, pass: Double, fail: Double, reading: String = "signed") ='
    )
    lines.append(
        '            Band("lte", passHi = pass, failHi = fail, strongHi = strong, reading = reading)'
    )
    lines.append(
        '        fun between(failLo: Double, passLo: Double, passHi: Double, failHi: Double, reading: String = "signed"): Band {'
    )
    lines.append("            val mid = 0.5 * (passLo + passHi)")
    lines.append("            val quarter = 0.25 * (passHi - passLo)")
    lines.append(
        '            return Band("between", failLo, passLo, passHi, failHi, mid - quarter, mid + quarter, reading = reading)'
    )
    lines.append("        }")
    lines.append("        fun count(allowRatio: Double = 0.10, minAllowance: Int = 2) =")
    lines.append(
        '            Band("count", allowRatio = allowRatio, minAllowance = minAllowance)'
    )
    lines.append("    }")
    lines.append("")
    lines.append("    fun read(value: Double?): Double? {")
    lines.append("        if (value == null) return null")
    lines.append('        return if (reading == "magnitude") kotlin.math.abs(value) else value')
    lines.append("    }")
    lines.append("")
    lines.append("    fun allowance(total: Int): Int {")
    lines.append("        if (total <= 0) return minAllowance")
    lines.append("        return maxOf(minAllowance, kotlin.math.ceil(allowRatio * total).toInt())")
    lines.append("    }")
    lines.append("")
    lines.append(
        "    fun membership(value: Double?, faulty: Int? = null, total: Int? = null): Double? {"
    )
    lines.append('        if (kind == "count") {')
    lines.append("            if (faulty == null || total == null || total <= 0) return null")
    lines.append("            val allowed = allowance(total)")
    lines.append("            val ratio = faulty.toDouble() / total.toDouble()")
    lines.append("            val edge = (allowed / total.toDouble()) + 0.35")
    lines.append("            if (faulty == 0) return 1.0")
    lines.append("            if (ratio >= edge) return 0.0")
    lines.append("            return ramp(ratio, edge, 0.0)")
    lines.append("        }")
    lines.append("        val raw = read(value) ?: return null")
    lines.append("        if (raw in strongLo..strongHi) return 1.0")
    lines.append("        if (raw < strongLo) {")
    lines.append("            if (raw <= failLo) return 0.0")
    lines.append("            return ramp(raw, failLo, strongLo)")
    lines.append("        }")
    lines.append("        if (raw >= failHi) return 0.0")
    lines.append("        return ramp(raw, failHi, strongHi)")
    lines.append("    }")
    lines.append("")
    lines.append(
        "    fun rubric(value: Double?, faulty: Int? = null, total: Int? = null): String {"
    )
    lines.append('        if (kind == "count") {')
    lines.append(
        '            if (faulty == null || total == null || total <= 0) return "not_rated"'
    )
    lines.append('            if (faulty == 0) return "strong"')
    lines.append('            return if (faulty <= allowance(total)) "pass" else "not_yet"')
    lines.append("        }")
    lines.append('        val raw = read(value) ?: return "not_rated"')
    lines.append('        if (raw in strongLo..strongHi) return "strong"')
    lines.append('        if (raw in passLo..passHi) return "pass"')
    lines.append('        return "not_yet"')
    lines.append("    }")
    lines.append("")
    lines.append(
        "    fun score(value: Double?, faulty: Int? = null, total: Int? = null): Double? {"
    )
    lines.append('        if (kind == "count") {')
    lines.append("            if (faulty == null || total == null || total <= 0) return null")
    lines.append("            val allowed = allowance(total)")
    lines.append("            val base = 100.0 * (1.0 - faulty.toDouble() / total.toDouble())")
    lines.append(
        "            if (faulty > allowed) return kotlin.math.round(minOf(base, 55.0) * 10.0) / 10.0"
    )
    lines.append(
        "            return if (faulty == 0) 100.0 else kotlin.math.round(maxOf(base, 65.0) * 10.0) / 10.0"
    )
    lines.append("        }")
    lines.append("        val raw = read(value) ?: return null")
    lines.append('        if (kind == "gte") return piecewise(raw, failLo, passLo, strongLo)')
    lines.append('        if (kind == "lte") return piecewise(-raw, -failHi, -passHi, -strongHi)')
    lines.append("        val lo = passLo")
    lines.append("        val hi = passHi")
    lines.append("        if (raw in lo..hi) {")
    lines.append("            val mid = 0.5 * (lo + hi)")
    lines.append("            val span = maxOf((hi - lo) / 2.0, 1e-6)")
    lines.append(
        "            return kotlin.math.round((100.0 - 40.0 * kotlin.math.abs(raw - mid) / span) * 10.0) / 10.0"
    )
    lines.append("        }")
    lines.append("        if (raw < lo) {")
    lines.append("            val width = maxOf(lo - failLo, 1e-6)")
    lines.append(
        "            return kotlin.math.round(maxOf(0.0, 60.0 * (1.0 - (lo - raw) / width)) * 10.0) / 10.0"
    )
    lines.append("        }")
    lines.append("        val width = maxOf(failHi - hi, 1e-6)")
    lines.append(
        "        return kotlin.math.round(maxOf(0.0, 60.0 * (1.0 - (raw - hi) / width)) * 10.0) / 10.0"
    )
    lines.append("    }")
    lines.append("")
    lines.append("    fun standard(total: Int? = null): String {")
    lines.append(
        '        if (kind == "count") return "at most ${allowance(total ?: 0)} of ${total ?: 0}"'
    )
    lines.append('        if (kind == "gte") return "at least ${num(passLo)}"')
    lines.append('        if (kind == "lte") return "at most ${num(passHi)}"')
    lines.append('        return "${num(passLo)} to ${num(passHi)}"')
    lines.append("    }")
    lines.append("")
    lines.append("    fun widenedHigh(delta: Double): Band {")
    lines.append('        if (delta <= 0.0 || kind == "count") return this')
    lines.append("        return copy(")
    lines.append(
        "            passHi = if (passHi.isFinite()) passHi + delta else passHi,"
    )
    lines.append(
        "            failHi = if (failHi.isFinite()) failHi + delta else failHi,"
    )
    lines.append(
        "            strongHi = if (strongHi.isFinite()) strongHi + delta else strongHi,"
    )
    lines.append("        )")
    lines.append("    }")
    lines.append("")
    lines.append("    private fun ramp(value: Double, zeroAt: Double, oneAt: Double): Double {")
    lines.append("        val span = oneAt - zeroAt")
    lines.append("        if (!span.isFinite() || kotlin.math.abs(span) < 1e-12) return 0.0")
    lines.append("        return ((value - zeroAt) / span).coerceIn(0.0, 1.0)")
    lines.append("    }")
    lines.append("")
    lines.append(
        "    private fun piecewise(value: Double, lo: Double, mid: Double, hi: Double): Double {"
    )
    lines.append("        if (value <= lo) return 0.0")
    lines.append("        if (value >= hi) return 100.0")
    lines.append("        if (value < mid) {")
    lines.append(
        "            return kotlin.math.round(60.0 * (value - lo) / maxOf(mid - lo, 1e-6) * 10.0) / 10.0"
    )
    lines.append("        }")
    lines.append(
        "        return kotlin.math.round((60.0 + 40.0 * (value - mid) / maxOf(hi - mid, 1e-6)) * 10.0) / 10.0"
    )
    lines.append("    }")
    lines.append("")
    lines.append("    private fun num(v: Double): String {")
    lines.append(
        '        return if (kotlin.math.abs(v - v.toInt()) < 1e-9) v.toInt().toString() else "%.2f".format(v)'
    )
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("data class BandEvaluation(")
    lines.append("    val membership: Double? = null,")
    lines.append('    val rubric: String = "not_rated",')
    lines.append("    val score: Double? = null,")
    lines.append("    val passing: Boolean = false,")
    lines.append('    val standard: String = "",')
    lines.append(")")
    lines.append("")
    lines.append(
        "fun evaluateBand(band: Band?, item: MetricValue?): BandEvaluation {"
    )
    lines.append("    if (band == null || item == null || item.state != \"ok\") {")
    lines.append("        return BandEvaluation()")
    lines.append("    }")
    lines.append("    val membership = band.membership(item.value, item.faultyTurns, item.totalTurns)")
    lines.append("    val rubric = band.rubric(item.value, item.faultyTurns, item.totalTurns)")
    lines.append("    val score = band.score(item.value, item.faultyTurns, item.totalTurns)")
    lines.append('    val passing = rubric == "pass" || rubric == "strong"')
    lines.append(
        "    return BandEvaluation(membership, rubric, score, passing, band.standard(item.totalTurns))"
    )
    lines.append("}")
    lines.append("")
    lines.append("object LevelBands {")
    lines.extend(emit_map("defaults", DEFAULTS))
    lines.append("")
    lines.extend(emit_map("overrides", OVERRIDES))
    lines.append("")
    lines.append("    private val ageWidenings = mapOf(")
    lines.append('        "age-3-6" to mapOf("stance_width" to 0.18),')
    lines.append('        "age-7-12" to mapOf("stance_width" to 0.12),')
    lines.append("    )")
    lines.append("")
    lines.append(
        "    fun bandFor(levelId: String, metricId: String, ageBand: String? = null): Band? {"
    )
    lines.append(
        "        val base = overrides[levelId]?.get(metricId) ?: defaults[metricId] ?: return null"
    )
    lines.append("        val delta = ageWidenings[ageBand.orEmpty()]?.get(metricId) ?: return base")
    lines.append("        return base.widenedHigh(delta)")
    lines.append("    }")
    lines.append("}")
    lines.append("")

    out = Path("clients/android/app/src/main/java/local/visual/corepose/LevelBands.kt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
