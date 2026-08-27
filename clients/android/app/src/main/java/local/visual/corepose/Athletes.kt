package local.visual.corepose

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

enum class AthleteGender(val value: String) {
    UNSPECIFIED("unspecified"),
    FEMALE("female"),
    MALE("male"),
    OTHER("other");

    companion object {
        fun fromValue(raw: String?): AthleteGender {
            return entries.firstOrNull { it.value == raw } ?: UNSPECIFIED
        }
    }
}

data class AthleteProfile(
    val key: String,
    val name: String,
    val birthday: String = "",
    val heightCm: Float,
    val gender: AthleteGender = AthleteGender.UNSPECIFIED,
    val weightKg: Float,
    val skiCm: Float,
    val updatedAt: String = "",
) {
    fun toJson(): JSONObject {
        return JSONObject()
            .put("key", key)
            .put("name", name)
            .put("birthday", birthday)
            .put("height_cm", heightCm.toDouble())
            .put("gender", gender.value)
            .put("weight_kg", weightKg.toDouble())
            .put("ski_cm", skiCm.toDouble())
            .put("updated_at", updatedAt)
    }

    companion object {
        fun fromJson(obj: JSONObject): AthleteProfile {
            return AthleteProfile(
                key = obj.optString("key"),
                name = obj.optString("name"),
                birthday = obj.optString("birthday"),
                heightCm = obj.optDouble("height_cm").toFloat(),
                gender = AthleteGender.fromValue(obj.optString("gender")),
                weightKg = obj.optDouble("weight_kg").toFloat(),
                skiCm = obj.optDouble("ski_cm").toFloat(),
                updatedAt = obj.optString("updated_at"),
            )
        }
    }
}

class Athletes(private val file: File) {
    fun list(): List<AthleteProfile> {
        return load().sortedBy { it.key.lowercase(Locale.US) }
    }

    fun getByKey(key: String): AthleteProfile? {
        val want = key.trim()
        return load().firstOrNull { it.key == want }
    }

    fun upsert(
        name: String,
        weightKg: Float,
        heightCm: Float,
        skiCm: Float,
        birthday: String = "",
        gender: AthleteGender = AthleteGender.UNSPECIFIED,
    ): AthleteProfile {
        val cleaned = name.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
        if (cleaned.isEmpty()) {
            throw IllegalArgumentException("name required")
        }
        if (weightKg <= 0f || heightCm <= 0f || skiCm <= 0f) {
            throw IllegalArgumentException("measures must be positive")
        }
        val profile = AthleteProfile(
            key = athleteKey(cleaned, weightKg, heightCm, skiCm),
            name = cleaned,
            birthday = birthday.trim(),
            heightCm = round1(heightCm),
            gender = gender,
            weightKg = round1(weightKg),
            skiCm = round1(skiCm),
            updatedAt = nowIso(),
        )
        val next = ArrayList<AthleteProfile>()
        var replaced = false
        for (item in load()) {
            if (item.key == profile.key) {
                next.add(profile)
                replaced = true
            } else {
                next.add(item)
            }
        }
        if (!replaced) {
            next.add(profile)
        }
        save(next)
        return profile
    }

    private fun load(): List<AthleteProfile> {
        if (!file.isFile) {
            return emptyList()
        }
        return try {
            val root = JSONObject(file.readText(Charsets.UTF_8))
            val arr = root.optJSONArray("athletes") ?: JSONArray()
            val out = ArrayList<AthleteProfile>(arr.length())
            for (i in 0 until arr.length()) {
                val item = arr.optJSONObject(i) ?: continue
                out.add(AthleteProfile.fromJson(item))
            }
            out
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun save(athletes: List<AthleteProfile>) {
        file.parentFile?.mkdirs()
        val arr = JSONArray()
        for (item in athletes) {
            arr.put(item.toJson())
        }
        val root = JSONObject()
            .put("schema_version", "1.0.0")
            .put("athletes", arr)
        file.writeText(root.toString(2), Charsets.UTF_8)
    }

    companion object {
        fun formatMeasure(value: Float): String {
            val rounded = round1(value)
            return if (rounded == rounded.toInt().toFloat()) {
                rounded.toInt().toString()
            } else {
                "%.1f".format(Locale.US, rounded)
            }
        }

        fun athleteKey(name: String, weightKg: Float, heightCm: Float, skiCm: Float): String {
            val cleaned = name.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
            return "$cleaned-${formatMeasure(weightKg)}-${formatMeasure(heightCm)}-${formatMeasure(skiCm)}"
        }

        fun round1(value: Float): Float = kotlin.math.round(value * 10f) / 10f

        fun nowIso(): String {
            val fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            fmt.timeZone = TimeZone.getDefault()
            return fmt.format(Date())
        }
    }
}
