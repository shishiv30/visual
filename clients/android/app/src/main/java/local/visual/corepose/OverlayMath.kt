package local.visual.corepose

data class CocoKeypoint(
    val x: Float,
    val y: Float,
    val confidence: Float,
)

data class CocoPose(
    val keypoints: List<CocoKeypoint>,
)

object OverlayMath {
    const val MIN_VIS = 0.3f

    val COCO17_EDGES: List<Pair<Int, Int>> = listOf(
        0 to 1,
        0 to 2,
        1 to 3,
        2 to 4,
        5 to 6,
        5 to 7,
        7 to 9,
        6 to 8,
        8 to 10,
        5 to 11,
        6 to 12,
        11 to 12,
        11 to 13,
        13 to 15,
        12 to 14,
        14 to 16,
    )

    data class Segment(
        val x1: Float,
        val y1: Float,
        val x2: Float,
        val y2: Float,
    )

    data class Joint(
        val x: Float,
        val y: Float,
    )

    data class Cover(
        val scale: Float,
        val dx: Float,
        val dy: Float,
    )

    fun cover(srcW: Int, srcH: Int, viewW: Int, viewH: Int): Cover {
        if (srcW <= 0 || srcH <= 0 || viewW <= 0 || viewH <= 0) {
            return Cover(1f, 0f, 0f)
        }
        val scale = maxOf(viewW.toFloat() / srcW, viewH.toFloat() / srcH)
        val dx = (viewW - srcW * scale) / 2f
        val dy = (viewH - srcH * scale) / 2f
        return Cover(scale, dx, dy)
    }

    fun contain(srcW: Int, srcH: Int, viewW: Int, viewH: Int): Cover {
        if (srcW <= 0 || srcH <= 0 || viewW <= 0 || viewH <= 0) {
            return Cover(1f, 0f, 0f)
        }
        val scale = minOf(viewW.toFloat() / srcW, viewH.toFloat() / srcH)
        val dx = (viewW - srcW * scale) / 2f
        val dy = (viewH - srcH * scale) / 2f
        return Cover(scale, dx, dy)
    }

    fun mapFillCenter(
        x: Float,
        y: Float,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
    ): Pair<Float, Float> {
        val cover = cover(srcW, srcH, viewW, viewH)
        return x * cover.scale + cover.dx to y * cover.scale + cover.dy
    }

    fun unmapFillCenter(
        x: Float,
        y: Float,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
    ): Pair<Float, Float> {
        val cover = cover(srcW, srcH, viewW, viewH)
        return (x - cover.dx) / cover.scale to (y - cover.dy) / cover.scale
    }

    fun mapContain(
        x: Float,
        y: Float,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
    ): Pair<Float, Float> {
        val box = contain(srcW, srcH, viewW, viewH)
        return x * box.scale + box.dx to y * box.scale + box.dy
    }

    fun unmapContain(
        x: Float,
        y: Float,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
    ): Pair<Float, Float> {
        val box = contain(srcW, srcH, viewW, viewH)
        return (x - box.dx) / box.scale to (y - box.dy) / box.scale
    }

    fun mapPoint(
        x: Float,
        y: Float,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
        letterbox: Boolean,
    ): Pair<Float, Float> {
        return if (letterbox) {
            mapContain(x, y, srcW, srcH, viewW, viewH)
        } else {
            mapFillCenter(x, y, srcW, srcH, viewW, viewH)
        }
    }

    fun visibleJoints(
        pose: CocoPose,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
        letterbox: Boolean = false,
    ): List<Joint> {
        return pose.keypoints.mapNotNull { kp ->
            if (kp.confidence < MIN_VIS) {
                null
            } else {
                val (x, y) = mapPoint(kp.x, kp.y, srcW, srcH, viewW, viewH, letterbox)
                Joint(x, y)
            }
        }
    }

    fun visibleSegments(
        pose: CocoPose,
        srcW: Int,
        srcH: Int,
        viewW: Int,
        viewH: Int,
        letterbox: Boolean = false,
    ): List<Segment> {
        if (pose.keypoints.size < 17) {
            return emptyList()
        }
        return COCO17_EDGES.mapNotNull { (a, b) ->
            val pa = pose.keypoints[a]
            val pb = pose.keypoints[b]
            if (pa.confidence < MIN_VIS || pb.confidence < MIN_VIS) {
                null
            } else {
                val (x1, y1) = mapPoint(pa.x, pa.y, srcW, srcH, viewW, viewH, letterbox)
                val (x2, y2) = mapPoint(pb.x, pb.y, srcW, srcH, viewW, viewH, letterbox)
                Segment(x1, y1, x2, y2)
            }
        }
    }

    fun bboxFromPose(pose: CocoPose): BBox? {
        val pts = pose.keypoints.filter { it.confidence >= MIN_VIS }
        if (pts.isEmpty()) {
            return null
        }
        return BBox(
            pts.minOf { it.x },
            pts.minOf { it.y },
            pts.maxOf { it.x },
            pts.maxOf { it.y },
        )
    }
}
