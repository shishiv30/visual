package local.visual.corepose

import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

data class FrameFeedbackEntry(
    var tMs: Double = 0.0,
    var poseIndex: Int? = null,
    var stageVote: String? = null,
    var skeletonOk: Boolean = true,
    var updatedAt: String = "",
)

data class FrameFeedbackFile(
    var clipId: String,
    var stageIdAtVote: String = "",
    val frames: MutableMap<String, FrameFeedbackEntry> = LinkedHashMap(),
)

object FrameFeedback {
    fun empty(clipId: String): FrameFeedbackFile = FrameFeedbackFile(clipId = clipId)

    fun load(file: File, clipId: String): FrameFeedbackFile {
        val empty = empty(clipId)
        if (!file.isFile) {
            return empty
        }
        return try {
            val obj = JSONObject(file.readText(Charsets.UTF_8))
            val doc = FrameFeedbackFile(
                clipId = obj.optString("clip_id", clipId),
                stageIdAtVote = obj.optString("stage_id_at_vote"),
            )
            val frames = obj.optJSONObject("frames") ?: JSONObject()
            val keys = frames.keys()
            while (keys.hasNext()) {
                val key = keys.next()
                val item = frames.optJSONObject(key) ?: continue
                doc.frames[key] = FrameFeedbackEntry(
                    tMs = item.optDouble("t_ms"),
                    poseIndex = if (item.isNull("pose_index")) null else item.optInt("pose_index"),
                    stageVote = if (item.isNull("stage_vote")) {
                        null
                    } else {
                        item.optString("stage_vote").ifBlank { null }
                    },
                    skeletonOk = item.optBoolean("skeleton_ok", true),
                    updatedAt = item.optString("updated_at"),
                )
            }
            doc
        } catch (_: Exception) {
            empty
        }
    }

    fun save(file: File, doc: FrameFeedbackFile) {
        file.parentFile?.mkdirs()
        val frames = JSONObject()
        for ((key, entry) in doc.frames) {
            val item = JSONObject()
                .put("t_ms", entry.tMs)
                .put("skeleton_ok", entry.skeletonOk)
                .put("updated_at", entry.updatedAt)
            if (entry.poseIndex == null) {
                item.put("pose_index", JSONObject.NULL)
            } else {
                item.put("pose_index", entry.poseIndex)
            }
            if (entry.stageVote == null) {
                item.put("stage_vote", JSONObject.NULL)
            } else {
                item.put("stage_vote", entry.stageVote)
            }
            frames.put(key, item)
        }
        file.writeText(
            JSONObject()
                .put("clip_id", doc.clipId)
                .put("stage_id_at_vote", doc.stageIdAtVote)
                .put("frames", frames)
                .toString(2),
            Charsets.UTF_8,
        )
    }

    fun toggleVote(
        file: File,
        clipId: String,
        videoFrame: Int,
        vote: String,
        tMs: Double,
        poseIndex: Int?,
        stageId: String,
    ): FrameFeedbackFile {
        val doc = load(file, clipId)
        doc.clipId = clipId
        val entry = touch(doc, videoFrame, tMs, poseIndex, stageId)
        entry.stageVote = if (entry.stageVote == vote) null else vote
        save(file, doc)
        return doc
    }

    fun toggleSkeleton(
        file: File,
        clipId: String,
        videoFrame: Int,
        tMs: Double,
        poseIndex: Int?,
        stageId: String,
    ): FrameFeedbackFile {
        val doc = load(file, clipId)
        doc.clipId = clipId
        val entry = touch(doc, videoFrame, tMs, poseIndex, stageId)
        entry.skeletonOk = !entry.skeletonOk
        save(file, doc)
        return doc
    }

    private fun touch(
        doc: FrameFeedbackFile,
        videoFrame: Int,
        tMs: Double,
        poseIndex: Int?,
        stageId: String,
    ): FrameFeedbackEntry {
        val key = videoFrame.toString()
        val entry = doc.frames.getOrPut(key) { FrameFeedbackEntry() }
        entry.tMs = tMs
        entry.poseIndex = poseIndex
        entry.updatedAt = nowIso()
        if (stageId.isNotEmpty()) {
            doc.stageIdAtVote = stageId
        }
        return entry
    }

    private fun nowIso(): String {
        val fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        fmt.timeZone = TimeZone.getDefault()
        return fmt.format(Date())
    }
}
