package local.visual.corepose

object PoseFilter {
    const val MAX_BBOX_ASPECT = 3.2
    const val MAX_HEIGHT_OVER_SHOULDER = 4.5
    const val MAX_FULL_HEIGHT_FRAC = 0.90
    const val MIN_FULL_WIDTH_FRAC = 0.35
    const val MIN_SHOULDER_VIS = 0.35f
    const val MIN_HEAD_VIS = 0.25f
    // Higher alpha = more weight on the current detection = less positional lag.
    // 0.45 caused visible skeleton drift on fast skier turns; 0.65 is more responsive.
    const val EMA_ALPHA = 0.65f
    // When a confident joint jumps more than this fraction of torso length, bypass
    // EMA entirely so the skeleton snaps to the new position instead of drifting.
    const val EMA_SNAP_DIST = 0.30f
    const val EMA_SNAP_CONF = 0.60f
    const val CROP_PAD = 0.28
    const val TALL_CROP_KEEP_BOTTOM = 0.55

    const val NOSE = 0
    const val LEFT_EYE = 1
    const val RIGHT_EYE = 2
    const val LEFT_EAR = 3
    const val RIGHT_EAR = 4
    const val LEFT_SHOULDER = 5
    const val RIGHT_SHOULDER = 6
    const val LEFT_HIP = 11
    const val RIGHT_HIP = 12

    fun bboxIou(a: BBox, b: BBox): Double {
        val ix1 = maxOf(a.x1, b.x1)
        val iy1 = maxOf(a.y1, b.y1)
        val ix2 = minOf(a.x2, b.x2)
        val iy2 = minOf(a.y2, b.y2)
        val inter = maxOf(0f, ix2 - ix1) * maxOf(0f, iy2 - iy1)
        val areaA = maxOf(0f, a.x2 - a.x1) * maxOf(0f, a.y2 - a.y1)
        val areaB = maxOf(0f, b.x2 - b.x1) * maxOf(0f, b.y2 - b.y1)
        val union = areaA + areaB - inter
        if (union <= 0f) {
            return 0.0
        }
        return inter / union.toDouble()
    }

    fun pickPrimary(mapped: MappedPeople, prev: BBox?): MappedPeople {
        if (mapped.poses.size <= 1) {
            return mapped
        }
        var bestI = 0
        var best = -1.0
        for (i in mapped.poses.indices) {
            var score = mapped.poses[i].keypoints.map { it.confidence }.average()
            val box = mapped.bboxes.getOrNull(i)
            if (box != null && prev != null) {
                score += bboxIou(box, prev)
            }
            if (score > best) {
                best = score
                bestI = i
            }
        }
        return MappedPeople(
            poses = listOf(mapped.poses[bestI]),
            blazePeople = listOf(mapped.blazePeople.getOrNull(bestI).orEmpty()),
            bboxes = listOfNotNull(mapped.bboxes.getOrNull(bestI)),
        )
    }

    fun isPlausible(pose: CocoPose, box: BBox, frameW: Int, frameH: Int): Boolean {
        val width = maxOf(1.0, (box.x2 - box.x1).toDouble())
        val height = maxOf(0.0, (box.y2 - box.y1).toDouble())
        if (height / width > MAX_BBOX_ASPECT) {
            return false
        }
        if (height > MAX_FULL_HEIGHT_FRAC * frameH && width < MIN_FULL_WIDTH_FRAC * frameW) {
            return false
        }
        val leftS = pose.keypoints.getOrNull(LEFT_SHOULDER)
        val rightS = pose.keypoints.getOrNull(RIGHT_SHOULDER)
        if (
            leftS != null &&
            rightS != null &&
            leftS.confidence >= MIN_SHOULDER_VIS &&
            rightS.confidence >= MIN_SHOULDER_VIS
        ) {
            val shoulder = kotlin.math.abs(leftS.x - rightS.x)
            if (shoulder > 1f && height / shoulder > MAX_HEIGHT_OVER_SHOULDER) {
                return false
            }
        }
        val headIds = intArrayOf(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR)
        var headVis = 0.0
        var nHead = 0
        for (id in headIds) {
            val kp = pose.keypoints.getOrNull(id) ?: continue
            headVis += kp.confidence
            nHead += 1
        }
        if (nHead > 0 && (headVis / nHead) < MIN_HEAD_VIS) {
            return false
        }
        return true
    }

    fun isPlausible(mapped: MappedPeople, frameW: Int, frameH: Int): Boolean {
        val pose = mapped.poses.firstOrNull() ?: return false
        val box = mapped.bboxes.firstOrNull() ?: return false
        return isPlausible(pose, box, frameW, frameH)
    }

    fun cropDisagreesWithPrev(prev: MappedPeople?, curr: MappedPeople): Boolean {
        if (prev == null || prev.poses.isEmpty() || curr.poses.isEmpty()) {
            return false
        }
        val tPrev = torsoLength(prev.poses[0])
        val tCurr = torsoLength(curr.poses[0])
        if (tPrev > 1.0 && tCurr / tPrev < 0.75) {
            return true
        }
        return relativeJump(prev.poses[0], curr.poses[0]) > 0.35
    }

