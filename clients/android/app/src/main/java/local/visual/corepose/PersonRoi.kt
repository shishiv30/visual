package local.visual.corepose

data class PixelBox(
    val x1: Double,
    val y1: Double,
    val x2: Double,
    val y2: Double,
) {
    fun toBBox(): BBox = BBox(x1.toFloat(), y1.toFloat(), x2.toFloat(), y2.toFloat())
}

data class CropSpec(
    val ox: Int,
    val oy: Int,
    val x2: Int,
    val y2: Int,
    val scale: Double,
)

object PersonRoi {
    const val HIST_H_BINS = 30
    const val HIST_S_BINS = 32
    const val MIN_SAT = 40
    const val MAX_VAL = 250
    const val SEARCH_EXPAND = 1.8
    const val POSE_PAD = 0.35
    const val MIN_CROP_SIDE = 256
    const val TERM_COUNT = 12
    const val TERM_EPS = 1.0

    fun denormBox(seed: NormBox, width: Int, height: Int): PixelBox {
        return PixelBox(
            seed.x1 * width.toDouble(),
            seed.y1 * height.toDouble(),
            seed.x2 * width.toDouble(),
            seed.y2 * height.toDouble(),
        )
    }

    fun clipBox(box: PixelBox, width: Int, height: Int): IntArray {
        val nx1 = maxOf(0.0, minOf(box.x1, box.x2)).toInt()
        val ny1 = maxOf(0.0, minOf(box.y1, box.y2)).toInt()
        val nx2 = minOf(width.toDouble(), maxOf(box.x1, box.x2)).toInt()
        val ny2 = minOf(height.toDouble(), maxOf(box.y1, box.y2)).toInt()
        if (nx2 <= nx1 || ny2 <= ny1) {
            return intArrayOf(0, 0, width, height)
        }
        return intArrayOf(nx1, ny1, nx2, ny2)
    }

    fun cropRect(
        box: PixelBox,
        width: Int,
        height: Int,
        pad: Double = POSE_PAD,
        minSide: Int = MIN_CROP_SIDE,
    ): CropSpec {
        val bw = maxOf(1.0, box.x2 - box.x1)
        val bh = maxOf(1.0, box.y2 - box.y1)
        val padded = PixelBox(
            box.x1 - bw * pad,
            box.y1 - bh * pad,
            box.x2 + bw * pad,
            box.y2 + bh * pad,
        )
        val clipped = clipBox(padded, width, height)
        val cw = (clipped[2] - clipped[0]).coerceAtLeast(1)
        val ch = (clipped[3] - clipped[1]).coerceAtLeast(1)
        val shortest = minOf(cw, ch)
        val scale = if (shortest < minSide) minSide.toDouble() / shortest.toDouble() else 1.0
        return CropSpec(clipped[0], clipped[1], clipped[2], clipped[3], scale)
    }

    fun remapPoint(x: Double, y: Double, ox: Int, oy: Int, scale: Double): Pair<Double, Double> {
        val inv = if (scale == 0.0) 1.0 else 1.0 / scale
        return x * inv + ox to y * inv + oy
    }

    fun buildHist(pixels: IntArray, width: Int, height: Int, box: PixelBox): FloatArray {
        val hist = FloatArray(HIST_H_BINS * HIST_S_BINS)
        val clip = clipBox(box, width, height)
        val hsv = FloatArray(3)
        for (y in clip[1] until clip[3]) {
            for (x in clip[0] until clip[2]) {
                val argb = pixels[y * width + x]
                toHsv(argb, hsv)
                val h = hsv[0]
                val s = hsv[1]
                val v = hsv[2]
                if (s < MIN_SAT || v < 32 || v > MAX_VAL) {
                    continue
                }
                val hb = ((h / 180.0) * HIST_H_BINS).toInt().coerceIn(0, HIST_H_BINS - 1)
                val sb = ((s / 256.0) * HIST_S_BINS).toInt().coerceIn(0, HIST_S_BINS - 1)
                hist[hb * HIST_S_BINS + sb] += 1f
            }
        }
        var max = 0f
        for (value in hist) {
            if (value > max) {
                max = value
            }
        }
        if (max > 0f) {
            val gain = 255f / max
            for (i in hist.indices) {
                hist[i] *= gain
            }
        }
        return hist
    }

