package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.File

class LibraryTest {
    private fun tempDir(): File {
        val dir = File.createTempFile("visual-lib", "")
        dir.delete()
        dir.mkdirs()
        return dir
    }

    @Test
    fun formatDuration() {
        assertEquals("1:07", Library.formatDurationMs(67_000))
        assertEquals("0:00", Library.formatDurationMs(0))
        assertEquals("--", Library.formatDurationMs(1200, image = true))
        assertEquals(120_000L, Library.MAX_MS)
        assertEquals(120_000L, VideoPose.MAX_MS)
    }

    @Test
    fun playWindowUsesInOut() {
        val meta = ClipMeta(
            clipId = "a",
            createdAt = "t",
            displayName = "n",
            durationMs = 10_000,
            playStartMs = 1000,
            playEndMs = 4000,
        )
        assertEquals(1000L to 4000L, Library.playWindowMs(meta))
    }

    @Test
    fun playWindowReadsFloatingPointJson() {
        val dir = tempDir()
        try {
            val lib = Library(dir)
            val folder = lib.clipDir("clip-f")
            folder.mkdirs()
            File(folder, "meta.json").writeText(
                """
                {"clip_id":"clip-f","created_at":"t","display_name":"n","duration_ms":20000,
                 "play_start_ms":10500.4,"play_end_ms":18000.9,"kind":"video","status":"done"}
                """.trimIndent(),
            )
            val loaded = lib.loadMeta("clip-f")
            assertEquals(10500, loaded.playStartMs)
            assertEquals(18000, loaded.playEndMs)
            assertEquals(10500L to 18000L, Library.playWindowMs(loaded))
        } finally {
            dir.deleteRecursively()
        }
    }

    @Test
    fun jsonRoundTrip() {
        val dir = tempDir()
        try {
            val lib = Library(dir)
            val meta = ClipMeta(
                clipId = "clip-1",
                createdAt = "2026-08-25T21:45:00-05:00",
                displayName = "08/25/2026-21:45",
                durationMs = 83400,
                width = 1280,
                height = 720,
                status = ClipStatus.PENDING,
                seedBox = NormBox(0.1f, 0.2f, 0.8f, 0.9f),
                seeds = listOf(SeedMark(120.0, NormBox(0.1f, 0.2f, 0.8f, 0.9f))),
                athleteKey = "Ada-65-170-160",
                athlete = AthleteProfile(
                    key = "Ada-65-170-160",
                    name = "Ada",
                    birthday = "1990-01-01",
                    heightCm = 170f,
                    gender = AthleteGender.FEMALE,
                    weightKg = 65f,
                    skiCm = 160f,
                ),
            )
            lib.saveMeta(meta)
            val loaded = lib.loadMeta("clip-1")
            assertEquals("clip-1", loaded.clipId)
            assertEquals(ClipStatus.PENDING, loaded.status)
            assertEquals(0.1f, loaded.seedBox?.x1 ?: 0f, 0.001f)
            assertEquals(1, loaded.seeds.size)
            assertEquals("Ada-65-170-160", loaded.athleteKey)
            assertEquals(AthleteGender.FEMALE, loaded.athlete?.gender)
            assertNull(loaded.error)
        } finally {
            dir.deleteRecursively()
        }
    }

    @Test
    fun reanalyzeClearsAnalysis() {
        val dir = tempDir()
        try {
            val lib = Library(dir)
            val meta = ClipMeta(
                clipId = "c2",
                createdAt = "t",
                displayName = "n",
                status = ClipStatus.DONE,
                seedBox = NormBox(0f, 0f, 1f, 1f),
            )
            lib.saveMeta(meta)
            File(lib.clipDir("c2"), "analysis.json").writeText("{}")
            val next = lib.prepareReanalyze("c2")
            assertEquals(ClipStatus.PENDING, next.status)
            assertNull(next.seedBox)
            assertEquals(false, lib.analysisFile("c2").isFile)
        } finally {
            dir.deleteRecursively()
        }
    }
}
