package local.visual.corepose

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

enum class ClipKind {
    VIDEO,
    IMAGE,
}

enum class ClipStatus {
    PENDING,
    PROCESSING,
    DONE,
}

data class NormBox(
    val x1: Float,
    val y1: Float,
    val x2: Float,
    val y2: Float,
) {
    fun toList(): List<Float> = listOf(x1, y1, x2, y2)

    companion object {
        fun fromArray(arr: JSONArray): NormBox? {
            if (arr.length() < 4) {
                return null
            }
            return NormBox(
                arr.optDouble(0).toFloat(),
                arr.optDouble(1).toFloat(),
                arr.optDouble(2).toFloat(),
                arr.optDouble(3).toFloat(),
            )
        }
    }
}

data class SeedMark(
    val tMs: Double,
    val box: NormBox,
)

data class ClipMeta(
    val clipId: String,
    val createdAt: String,
    val displayName: String,
    val durationMs: Int = 0,
    val width: Int = 1,
    val height: Int = 1,
    val fps: Double = 30.0,
    val kind: ClipKind = ClipKind.VIDEO,
    val status: ClipStatus = ClipStatus.PENDING,
    val error: String? = null,
    val seedBox: NormBox? = null,
    val seeds: List<SeedMark> = emptyList(),
    val playStartMs: Int = 0,
    val playEndMs: Int? = null,
    val athleteKey: String? = null,
    val athlete: AthleteProfile? = null,
    val scene: SceneContext? = null,
)

class Library(private val root: File) {
    fun clipDir(clipId: String): File = File(root, clipId)

    fun mediaFile(meta: ClipMeta): File {
        val folder = clipDir(meta.clipId)
        return if (meta.kind == ClipKind.IMAGE) File(folder, "clip.jpg") else File(folder, "clip.mp4")
    }

    fun thumbFile(clipId: String): File = File(clipDir(clipId), "thumb.jpg")

    fun metaFile(clipId: String): File = File(clipDir(clipId), "meta.json")

    fun analysisFile(clipId: String): File = File(clipDir(clipId), "analysis.json")

    fun stageReportFile(clipId: String): File = File(clipDir(clipId), "stage_report.json")

    fun frameFeedbackFile(clipId: String): File = File(clipDir(clipId), "frame_feedback.json")

    fun reportCorrectionFile(clipId: String): File = File(clipDir(clipId), "report_correction.json")

    fun saveMeta(meta: ClipMeta) {
        val path = metaFile(meta.clipId)
        path.parentFile?.mkdirs()
        path.writeText(toJson(meta).toString(2), Charsets.UTF_8)
    }

    fun loadMeta(clipId: String): ClipMeta {
        return fromJson(JSONObject(metaFile(clipId).readText(Charsets.UTF_8)))
    }

    fun listClips(): List<ClipMeta> {
        if (!root.isDirectory) {
            return emptyList()
        }
        return root.listFiles()
            ?.mapNotNull { folder ->
                val path = File(folder, "meta.json")
                if (!path.isFile) {
                    return@mapNotNull null
                }
                try {
                    fromJson(JSONObject(path.readText(Charsets.UTF_8)))
                } catch (_: Exception) {
                    null
                }
            }
            ?.sortedByDescending { it.createdAt }
            ?: emptyList()
    }

    fun deleteClip(clipId: String) {
        clipDir(clipId).deleteRecursively()
    }

    fun prepareReanalyze(clipId: String): ClipMeta {
        val meta = loadMeta(clipId).copy(
            status = ClipStatus.PENDING,
            error = null,
            seedBox = null,
            seeds = emptyList(),
            playStartMs = 0,
            playEndMs = null,
        )
        saveMeta(meta)
        analysisFile(clipId).delete()
        stageReportFile(clipId).delete()
        frameFeedbackFile(clipId).delete()
        return meta
    }

    fun newClipId(): String = UUID.randomUUID().toString()

