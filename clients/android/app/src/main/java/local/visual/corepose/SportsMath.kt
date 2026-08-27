package local.visual.corepose

import kotlin.math.pow
import kotlin.math.sqrt

object SportsMath {
    fun mean(values: DoubleArray): Double {
        if (values.isEmpty()) {
            return 0.0
        }
        return values.sum() / values.size
    }

    fun median(values: DoubleArray): Double {
        if (values.isEmpty()) {
            return 0.0
        }
        val sorted = values.sorted()
        val mid = sorted.size / 2
        return if (sorted.size % 2 == 0) {
            (sorted[mid - 1] + sorted[mid]) / 2.0
        } else {
            sorted[mid]
        }
    }

    fun std(values: DoubleArray): Double {
        if (values.isEmpty()) {
            return 0.0
        }
        val mu = mean(values)
        val varPop = values.sumOf { (it - mu).pow(2) } / values.size
        return sqrt(varPop)
    }

    fun percentile(values: DoubleArray, p: Double): Double {
        if (values.isEmpty()) {
            return 0.0
        }
        val sorted = values.sorted()
        if (sorted.size == 1) {
            return sorted[0]
        }
        val idx = (p / 100.0) * (sorted.size - 1)
        val lo = idx.toInt().coerceIn(0, sorted.lastIndex)
        val hi = (lo + 1).coerceAtMost(sorted.lastIndex)
        val frac = idx - lo
        return sorted[lo] * (1.0 - frac) + sorted[hi] * frac
    }

    fun angleDeg(ax: Double, ay: Double, bx: Double, by: Double, cx: Double, cy: Double): Double {
        val bax = ax - bx
        val bay = ay - by
        val bcx = cx - bx
        val bcy = cy - by
        val nba = sqrt(bax * bax + bay * bay)
        val nbc = sqrt(bcx * bcx + bcy * bcy)
        if (nba < 1e-6 || nbc < 1e-6) {
            return Double.NaN
        }
        val cos = ((bax * bcx + bay * bcy) / (nba * nbc)).coerceIn(-1.0, 1.0)
        return Math.toDegrees(Math.acos(cos))
    }

    fun zeroCrossFreq(series: DoubleArray, fps: Double): Double {
        if (series.size < 4) {
            return 0.0
        }
        val sign = DoubleArray(series.size) { i ->
            val s = kotlin.math.sign(series[i])
            if (s == 0.0) 1.0 else s
        }
        var crosses = 0
        for (i in 1 until sign.size) {
            if (sign[i] * sign[i - 1] < 0) {
                crosses += 1
            }
        }
        val dur = series.size / maxOf(fps, 1.0)
        return 0.5 * crosses / maxOf(dur, 1e-3)
    }
}