    fun search(
        pixels: IntArray,
        width: Int,
        height: Int,
        hist: FloatArray,
        prev: PixelBox,
    ): PixelBox {
        val back = backProject(pixels, width, height, hist)
        val window = expandWindow(prev, width, height, SEARCH_EXPAND)
        var x = window[0]
        var y = window[1]
        var w = window[2]
        var h = window[3]
        for (iter in 0 until TERM_COUNT) {
            var m00 = 0.0
            var m10 = 0.0
            var m01 = 0.0
            val x2 = (x + w).coerceAtMost(width)
            val y2 = (y + h).coerceAtMost(height)
            for (py in y until y2) {
                val row = py * width
                for (px in x until x2) {
                    val mass = back[row + px].toDouble()
                    m00 += mass
                    m10 += px * mass
                    m01 += py * mass
                }
            }
            if (m00 < 1.0) {
                break
            }
            val cx = (m10 / m00).toInt()
            val cy = (m01 / m00).toInt()
            val nx = (cx - w / 2).coerceIn(0, width - 1)
            val ny = (cy - h / 2).coerceIn(0, height - 1)
            val dx = kotlin.math.abs(nx - x)
            val dy = kotlin.math.abs(ny - y)
            x = nx
            y = ny
            if (dx < TERM_EPS && dy < TERM_EPS) {
                break
            }
        }
        if (w >= 8 && h >= 8) {
            return PixelBox(
                x.toDouble(),
                y.toDouble(),
                (x + w).coerceAtMost(width).toDouble(),
                (y + h).coerceAtMost(height).toDouble(),
            )
        }
        return peakFallback(back, width, height, prev)
    }

    fun blendHist(prev: FloatArray, next: FloatArray, alpha: Float = 0.15f): FloatArray {
        val mixed = FloatArray(prev.size)
        var max = 0f
        for (i in prev.indices) {
            val value = (1f - alpha) * prev[i] + alpha * next[i]
            mixed[i] = value
            if (value > max) {
                max = value
            }
        }
        if (max > 0f) {
            val gain = 255f / max
            for (i in mixed.indices) {
                mixed[i] *= gain
            }
        }
        return mixed
    }

    private fun backProject(pixels: IntArray, width: Int, height: Int, hist: FloatArray): FloatArray {
        val out = FloatArray(pixels.size)
        val hsv = FloatArray(3)
        for (i in pixels.indices) {
            toHsv(pixels[i], hsv)
            val hb = ((hsv[0] / 180.0) * HIST_H_BINS).toInt().coerceIn(0, HIST_H_BINS - 1)
            val sb = ((hsv[1] / 256.0) * HIST_S_BINS).toInt().coerceIn(0, HIST_S_BINS - 1)
            out[i] = hist[hb * HIST_S_BINS + sb]
        }
        return out
    }

    private fun expandWindow(box: PixelBox, width: Int, height: Int, scale: Double): IntArray {
        val cx = 0.5 * (box.x1 + box.x2)
        val cy = 0.5 * (box.y1 + box.y2)
        val bw = maxOf(8.0, (box.x2 - box.x1) * scale)
        val bh = maxOf(8.0, (box.y2 - box.y1) * scale)
        val nx1 = maxOf(0.0, cx - bw / 2.0).toInt()
        val ny1 = maxOf(0.0, cy - bh / 2.0).toInt()
        val nw = minOf(width - nx1, bw.toInt()).coerceAtLeast(1)
        val nh = minOf(height - ny1, bh.toInt()).coerceAtLeast(1)
        return intArrayOf(nx1, ny1, nw, nh)
    }

    private fun peakFallback(back: FloatArray, width: Int, height: Int, prev: PixelBox): PixelBox {
        val sw = maxOf(1, width / 4)
        val sh = maxOf(1, height / 4)
        var best = -1f
        var px = width / 2
        var py = height / 2
        for (sy in 0 until sh) {
            for (sx in 0 until sw) {
                val value = back[(sy * 4).coerceAtMost(height - 1) * width + (sx * 4).coerceAtMost(width - 1)]
                if (value > best) {
                    best = value
                    px = sx * 4
                    py = sy * 4
                }
            }
        }
        val bw = maxOf(16.0, prev.x2 - prev.x1)
        val bh = maxOf(16.0, prev.y2 - prev.y1)
        return PixelBox(
            maxOf(0.0, px - bw / 2),
            maxOf(0.0, py - bh / 2),
            minOf(width.toDouble(), px + bw / 2),
            minOf(height.toDouble(), py + bh / 2),
        )
    }

    private fun toHsv(argb: Int, out: FloatArray) {
        val r = (argb shr 16) and 0xFF
        val g = (argb shr 8) and 0xFF
        val b = argb and 0xFF
        val max = maxOf(r, g, b)
        val min = minOf(r, g, b)
        val delta = max - min
        val v = max.toFloat()
        val s = if (max == 0) 0f else delta * 255f / max
        val h = if (delta == 0) {
            0f
        } else if (max == r) {
            60f * (((g - b).toFloat() / delta + 6f) % 6f)
        } else if (max == g) {
            60f * ((b - r).toFloat() / delta + 2f)
        } else {
            60f * ((r - g).toFloat() / delta + 4f)
        }
        out[0] = (h / 2f).coerceIn(0f, 179f)
        out[1] = s.coerceIn(0f, 255f)
        out[2] = v
    }
}
