package local.visual.corepose

/**
 * Scene facts the clip cannot supply alone (mirrors `core.sports.scene`).
 * All fields optional; missing facts exclude scene-tier levels from auto-detect.
 */
data class SceneContext(
    val terrainType: String? = null,
    val slopeBand: String? = null,
    val snowSurface: String? = null,
    val view: String? = null,
    val cameraMotion: String? = null,
) {
    fun toJson(): org.json.JSONObject {
        val obj = org.json.JSONObject()
        putOpt(obj, "terrain_type", terrainType)
        putOpt(obj, "slope_band", slopeBand)
        putOpt(obj, "snow_surface", snowSurface)
        putOpt(obj, "view", view)
        putOpt(obj, "camera_motion", cameraMotion)
        return obj
    }

    companion object {
        const val NOT_SURE = ""

        val TERRAIN_CHOICES = listOf(
            "piste" to "Groomed piste",
            "mogul" to "Mogul run",
            "park" to "Terrain park",
            "offpiste" to "Off-piste / powder",
        )
        val SLOPE_CHOICES = listOf(
            "green" to "Green run",
            "blue" to "Blue run",
            "black" to "Black run",
            "double-black" to "Double black run",
        )
        val SNOW_CHOICES = listOf(
            "corduroy" to "Corduroy",
            "packed" to "Packed",
            "hardpack" to "Hardpack",
            "ice" to "Ice",
            "soft" to "Soft",
            "powder" to "Powder",
            "crud" to "Crud",
            "slush" to "Slush",
        )

        fun fromJson(obj: org.json.JSONObject?): SceneContext? {
            if (obj == null) {
                return null
            }
            return SceneContext(
                terrainType = obj.optString("terrain_type").ifBlank { null },
                slopeBand = obj.optString("slope_band").ifBlank { null },
                snowSurface = obj.optString("snow_surface").ifBlank { null },
                view = obj.optString("view").ifBlank { null },
                cameraMotion = obj.optString("camera_motion").ifBlank { null },
            )
        }

        private fun putOpt(obj: org.json.JSONObject, key: String, value: String?) {
            if (value.isNullOrBlank()) {
                obj.put(key, org.json.JSONObject.NULL)
            } else {
                obj.put(key, value)
            }
        }
    }
}
