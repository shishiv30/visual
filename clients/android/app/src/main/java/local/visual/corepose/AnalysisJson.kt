package local.visual.corepose

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

object AnalysisJson {
    fun save(file: File, clipId: String, frames: List<PoseFrame>) {
        file.parentFile?.mkdirs()
        val arr = JSONArray()
        for (frame in frames) {
            val poses = JSONArray()
            for (pose in frame.poses) {
                val kps = JSONArray()
                for (kp in pose.keypoints) {
                    kps.put(
                        JSONObject()
                            .put("x", kp.x.toDouble())
                            .put("y", kp.y.toDouble())
                            .put("confidence", kp.confidence.toDouble()),
                    )
                }
                poses.put(JSONObject().put("keypoints", kps))
            }
            val blaze = JSONArray()
            for (joint in frame.blaze33) {
                blaze.put(
                    JSONObject()
                        .put("x", joint.x.toDouble())
                        .put("y", joint.y.toDouble())
                        .put("z", joint.z.toDouble())
                        .put("confidence", joint.confidence.toDouble()),
                )
            }
            val obj = JSONObject()
                .put("t_ms", frame.tMs)
                .put("width", frame.width)
                .put("height", frame.height)
                .put("poses", poses)
                .put("blaze33", blaze)
            if (frame.bbox == null) {
                obj.put("bbox", JSONObject.NULL)
            } else {
                obj.put(
                    "bbox",
                    JSONArray()
                        .put(frame.bbox.x1.toDouble())
                        .put(frame.bbox.y1.toDouble())
                        .put(frame.bbox.x2.toDouble())
                        .put(frame.bbox.y2.toDouble()),
                )
            }
            arr.put(obj)
        }
        file.writeText(
            JSONObject()
                .put("clip_id", clipId)
                .put("frames", arr)
                .toString(),
            Charsets.UTF_8,
        )
    }

    fun load(file: File): List<PoseFrame> {
        if (!file.isFile) {
            return emptyList()
        }
        val root = JSONObject(file.readText(Charsets.UTF_8))
        val arr = root.optJSONArray("frames") ?: return emptyList()
        val frames = ArrayList<PoseFrame>(arr.length())
        for (i in 0 until arr.length()) {
            val obj = arr.optJSONObject(i) ?: continue
            val posesArr = obj.optJSONArray("poses") ?: JSONArray()
            val poses = ArrayList<CocoPose>(posesArr.length())
            for (p in 0 until posesArr.length()) {
                val poseObj = posesArr.optJSONObject(p) ?: continue
                val kps = poseObj.optJSONArray("keypoints") ?: continue
                val points = ArrayList<CocoKeypoint>(kps.length())
                for (k in 0 until kps.length()) {
                    val kp = kps.optJSONObject(k) ?: continue
                    points.add(
                        CocoKeypoint(
                            x = kp.optDouble("x").toFloat(),
                            y = kp.optDouble("y").toFloat(),
                            confidence = kp.optDouble("confidence").toFloat(),
                        ),
                    )
                }
                if (points.isNotEmpty()) {
                    poses.add(CocoPose(points))
                }
            }
            val blazeArr = obj.optJSONArray("blaze33") ?: JSONArray()
            val blaze = ArrayList<BlazeJoint>(blazeArr.length())
            for (j in 0 until blazeArr.length()) {
                val joint = blazeArr.optJSONObject(j) ?: continue
                blaze.add(
                    BlazeJoint(
                        x = joint.optDouble("x").toFloat(),
                        y = joint.optDouble("y").toFloat(),
                        z = joint.optDouble("z").toFloat(),
                        confidence = joint.optDouble("confidence").toFloat(),
                    ),
                )
            }
            val boxArr = obj.optJSONArray("bbox")
            val bbox = if (boxArr != null && boxArr.length() >= 4) {
                BBox(
                    boxArr.optDouble(0).toFloat(),
                    boxArr.optDouble(1).toFloat(),
                    boxArr.optDouble(2).toFloat(),
                    boxArr.optDouble(3).toFloat(),
                )
            } else {
                null
            }
            frames.add(
                PoseFrame(
                    tMs = obj.optLong("t_ms"),
                    poses = poses,
                    width = obj.optInt("width", 1).coerceAtLeast(1),
                    height = obj.optInt("height", 1).coerceAtLeast(1),
                    blaze33 = blaze,
                    bbox = bbox,
                ),
            )
        }
        return frames
    }

    fun toAssessFrames(frames: List<PoseFrame>): List<AssessFrame> {
        return frames.map { frame ->
            AssessFrame(tMs = frame.tMs.toDouble(), blaze33 = frame.blaze33)
        }
    }
}
