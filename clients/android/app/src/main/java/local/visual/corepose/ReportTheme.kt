package local.visual.corepose

import android.graphics.Color

object ReportTheme {
    const val CARD = 0xFF1A2433.toInt()
    const val TITLE = 0xFF9E9E9E.toInt()
    const val PAPER = 0xFFF5F5F5.toInt()
    const val RING_TRACK = 0xFF2A3544.toInt()
    const val LINK = 0xFF4FC3F7.toInt()
    const val DEEP_PURPLE = 0xFF5E35B1.toInt()
    const val LIGHT_PURPLE = 0xFFCE93D8.toInt()
    const val WATERMELON = 0xFFE94B6A.toInt()
    const val TERRAIN_BLACK = 0xFF000000.toInt()
    const val SPACE_CHAPTER = 36
    const val SPACE_PANEL = 24
    const val SPACE_TEXT = 16
    const val PAGE_INSET = 12
    const val REPORT_INSET = 8

    fun scorePurple(score: Double?): Int {
        if (score == null || score <= 0.0) {
            return TITLE
        }
        val frac = (score / 100.0).coerceIn(0.0, 1.0)
        val r0 = 0x5E
        val g0 = 0x35
        val b0 = 0xB1
        val r1 = 0xCE
        val g1 = 0x93
        val b1 = 0xD8
        val r = (r0 + (r1 - r0) * frac).toInt()
        val g = (g0 + (g1 - g0) * frac).toInt()
        val b = (b0 + (b1 - b0) * frac).toInt()
        return Color.rgb(r, g, b)
    }

    fun medalColor(stageId: String): Int {
        return when (stageId) {
            "pizza_glide", "pizza", "wedge_christie" -> 0xFF43A047.toInt()
            "parallel", "skid_short", "carve_long", "switch" -> 0xFF1E88E5.toInt()
            "carve_medium", "mogul_absorb", "gates" -> 0xFF8E24AA.toInt()
            "carve_short", "mogul_fallline", "ollie", "park" -> 0xFFFFC107.toInt()
            else -> 0xFF1E88E5.toInt()
        }
    }

    fun terrainDiamondColors(terrainId: String): List<Int> {
        return when (terrainId) {
            "green" -> listOf(0xFF2E7D32.toInt())
            "blue" -> listOf(0xFF1565C0.toInt())
            "red" -> listOf(0xFFC62828.toInt())
            "black", "mogul" -> listOf(TERRAIN_BLACK)
            "double_black", "black_double" -> listOf(TERRAIN_BLACK, TERRAIN_BLACK)
            "park" -> listOf(0xFF8E24AA.toInt())
            else -> listOf(0xFF9E9E9E.toInt())
        }
    }

    fun formatEvidenceMs(tMs: Double): String {
        val total = maxOf(0.0, tMs / 1000.0)
        val minutes = total.toInt() / 60
        val seconds = total - minutes * 60
        return "%d:%04.1f".format(minutes, seconds)
    }

    fun sortedKeypoints(items: List<KeypointResult>): List<KeypointResult> {
        return items.sortedWith(
            compareBy<KeypointResult> { if (it.status == KeypointStatus.FAIL) 0 else 1 }
                .thenBy { it.score ?: 101.0 },
        )
    }
}
