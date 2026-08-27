package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoreJsonTest {
    @Test
    fun parsesCoco17Pose() {
        val json = """
            {"schema_version":"0.1.0","error":null,"poses":[
              {"skeleton":"coco_17","score":0.9,"detection_index":0,"keypoints":[
                {"name":"nose","x":10,"y":20,"z":0,"confidence":0.9},
                {"name":"left_eye","x":12,"y":18,"z":0,"confidence":0.8},
                {"name":"right_eye","x":8,"y":18,"z":0,"confidence":0.8},
                {"name":"left_ear","x":14,"y":18,"z":0,"confidence":0.7},
                {"name":"right_ear","x":6,"y":18,"z":0,"confidence":0.7},
                {"name":"left_shoulder","x":20,"y":40,"z":0,"confidence":0.9},
                {"name":"right_shoulder","x":0,"y":40,"z":0,"confidence":0.9},
                {"name":"left_elbow","x":22,"y":60,"z":0,"confidence":0.8},
                {"name":"right_elbow","x":-2,"y":60,"z":0,"confidence":0.8},
                {"name":"left_wrist","x":24,"y":80,"z":0,"confidence":0.7},
                {"name":"right_wrist","x":-4,"y":80,"z":0,"confidence":0.7},
                {"name":"left_hip","x":18,"y":90,"z":0,"confidence":0.9},
                {"name":"right_hip","x":2,"y":90,"z":0,"confidence":0.9},
                {"name":"left_knee","x":18,"y":120,"z":0,"confidence":0.8},
                {"name":"right_knee","x":2,"y":120,"z":0,"confidence":0.8},
                {"name":"left_ankle","x":18,"y":150,"z":0,"confidence":0.7},
                {"name":"right_ankle","x":2,"y":150,"z":0,"confidence":0.7}
              ]}
            ]}
        """.trimIndent()
        val poses = CoreJson.poses(json)
        assertEquals(1, poses.size)
        assertEquals(17, poses[0].keypoints.size)
        assertEquals(10f, poses[0].keypoints[0].x)
        assertEquals(20f, poses[0].keypoints[0].y)
        assertEquals(0.9f, poses[0].keypoints[0].confidence)
    }

    @Test
    fun errorYieldsNoPoses() {
        val json =
            """{"error":{"code":"NO_PERSON","message":"no detections"},"poses":[]}"""
        assertTrue(CoreJson.poses(json).isEmpty())
        assertTrue(CoreJson.bboxes(json).isEmpty())
    }

    @Test
    fun parsesBbox() {
        val json = """{"detections":[{"bbox_xyxy":[1,2,30,40]}]}"""
        val boxes = CoreJson.bboxes(json)
        assertEquals(1, boxes.size)
        assertEquals(1f, boxes[0].x1)
        assertEquals(40f, boxes[0].y2)
    }
}
