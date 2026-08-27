package local.visual.corepose

object ClipRange {
    const val FRAME_STRIDE = 2

    fun collectSeeds(seeds: List<SeedMark>, seedBox: NormBox?): List<SeedMark> {
        if (seeds.isNotEmpty()) {
            return seeds.sortedBy { it.tMs }
        }
        if (seedBox != null) {
            return listOf(SeedMark(0.0, seedBox))
        }
        return emptyList()
    }

    fun seedAt(tMs: Double, seeds: List<SeedMark>, halfMs: Double): SeedMark? {
        var hit: SeedMark? = null
        var best = halfMs
        for (item in seeds) {
            val delta = kotlin.math.abs(item.tMs - tMs)
            if (delta <= best) {
                best = delta
                hit = item
            }
        }
        return hit
    }

    fun inPlayRange(tMs: Double, startMs: Double, endMs: Double): Boolean {
        return tMs in startMs..endMs
    }

    fun clampPlayheadMs(tMs: Long, startMs: Long, endMs: Long): Long {
        val hi = (endMs - 1L).coerceAtLeast(startMs)
        return tMs.coerceIn(startMs, hi)
    }

    fun pastPlayEnd(posMs: Long, endMs: Long): Boolean {
        return posMs >= endMs
    }

    fun shouldReseekToStart(posMs: Long, startMs: Long, seekPending: Boolean): Boolean {
        return !seekPending && posMs < startMs
    }

    fun strideMs(fps: Double): Long {
        val step = (1000.0 / maxOf(fps, 1.0)) * FRAME_STRIDE
        return step.toLong().coerceAtLeast(1L).let { rounded ->
            if (step - rounded >= 0.5) rounded + 1 else rounded
        }
    }

    fun halfMs(fps: Double): Double {
        return (1000.0 / maxOf(fps, 1.0)) * FRAME_STRIDE / 2.0
    }
}