    companion object {
        const val MAX_MS = 120_000L

        fun displayNameNow(now: Date = Date()): String {
            val fmt = SimpleDateFormat("MM/dd/yyyy-HH:mm", Locale.US)
            fmt.timeZone = TimeZone.getDefault()
            return fmt.format(now)
        }

        fun createdAtIso(now: Date = Date()): String {
            val fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            fmt.timeZone = TimeZone.getDefault()
            return fmt.format(now)
        }

        fun formatDurationMs(ms: Int, image: Boolean = false): String {
            if (image) {
                return "--"
            }
            val total = (ms / 1000).coerceAtLeast(0)
            val m = total / 60
            val s = total % 60
            return "$m:${s.toString().padStart(2, '0')}"
        }

        fun playWindowMs(meta: ClipMeta): Pair<Long, Long> {
            val start = meta.playStartMs.toLong().coerceAtLeast(0L)
            val end = meta.playEndMs?.toLong()
                ?: if (meta.durationMs > 0) meta.durationMs.toLong() else Long.MAX_VALUE / 4
            return start to if (end <= start) start + 1 else end
        }

        fun statusKey(status: ClipStatus): String = when (status) {
            ClipStatus.PENDING -> "Pending"
            ClipStatus.PROCESSING -> "Processing"
            ClipStatus.DONE -> "Done"
        }

        fun toJson(meta: ClipMeta): JSONObject {
            val obj = JSONObject()
            obj.put("clip_id", meta.clipId)
            obj.put("created_at", meta.createdAt)
            obj.put("display_name", meta.displayName)
            obj.put("duration_ms", meta.durationMs)
            obj.put("width", meta.width)
            obj.put("height", meta.height)
            obj.put("fps", meta.fps)
            obj.put("kind", meta.kind.name.lowercase(Locale.US))
            obj.put("status", meta.status.name.lowercase(Locale.US))
            if (meta.error == null) {
                obj.put("error", JSONObject.NULL)
            } else {
                obj.put("error", meta.error)
            }
            if (meta.seedBox == null) {
                obj.put("seed_box", JSONObject.NULL)
            } else {
                obj.put("seed_box", JSONArray(meta.seedBox.toList()))
            }
            val seeds = JSONArray()
            for (seed in meta.seeds) {
                seeds.put(
                    JSONObject()
                        .put("t_ms", seed.tMs)
                        .put("box", JSONArray(seed.box.toList())),
                )
            }
            obj.put("seeds", seeds)
            obj.put("play_start_ms", meta.playStartMs)
            if (meta.playEndMs == null) {
                obj.put("play_end_ms", JSONObject.NULL)
            } else {
                obj.put("play_end_ms", meta.playEndMs)
            }
            if (meta.athleteKey == null) {
                obj.put("athlete_key", JSONObject.NULL)
            } else {
                obj.put("athlete_key", meta.athleteKey)
            }
            if (meta.athlete == null) {
                obj.put("athlete", JSONObject.NULL)
            } else {
                obj.put("athlete", meta.athlete.toJson())
            }
            if (meta.scene == null) {
                obj.put("scene", JSONObject.NULL)
            } else {
                obj.put("scene", meta.scene.toJson())
            }
            return obj
        }

        fun fromJson(obj: JSONObject): ClipMeta {
            val seedArr = obj.optJSONArray("seed_box")
            val seedsArr = obj.optJSONArray("seeds")
            val seeds = ArrayList<SeedMark>()
            if (seedsArr != null) {
                for (i in 0 until seedsArr.length()) {
                    val item = seedsArr.optJSONObject(i) ?: continue
                    val box = item.optJSONArray("box")?.let { NormBox.fromArray(it) } ?: continue
                    seeds.add(SeedMark(item.optDouble("t_ms"), box))
                }
            }
            return ClipMeta(
                clipId = obj.getString("clip_id"),
                createdAt = obj.optString("created_at"),
                displayName = obj.optString("display_name"),
                durationMs = obj.optInt("duration_ms"),
                width = obj.optInt("width", 1).coerceAtLeast(1),
                height = obj.optInt("height", 1).coerceAtLeast(1),
                fps = obj.optDouble("fps", 30.0),
                kind = if (obj.optString("kind") == "image") ClipKind.IMAGE else ClipKind.VIDEO,
                status = when (obj.optString("status")) {
                    "processing" -> ClipStatus.PROCESSING
                    "done" -> ClipStatus.DONE
                    else -> ClipStatus.PENDING
                },
                error = if (obj.isNull("error")) null else obj.optString("error").ifBlank { null },
                seedBox = seedArr?.let { NormBox.fromArray(it) },
                seeds = seeds,
                playStartMs = obj.optDouble("play_start_ms", 0.0).toInt().coerceAtLeast(0),
                playEndMs = if (obj.isNull("play_end_ms")) {
                    null
                } else {
                    obj.optDouble("play_end_ms").toInt().coerceAtLeast(0)
                },
                athleteKey = if (obj.has("athlete_key") && !obj.isNull("athlete_key")) {
                    obj.optString("athlete_key").ifBlank { null }
                } else {
                    null
                },
                athlete = obj.optJSONObject("athlete")?.let { AthleteProfile.fromJson(it) },
                scene = SceneContext.fromJson(obj.optJSONObject("scene")),
            )
        }
    }
}
