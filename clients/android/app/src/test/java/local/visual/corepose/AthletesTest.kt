package local.visual.corepose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.File

class AthletesTest {
    private fun tempFile(): File {
        val dir = File.createTempFile("visual-ath", "")
        dir.delete()
        dir.mkdirs()
        return File(dir, "athletes.json")
    }

    @Test
    fun upsertRoundTripAndKey() {
        val path = tempFile()
        try {
            val store = Athletes(path)
            val profile = store.upsert(
                name = "Ada  Lovelace",
                weightKg = 65f,
                heightCm = 170f,
                skiCm = 160f,
                birthday = "1990-01-01",
                gender = AthleteGender.FEMALE,
            )
            assertEquals("Ada Lovelace-65-170-160", profile.key)
            assertEquals(AthleteGender.FEMALE, store.getByKey(profile.key)?.gender)
            assertEquals(1, store.list().size)
            store.upsert(
                name = "Ada Lovelace",
                weightKg = 65f,
                heightCm = 170f,
                skiCm = 160f,
                birthday = "1991-02-03",
                gender = AthleteGender.FEMALE,
            )
            assertEquals(1, store.list().size)
            assertEquals("1991-02-03", store.getByKey(profile.key)?.birthday)
        } finally {
            path.parentFile?.deleteRecursively()
        }
    }

    @Test
    fun missingFileIsEmpty() {
        val path = File.createTempFile("visual-missing", ".json")
        path.delete()
        assertNull(Athletes(path).getByKey("nope"))
        assertEquals(0, Athletes(path).list().size)
    }
}
