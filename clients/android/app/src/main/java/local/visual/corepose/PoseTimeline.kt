package local.visual.corepose

import kotlin.math.abs

data class PoseFrame(
    val tMs: Long,
    val poses: List<CocoPose>,
    val width: Int,
    val height: Int,
    val blaze33: List<BlazeJoint> = emptyList(),
    val bbox: BBox? = null,
)

object PoseTimeline {
    fun nearest(frames: List<PoseFrame>, tMs: Long): PoseFrame? {
        if (frames.isEmpty()) {
            return null
        }
        val i = frames.binarySearchBy(tMs) { it.tMs }
        if (i >= 0) {
            return frames[i]
        }
        val insert = -i - 1
        val lo = (insert - 1).coerceAtLeast(0)
        val hi = insert.coerceAtMost(frames.lastIndex)
        return if (abs(frames[lo].tMs - tMs) <= abs(frames[hi].tMs - tMs)) {
            frames[lo]
        } else {
            frames[hi]
        }
    }
}
