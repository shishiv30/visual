package local.visual.corepose

object Posture {
    fun scores(pack: FeaturePack, results: List<KeypointResult> = emptyList()): PostureScores {
        val stability = clamp(
            0.55 * scoreQuiet(pack.upperQuiet) + 0.45 * scoreStanceLock(pack.stanceWidthStd),
        )
        val coordination = clamp(
            0.6 * scoreRhythm(pack.kneeFlexFreq, pack.turnFreq) + 0.4 * scoreHands(pack.handsLow),
        )
        val fromKp = scoreControlFromKeypoints(results)
        val lean = scoreLean(pack.inwardLean)
        val control = if (fromKp == null) lean else clamp(0.65 * fromKp + 0.35 * lean)
        val balance = scoreBalance(pack.backseat, pack.kneeValgus)
        return PostureScores(
            stability = round1(stability),
            coordination = round1(coordination),
            control = round1(control),
            balance = round1(balance),
        )
    }

    private fun clamp(value: Double): Double = value.coerceIn(0.0, 100.0)

    private fun round1(value: Double): Double = kotlin.math.round(value * 10.0) / 10.0

    private fun scoreQuiet(upperQuiet: Double): Double = clamp(100.0 - upperQuiet * 35.0)

    private fun scoreStanceLock(stanceStd: Double): Double = clamp(100.0 - stanceStd * 40.0)

    private fun scoreRhythm(kneeFreq: Double, turnFreq: Double): Double {
        if (kneeFreq <= 0.05 && turnFreq <= 0.05) {
            return 45.0
        }
        val ratio = minOf(kneeFreq, turnFreq) / maxOf(kneeFreq, turnFreq, 1e-3)
        return clamp(40.0 + ratio * 60.0)
    }

    private fun scoreHands(handsLow: Double): Double = clamp(handsLow * 100.0)

    private fun scoreControlFromKeypoints(results: List<KeypointResult>): Double? {
        val known = results.mapNotNull { it.score }
        if (known.isEmpty()) {
            return null
        }
        return clamp(known.average())
    }

    private fun scoreLean(inwardLean: Double): Double {
        if (inwardLean <= 0.05) {
            return 55.0
        }
        if (inwardLean <= 0.35) {
            return clamp(55.0 + inwardLean * 100.0)
        }
        return clamp(100.0 - (inwardLean - 0.35) * 80.0)
    }

    private fun scoreBalance(backseat: Double, kneeValgus: Double): Double {
        val seat = clamp(100.0 - kotlin.math.abs(backseat) * 80.0)
        val valgus = clamp(100.0 - kotlin.math.abs(kneeValgus - 0.15) * 120.0)
        return clamp(0.55 * seat + 0.45 * valgus)
    }
}
