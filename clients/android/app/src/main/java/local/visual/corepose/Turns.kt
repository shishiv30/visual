package local.visual.corepose

/**
 * Lightweight turn segmentation from hip-X oscillation (Android port of the
 * desktop idea in `core.sports.turns` — not a full optical-flow port).
 */
data class TurnSegment(
    val index: Int,
    val startMs: Double,
    val endMs: Double,
    val direction: String,
) {
    val durationMs: Double get() = (endMs - startMs).coerceAtLeast(0.0)
}

data class TurnSegmentation(
    val turns: List<TurnSegment>,
) {
    val count: Int get() = turns.size
}

object Turns {
    fun segment(frames: List<AssessFrame>, fps: Double): TurnSegmentation {
        if (frames.size < 6 || fps <= 0.0) {
            return TurnSegmentation(emptyList())
        }
        val hipXs = frames.map { frame ->
            val joints = frame.blaze33
            if (joints.size < 25) {
                return@map null
            }
            val l = joints[23]
            val r = joints[24]
            if (l.confidence < 0.3f || r.confidence < 0.3f) {
                return@map null
            }
            0.5 * (l.x + r.x).toDouble() to frame.tMs
        }
        val series = hipXs.mapNotNull { it }
        if (series.size < 6) {
            return TurnSegmentation(emptyList())
        }
        val mean = series.map { it.first }.average()
        val signs = series.map { (x, t) ->
            val s = when {
                x > mean + 2.0 -> 1
                x < mean - 2.0 -> -1
                else -> 0
            }
            s to t
        }
        val turns = ArrayList<TurnSegment>()
        var lastSign = 0
        var startT = series.first().second
        var idx = 0
        for ((sign, t) in signs) {
            if (sign == 0) {
                continue
            }
            if (lastSign == 0) {
                lastSign = sign
                startT = t
                continue
            }
            if (sign != lastSign) {
                turns.add(
                    TurnSegment(
                        index = idx,
                        startMs = startT,
                        endMs = t,
                        direction = if (lastSign > 0) "right" else "left",
                    ),
                )
                idx += 1
                lastSign = sign
                startT = t
            }
        }
        if (lastSign != 0 && turns.isNotEmpty()) {
            val lastT = series.last().second
            if (lastT > startT) {
                turns.add(
                    TurnSegment(
                        index = idx,
                        startMs = startT,
                        endMs = lastT,
                        direction = if (lastSign > 0) "right" else "left",
                    ),
                )
            }
        }
        return TurnSegmentation(turns.filter { it.durationMs >= 200.0 })
    }

    fun toSummary(seg: TurnSegmentation, faultCounts: Map<String, Int> = emptyMap()): TurnSummary {
        val records = seg.turns.map { turn ->
            val side = when (turn.direction.lowercase()) {
                "left", "l" -> "L"
                "right", "r" -> "R"
                else -> turn.direction
            }
            TurnRecord(
                index = turn.index,
                side = side,
                tStartMs = turn.startMs,
                tEndMs = turn.endMs,
                durationS = turn.durationMs / 1000.0,
                amplitudeDeg = 0.0,
                flags = emptyList(),
            )
        }
        val left = records.count { it.side == "L" }
        val right = records.count { it.side == "R" }
        val durations = records.map { it.durationS }.filter { it > 0.0 }
        val mean = if (durations.isEmpty()) null else durations.average()
        val cv = if (durations.size < 2 || mean == null || mean <= 1e-6) {
            null
        } else {
            val variance = durations.map { (it - mean) * (it - mean) }.average()
            kotlin.math.sqrt(variance) / mean
        }
        return TurnSummary(
            count = records.size,
            leftCount = left,
            rightCount = right,
            meanDurationS = mean,
            durationCv = cv,
            turns = records,
            faultCounts = faultCounts,
        )
    }
}
