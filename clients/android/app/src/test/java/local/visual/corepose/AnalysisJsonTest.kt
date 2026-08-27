package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

class AnalysisJsonTest {
    @Test
    fun roundTripFrames() {
        val dir = File.createTempFile("visual-an", "").also { it.delete(); it.mkdirs() }
        try {
            val file = File(dir, "analysis.json")
            val frames = listOf(
                PoseFrame(
                    100,
                    listOf(CocoPose(listOf(CocoKeypoint(1f, 2f, 0.9f)))),
                    1280,
                    720,
                    blaze33 = listOf(BlazeJoint(1f, 2f, 0f, 0.9f)),
                    bbox = BBox(0f, 0f, 10f, 20f),
                ),
            )
            AnalysisJson.save(file, "c1", frames)
            val loaded = AnalysisJson.load(file)
            assertEquals(1, loaded.size)
            assertEquals(100L, loaded[0].tMs)
            assertEquals(1280, loaded[0].width)
            assertEquals(0.9f, loaded[0].poses[0].keypoints[0].confidence, 0.01f)
            assertEquals(1, loaded[0].blaze33.size)
            assertEquals(10f, loaded[0].bbox?.x2)
        } finally {
            dir.deleteRecursively()
        }
    }
}