    fun cropBoxForRetry(bbox: BBox, frameW: Int, frameH: Int): PixelBox {
        val bw = maxOf(1.0, (bbox.x2 - bbox.x1).toDouble())
        val bh = maxOf(1.0, (bbox.y2 - bbox.y1).toDouble())
        val y1 = bbox.y1 + bh * (1.0 - TALL_CROP_KEEP_BOTTOM)
        val padX = bw * CROP_PAD
        val padY = bh * CROP_PAD * TALL_CROP_KEEP_BOTTOM
        val nx1 = maxOf(0.0, bbox.x1 - padX)
        val ny1 = maxOf(0.0, y1 - padY)
        val nx2 = minOf(frameW.toDouble(), bbox.x2 + padX)
        val ny2 = minOf(frameH.toDouble(), bbox.y2 + padY)
        if (nx2 <= nx1 || ny2 <= ny1) {
            return PixelBox(0.0, 0.0, frameW.toDouble(), frameH.toDouble())
        }
        return PixelBox(nx1, ny1, nx2, ny2)
    }

    fun emaSmooth(prev: MappedPeople?, curr: MappedPeople): MappedPeople {
        if (prev == null || prev.poses.isEmpty() || curr.poses.isEmpty()) {
            return curr
        }
        val prevKps = prev.poses[0].keypoints
        val currKps = curr.poses[0].keypoints
        if (prevKps.size != currKps.size) {
            return curr
        }
        val torso = torsoLength(curr.poses[0]).toFloat().coerceAtLeast(1f)
        val mixed = currKps.mapIndexed { i, b ->
            val a = prevKps[i]
            if (b.confidence < 0.2f) {
                CocoKeypoint(a.x, a.y, b.confidence)
            } else {
                val dx = b.x - a.x
                val dy = b.y - a.y
                val dist = kotlin.math.sqrt((dx * dx + dy * dy).toDouble()).toFloat()
                // Snap to raw detection when the joint moves fast and confidence is high,
                // so the skeleton follows sudden movements instead of drifting behind.
                val alpha = if (b.confidence >= EMA_SNAP_CONF && dist / torso > EMA_SNAP_DIST) {
                    1f
                } else {
                    EMA_ALPHA
                }
                CocoKeypoint(
                    alpha * b.x + (1f - alpha) * a.x,
                    alpha * b.y + (1f - alpha) * a.y,
                    b.confidence,
                )
            }
        }
        val box = if (prev.bboxes.isNotEmpty() && curr.bboxes.isNotEmpty()) {
            val px = prev.bboxes[0]
            val cx = curr.bboxes[0]
            BBox(
                EMA_ALPHA * cx.x1 + (1f - EMA_ALPHA) * px.x1,
                EMA_ALPHA * cx.y1 + (1f - EMA_ALPHA) * px.y1,
                EMA_ALPHA * cx.x2 + (1f - EMA_ALPHA) * px.x2,
                EMA_ALPHA * cx.y2 + (1f - EMA_ALPHA) * px.y2,
            )
        } else {
            curr.bboxes.firstOrNull()
        }
        val blaze = if (prev.blazePeople.isNotEmpty() && curr.blazePeople.isNotEmpty()) {
            val pa = prev.blazePeople[0]
            val pb = curr.blazePeople[0]
            if (pa.size == pb.size) {
                pb.mapIndexed { i, b ->
                    val a = pa[i]
                    if (b.confidence < 0.2f) {
                        BlazeJoint(a.x, a.y, a.z, b.confidence)
                    } else {
                        BlazeJoint(
                            EMA_ALPHA * b.x + (1f - EMA_ALPHA) * a.x,
                            EMA_ALPHA * b.y + (1f - EMA_ALPHA) * a.y,
                            EMA_ALPHA * b.z + (1f - EMA_ALPHA) * a.z,
                            b.confidence,
                        )
                    }
                }
            } else {
                pb
            }
        } else {
            curr.blazePeople.firstOrNull().orEmpty()
        }
        return MappedPeople(
            poses = listOf(CocoPose(mixed)),
            blazePeople = listOf(blaze),
            bboxes = listOfNotNull(box),
        )
    }

    fun torsoLength(pose: CocoPose): Double {
        val sh = pairMid(pose, LEFT_SHOULDER, RIGHT_SHOULDER) ?: return 0.0
        val hp = pairMid(pose, LEFT_HIP, RIGHT_HIP) ?: return 0.0
        val dx = sh.first - hp.first
        val dy = sh.second - hp.second
        return kotlin.math.sqrt(dx * dx + dy * dy)
    }

    private fun relativeJump(a: CocoPose, b: CocoPose): Double {
        val am = pairMid(a, LEFT_HIP, RIGHT_HIP) ?: pairMid(a, LEFT_SHOULDER, RIGHT_SHOULDER)
        val bm = pairMid(b, LEFT_HIP, RIGHT_HIP) ?: pairMid(b, LEFT_SHOULDER, RIGHT_SHOULDER)
        if (am == null || bm == null) {
            return 0.0
        }
        val dx = am.first - bm.first
        val dy = am.second - bm.second
        val scale = maxOf(torsoLength(a), torsoLength(b), 1.0)
        return kotlin.math.sqrt(dx * dx + dy * dy) / scale
    }

    private fun pairMid(pose: CocoPose, left: Int, right: Int): Pair<Double, Double>? {
        val a = pose.keypoints.getOrNull(left) ?: return null
        val b = pose.keypoints.getOrNull(right) ?: return null
        if (a.confidence < MIN_SHOULDER_VIS || b.confidence < MIN_SHOULDER_VIS) {
            return null
        }
        return (a.x + b.x) / 2.0 to (a.y + b.y) / 2.0
    }
}
