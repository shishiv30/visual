package local.visual.corepose

object PoseTrack {
    const val HIGH_SCORE = 55.0
    const val LOW_SCORE = 40.0
    const val MAX_GAP_MS = 400.0
    const val HOLD_MS = 200.0
    const val INTERP_CONF = 0.85f

    // Below this, one landmark (not necessarily the whole pose) is weak enough
    // that stabilizeWeakJoints will try to bridge it from neighbors before any
    // per-metric consumer has to gate it out. Above it, the joint is left alone
    // even though a metric's own, usually stricter, confidence gate may still
    // discount or drop it later. Distinct from SportsSignals.CONF_MIN, which
    // gates metric computation itself and is unaffected by this pass.
    const val JOINT_CONF_MIN = 0.35
    private const val BLAZE_N = 33

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

    /**
     * Bridge one landmark's short confidence dip from its own neighbors.
     *
     * [fillLowScore] already does this at the whole-pose level, keyed off the
     * frame's overall score. That leaves the common ski case unaddressed: the
     * torso tracks perfectly all the way through a turn but one ankle or foot
     * drops out for a few frames -- occluded by snow spray, motion blur, or a
     * self-occlusion at full flex -- while the rest of the skeleton stays
     * confident. A frame like that never triggers the whole-frame path (its
     * overall score is fine), so the weak joint used to sit at its raw, noisy
     * coordinates until a metric's own confidence gate dropped it or (the bug
     * this fixes) it became the "most extreme" sample and got shown to the
     * coach as evidence.
     *
     * This runs per landmark index, independently of every other joint, with
     * the exact same [MAX_GAP_MS]/[HOLD_MS] policy as the whole-frame version:
     * a short gap flanked by two well-tracked samples is linearly interpolated
     * between them; a gap open on only one side is held from that side,
     * decaying via [INTERP_CONF] so it is never mistaken for a fresh
     * measurement; a gap with no well-tracked anchor on either side (or longer
     * than [MAX_GAP_MS]) is left alone, since there is nothing real to
     * interpolate from. Every per-metric confidence gate downstream
     * (SportsSignals.CONF_MIN, the evidence-frame bar) still applies on top of
     * this -- it only gives those gates a better-populated series to gate
     * over, it does not replace them.
     *
     * Must run before [fillLowScore] in the pipeline, since it operates on a
     * different, finer granularity (per-landmark blaze33) than that pass
     * (which keys off the pose's overall keypoint-average score).
     */
    fun stabilizeWeakJoints(frames: List<PoseFrame>, confMin: Double = JOINT_CONF_MIN): List<PoseFrame> {
        val n = frames.size
        if (n < 2) {
            return frames
        }
        val out = frames.toMutableList()
        for (j in 0 until BLAZE_N) {
            val conf = DoubleArray(n) { i ->
                val joints = out[i].blaze33
                if (j < joints.size) joints[j].confidence.toDouble() else 0.0
            }
            var i = 0
            while (i < n) {
                if (conf[i] >= confMin) {
                    i += 1
                    continue
                }
                var k = i
                while (k < n && conf[k] < confMin) {
                    k += 1
                }
                val leftI = if (i > 0 && conf[i - 1] >= confMin) i - 1 else null
                val rightI = if (k < n && conf[k] >= confMin) k else null
                if (leftI != null && rightI != null) {
                    val tLeft = out[leftI].tMs.toDouble()
                    val tRight = out[rightI].tMs.toDouble()
                    if (tRight - tLeft in 0.0..MAX_GAP_MS && tRight > tLeft) {
                        val leftJoint = out[leftI].blaze33[j]
                        val rightJoint = out[rightI].blaze33[j]
                        val span = tRight - tLeft
                        for (m in i until k) {
                            val joints = out[m].blaze33
                            if (j >= joints.size) continue
                            val w = ((out[m].tMs - tLeft) / span).toFloat()
                            out[m] = out[m].copy(blaze33 = replaceJoint(joints, j, lerpJoint(leftJoint, rightJoint, w)))
                        }
                    }
                } else if (leftI != null) {
                    val tLeft = out[leftI].tMs.toDouble()
                    val leftJoint = out[leftI].blaze33[j]
                    for (m in i until k) {
                        if (out[m].tMs - tLeft <= HOLD_MS) {
                            val joints = out[m].blaze33
                            if (j < joints.size) {
                                out[m] = out[m].copy(blaze33 = replaceJoint(joints, j, holdJoint(leftJoint)))
                            }
                        }
                    }
                } else if (rightI != null) {
                    val tRight = out[rightI].tMs.toDouble()
                    val rightJoint = out[rightI].blaze33[j]
                    for (m in i until k) {
                        if (tRight - out[m].tMs <= HOLD_MS) {
                            val joints = out[m].blaze33
                            if (j < joints.size) {
                                out[m] = out[m].copy(blaze33 = replaceJoint(joints, j, holdJoint(rightJoint)))
                            }
                        }
                    }
                }
                i = k
            }
        }
        return out
    }

    private fun replaceJoint(joints: List<BlazeJoint>, index: Int, value: BlazeJoint): List<BlazeJoint> {
        val out = joints.toMutableList()
        out[index] = value
        return out
    }

    private fun lerpJoint(left: BlazeJoint, right: BlazeJoint, w: Float): BlazeJoint {
        return BlazeJoint(
            lerp(left.x, right.x, w),
            lerp(left.y, right.y, w),
            lerp(left.z, right.z, w),
            minOf(1f, minOf(left.confidence, right.confidence) * INTERP_CONF),
        )
    }

    private fun holdJoint(anchor: BlazeJoint): BlazeJoint {
        return BlazeJoint(anchor.x, anchor.y, anchor.z, minOf(1f, anchor.confidence * INTERP_CONF))
    }
}
