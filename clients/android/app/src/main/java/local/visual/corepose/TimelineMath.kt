package local.visual.corepose

import kotlin.math.max
import kotlin.math.min

object TimelineMath {
    const val MIN_ZOOM = 1.0
    const val MAX_ZOOM = 5.0
    const val MIN_RANGE_MS = 200
    const val RULER_TICK_PX = 100.0
    const val KEYFRAME_HIT_PX = 10.0

    fun clampZoom(zoom: Double): Double = max(MIN_ZOOM, min(MAX_ZOOM, zoom))

    fun contentWidthPx(viewportWidth: Int, zoom: Double): Double {
        return max(1.0, viewportWidth.toDouble()) * clampZoom(zoom)
    }

    fun maxScrollX(viewportWidth: Int, zoom: Double): Double {
        return max(0.0, contentWidthPx(viewportWidth, zoom) - viewportWidth.toDouble())
    }

    fun clampScrollX(scrollX: Double, viewportWidth: Int, zoom: Double): Double {
        return max(0.0, min(maxScrollX(viewportWidth, zoom), scrollX))
    }

    fun msToX(
        tMs: Double,
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double,
    ): Double {
        val duration = max(1.0, durationMs)
        val content = contentWidthPx(viewportWidth, zoom)
        return (tMs / duration) * content - scrollX
    }

    fun xToMs(
        x: Double,
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double,
    ): Double {
        val duration = max(1.0, durationMs)
        val content = contentWidthPx(viewportWidth, zoom)
        val tMs = ((x + scrollX) / content) * duration
        return max(0.0, min(duration, tMs))
    }

    fun clampRange(
        inMs: Int,
        outMs: Int?,
        durationMs: Int,
        minRangeMs: Int = MIN_RANGE_MS,
    ): Pair<Int, Int> {
        val duration = max(minRangeMs, durationMs)
        var start = inMs.coerceIn(0, duration)
        var end = if (outMs == null) duration else outMs.coerceIn(0, duration)
        if (end - start < minRangeMs) {
            end = min(duration, start + minRangeMs)
            if (end - start < minRangeMs) {
                start = max(0, end - minRangeMs)
            }
        }
        return start to end
    }

    fun zoomKeepingMs(
        zoom: Double,
        anchorX: Double,
        durationMs: Double,
        viewportWidth: Int,
        oldZoom: Double,
        oldScrollX: Double,
    ): Pair<Double, Double> {
        val newZoom = clampZoom(zoom)
        val tMs = xToMs(anchorX, durationMs, viewportWidth, oldZoom, oldScrollX)
        val content = contentWidthPx(viewportWidth, newZoom)
        val duration = max(1.0, durationMs)
        val newScroll = (tMs / duration) * content - anchorX
        return newZoom to clampScrollX(newScroll, viewportWidth, newZoom)
    }

    fun rulerTickMs(
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        tickPx: Double = RULER_TICK_PX,
    ): Double {
        val content = contentWidthPx(viewportWidth, zoom)
        val duration = max(1.0, durationMs)
        return (tickPx / content) * duration
    }

    fun nearestKeyframeMs(
        x: Double,
        keyframeMs: List<Int>,
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double,
        hitPx: Double = KEYFRAME_HIT_PX,
    ): Int? {
        var best: Int? = null
        var bestD = hitPx
        for (tMs in keyframeMs) {
            val kx = msToX(tMs.toDouble(), durationMs, viewportWidth, zoom, scrollX)
            val dist = kotlin.math.abs(kx - x)
            if (dist <= bestD) {
                bestD = dist
                best = tMs
            }
        }
        return best
    }

    /** Fine-scrub rates, picked by how far the finger has slid off the strip vertically. */
    val SCRUB_RATES = doubleArrayOf(1.0, 0.5, 0.25, 0.1)

    /**
     * Vertical distance of a touch from the strip band [top, bottom]; 0 while inside.
     */
    fun offStripPx(y: Double, top: Double, bottom: Double): Double {
        return when {
            y < top -> top - y
            y > bottom -> y - bottom
            else -> 0.0
        }
    }

    /**
     * Scrub-speed multiplier (1, 1/2, 1/4, 1/10): every [bandPx] the finger moves away from
     * the strip, a horizontal finger movement maps to a smaller time delta (iOS-style fine scrubbing).
     */
    fun scrubRate(offStripPx: Double, bandPx: Double): Double {
        if (bandPx <= 0.0 || offStripPx <= 0.0) {
            return SCRUB_RATES[0]
        }
        val band = (offStripPx / bandPx).toInt().coerceIn(0, SCRUB_RATES.size - 1)
        return SCRUB_RATES[band]
    }

    /** Time delta for a horizontal finger delta at the given zoom and scrub rate. */
    fun dxToMs(dxPx: Double, durationMs: Double, viewportWidth: Int, zoom: Double, rate: Double): Double {
        val content = contentWidthPx(viewportWidth, zoom)
        return dxPx / content * max(1.0, durationMs) * rate
    }

    /**
     * Auto-scroll step (px per frame) while a handle is dragged near the viewport edges.
     * Negative scrolls toward the start; 0 outside the edge zones. [x] is viewport-relative.
     */
    fun edgeAutoScrollPx(x: Double, viewportWidth: Int, zonePx: Double, maxStepPx: Double): Double {
        if (zonePx <= 0.0) {
            return 0.0
        }
        val w = viewportWidth.toDouble()
        return when {
            x < zonePx -> -maxStepPx * min(1.0, (zonePx - x) / zonePx)
            x > w - zonePx -> maxStepPx * min(1.0, (x - (w - zonePx)) / zonePx)
            else -> 0.0
        }
    }

    fun formatRulerTime(tMs: Double, fine: Boolean): String {
        val totalS = max(0.0, tMs / 1000.0)
        val minutes = (totalS / 60).toInt()
        val seconds = totalS - minutes * 60
        return if (fine) {
            String.format(java.util.Locale.US, "%d:%04.1f", minutes, seconds)
        } else {
            String.format(java.util.Locale.US, "%d:%02d", minutes, seconds.toInt())
        }
    }
}
