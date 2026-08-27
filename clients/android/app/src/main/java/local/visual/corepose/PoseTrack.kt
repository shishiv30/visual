package local.visual.corepose

object PoseTrack {
    const val HIGH_SCORE = 55.0
    const val LOW_SCORE = 40.0
    const val MAX_GAP_MS = 400.0
    const val HOLD_MS = 200.0
    const val INTERP_CONF = 0.85f

    fun fillLowScore(frames: List<PoseFrame>): List<PoseFrame> {
        if (frames.size <= 1) {
            return frames
        }
        val scores = frames.map { frameScore(it) }.toMutableList()
        val out = frames.toMutableList()
        var i = 0
        val n = out.size
        while (i < n) {
            if (scores[i] >= LOW_SCORE) {
                i += 1
                continue
            }
            var j = i
            while (j < n && scores[j] < LOW_SCORE) {
                j += 1
            }
            val leftI = nearestHigh(scores, i - 1, -1)
            val rightI = nearestHigh(scores, j, 1)
            if (leftI != null && rightI != null) {
                val tLeft = out[leftI].tMs.toDouble()
                val tRight = out[rightI].tMs.toDouble()
                if (tRight - tLeft in 0.0..MAX_GAP_MS) {
                    val span = tRight - tLeft
                    for (k in i until j) {
                        val w = ((out[k].tMs - tLeft) / span).toFloat()
                        out[k] = lerpFrame(out[leftI], out[rightI], out[k], w)
                    }
                }
            } else if (leftI != null) {
                for (k in i until j) {
                    if (out[k].tMs - out[leftI].tMs <= HOLD_MS) {
                        out[k] = holdFrame(out[leftI], out[k])
                    }
                }
            } else if (rightI != null) {
                for (k in i until j) {
                    if (out[rightI].tMs - out[k].tMs <= HOLD_MS) {
                        out[k] = holdFrame(out[rightI], out[k])
                    }
                }
            }
            i = j
        }
        return out
    }

    fun frameScore(frame: PoseFrame): Double {
        val pose = frame.poses.firstOrNull() ?: return 0.0
        val vis = pose.keypoints.map { it.confidence }
        if (vis.isEmpty()) {
            return 0.0
        }
        return (vis.average() * 100.0).coerceIn(0.0, 100.0)
    }

    private fun nearestHigh(scores: List<Double>, start: Int, step: Int): Int? {
        var i = start
        while (i in scores.indices) {
            if (scores[i] >= HIGH_SCORE) {
                return i
            }
            i += step
        }
        return null
    }

    private fun lerpFrame(left: PoseFrame, right: PoseFrame, curr: PoseFrame, w: Float): PoseFrame {
        val lp = left.poses.firstOrNull() ?: return curr
        val rp = right.poses.firstOrNull() ?: return curr
        val pose = CocoPose(
            lp.keypoints.mapIndexed { i, a ->
                val b = rp.keypoints.getOrNull(i) ?: a
                CocoKeypoint(
                    lerp(a.x, b.x, w),
                    lerp(a.y, b.y, w),
                    minOf(a.confidence, b.confidence) * INTERP_CONF,
                )
            },
        )
        val blaze = if (left.blaze33.size == right.blaze33.size && left.blaze33.isNotEmpty()) {
            left.blaze33.mapIndexed { i, a ->
                val b = right.blaze33[i]
                BlazeJoint(
                    lerp(a.x, b.x, w),
                    lerp(a.y, b.y, w),
                    lerp(a.z, b.z, w),
                    minOf(a.confidence, b.confidence) * INTERP_CONF,
                )
            }
        } else {
            left.blaze33
        }
        val box = if (left.bbox != null && right.bbox != null) {
            BBox(
                lerp(left.bbox.x1, right.bbox.x1, w),
                lerp(left.bbox.y1, right.bbox.y1, w),
                lerp(left.bbox.x2, right.bbox.x2, w),
                lerp(left.bbox.y2, right.bbox.y2, w),
            )
        } else {
            left.bbox ?: right.bbox
        }
        return curr.copy(poses = listOf(pose), blaze33 = blaze, bbox = box)
    }

    private fun holdFrame(anchor: PoseFrame, curr: PoseFrame): PoseFrame {
        val pose = anchor.poses.firstOrNull() ?: return curr
        return curr.copy(
            poses = listOf(
                CocoPose(pose.keypoints.map { kp -> CocoKeypoint(kp.x, kp.y, kp.confidence * INTERP_CONF) }),
            ),
            blaze33 = anchor.blaze33.map { j -> BlazeJoint(j.x, j.y, j.z, j.confidence * INTERP_CONF) },
            bbox = anchor.bbox,
        )
    }

    private fun lerp(a: Float, b: Float, w: Float): Float = (1f - w) * a + w * b
}
