package local.visual.corepose

import com.google.mediapipe.tasks.components.containers.NormalizedLandmark

data class MappedPeople(
    val poses: List<CocoPose>,
    val blazePeople: List<List<BlazeJoint>>,
    val bboxes: List<BBox>,
)

object PoseMapper {
    fun fromLandmarks(
        poses: List<List<NormalizedLandmark>>,
        width: Int,
        height: Int,
        device: String,
    ): MappedPeople {
        val w = width.coerceAtLeast(1).toFloat()
        val h = height.coerceAtLeast(1).toFloat()
        val n = poses.size
        val flat = FloatArray(n * 33 * 4)
        val blazePeople = ArrayList<List<BlazeJoint>>(n)
        var o = 0
        for (person in poses) {
            val joints = ArrayList<BlazeJoint>(33)
            for (i in 0 until 33) {
                val lm = person.getOrNull(i)
                if (lm == null) {
                    joints.add(BlazeJoint(0f, 0f, 0f, 0f))
                    o += 4
                    continue
                }
                val x = lm.x() * w
                val y = lm.y() * h
                val z = lm.z() * w
                val vis = lm.visibility().orElse(1f)
                joints.add(BlazeJoint(x, y, z, vis))
                flat[o++] = x
                flat[o++] = y
                flat[o++] = z
                flat[o++] = vis
            }
            blazePeople.add(joints)
        }
        val json = CoreMap.fromBlaze33(flat, n, width.coerceAtLeast(1), height.coerceAtLeast(1), 0f, device)
        return MappedPeople(
            poses = CoreJson.poses(json),
            blazePeople = blazePeople,
            bboxes = CoreJson.bboxes(json),
        )
    }
}
