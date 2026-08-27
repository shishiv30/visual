package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PersonRoiTest {
    @Test
    fun denormBoxScalesToPixels() {
        val box = PersonRoi.denormBox(NormBox(0.1f, 0.2f, 0.4f, 0.8f), 200, 100)
        assertEquals(20.0, box.x1, 0.01)
        assertEquals(20.0, box.y1, 0.01)
        assertEquals(80.0, box.x2, 0.01)
        assertEquals(80.0, box.y2, 0.01)
    }

    @Test
    fun cropForPosePadsAndReportsOrigin() {
        val crop = PersonRoi.cropRect(PixelBox(80.0, 60.0, 140.0, 160.0), 320, 240, pad = 0.35, minSide = 32)
        assertTrue(crop.ox < 80)
        assertTrue(crop.oy < 60)
        assertTrue(crop.x2 > 140)
        assertTrue(crop.y2 > 160)
        assertEquals(1.0, crop.scale, 0.001)
    }

    @Test
    fun cropUpscalesShortSide() {
        val crop = PersonRoi.cropRect(PixelBox(10.0, 10.0, 30.0, 40.0), 320, 240, pad = 0.0, minSide = 256)
        assertTrue(crop.scale > 1.0)
        assertEquals(256.0 / 20.0, crop.scale, 0.05)
    }

    @Test
    fun remapUndoesCropScale() {
        val (x, y) = PersonRoi.remapPoint(12.0, 14.0, ox = 59, oy = 25, scale = 2.0)
        assertEquals(12.0 / 2.0 + 59, x, 0.01)
        assertEquals(14.0 / 2.0 + 25, y, 0.01)
    }

    @Test
    fun histSearchFindsRedBlock() {
        val image = redJacket(0)
        val box = PixelBox(80.0, 60.0, 140.0, 160.0)
        val hist = PersonRoi.buildHist(image.pixels, 320, 240, box)
        val found = PersonRoi.search(image.pixels, 320, 240, hist, box)
        val cx = 0.5 * (found.x1 + found.x2)
        val cy = 0.5 * (found.y1 + found.y2)
        assertTrue(cx > 70 && cx < 150)
        assertTrue(cy > 50 && cy < 170)
    }

    @Test
    fun histSearchFollowsShiftedBlock() {
        val hist = PersonRoi.buildHist(redJacket(0).pixels, 320, 240, PixelBox(80.0, 60.0, 140.0, 160.0))
        val found = PersonRoi.search(
            redJacket(40).pixels,
            320,
            240,
            hist,
            PixelBox(80.0, 60.0, 140.0, 160.0),
        )
        val cx = 0.5 * (found.x1 + found.x2)
        assertTrue(cx > 100)
    }

    private fun redJacket(shiftX: Int): ArgbImage {
        val pixels = IntArray(320 * 240) { 0xFFFFFFFF.toInt() }
        for (y in 60 until 160) {
            for (x in (80 + shiftX) until (140 + shiftX)) {
                pixels[y * 320 + x] = 0xFFDC0000.toInt()
            }
        }
        return ArgbImage(pixels)
    }

    private data class ArgbImage(val pixels: IntArray)
}
