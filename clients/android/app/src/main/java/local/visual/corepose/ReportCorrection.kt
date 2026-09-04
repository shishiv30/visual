package local.visual.corepose

import org.json.JSONObject
import java.io.File

data class ReportCorrection(
    val clipId: String,
    val predictedStageId: String,
    val correctedStageId: String,
    val note: String = "",
)

object ReportCorrectionStore {
    fun save(file: File, correction: ReportCorrection) {
        file.parentFile?.mkdirs()
        val obj = JSONObject()
            .put("clip_id", correction.clipId)
            .put("predicted_stage_id", correction.predictedStageId)
            .put("corrected_stage_id", correction.correctedStageId)
            .put("note", correction.note)
        file.writeText(obj.toString(2), Charsets.UTF_8)
    }

    fun load(file: File): ReportCorrection? {
        if (!file.isFile) {
            return null
        }
        return try {
            val obj = JSONObject(file.readText(Charsets.UTF_8))
            ReportCorrection(
                clipId = obj.optString("clip_id"),
                predictedStageId = obj.optString("predicted_stage_id"),
                correctedStageId = obj.optString("corrected_stage_id"),
                note = obj.optString("note"),
            )
        } catch (_: Exception) {
            null
        }
    }
}
