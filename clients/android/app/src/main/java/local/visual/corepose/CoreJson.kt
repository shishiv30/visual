package local.visual.corepose

import org.json.JSONObject

object CoreJson {
    fun poses(json: String): List<CocoPose> {
        val root = JSONObject(json)
        if (!root.isNull("error")) {
            return emptyList()
        }
        val arr = root.optJSONArray("poses") ?: return emptyList()
        val out = ArrayList<CocoPose>(arr.length())
        for (i in 0 until arr.length()) {
            val poseObj = arr.optJSONObject(i) ?: continue
            val kps = poseObj.optJSONArray("keypoints") ?: continue
            val points = ArrayList<CocoKeypoint>(kps.length())
            for (k in 0 until kps.length()) {
                val kp = kps.optJSONObject(k) ?: continue
                points.add(
                    CocoKeypoint(
                        x = kp.optDouble("x", 0.0).toFloat(),
                        y = kp.optDouble("y", 0.0).toFloat(),
                        confidence = kp.optDouble("confidence", 0.0).toFloat(),
                    ),
                )
            }
            if (points.isNotEmpty()) {
                out.add(CocoPose(points))
            }
        }
        return out
    }

    fun bboxes(json: String): List<BBox> {
        val root = JSONObject(json)
        if (!root.isNull("error")) {
            return emptyList()
        }
        val arr = root.optJSONArray("detections") ?: return emptyList()
        val out = ArrayList<BBox>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            val box = item.optJSONArray("bbox_xyxy") ?: continue
            if (box.length() < 4) {
                continue
            }
            out.add(
                BBox(
                    box.optDouble(0).toFloat(),
                    box.optDouble(1).toFloat(),
                    box.optDouble(2).toFloat(),
                    box.optDouble(3).toFloat(),
                ),
            )
        }
        return out
    }
}
