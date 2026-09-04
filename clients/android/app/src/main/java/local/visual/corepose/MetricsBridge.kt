package local.visual.corepose

/**
 * Map curriculum metric ids to on-device FeaturePack signal names when a proxy exists.
 */
object MetricsBridge {
    private val METRIC_TO_SIGNAL = mapOf(
        "stance_width" to "stance_width",
        "stance_width_var" to "stance_width_std",
        "upper_body_quiet" to "upper_quiet",
        "turn_rate" to "turn_freq",
        "com_vertical_travel" to "knee_flex_amp",
        "hip_over_foot" to "backseat",
        "inclination" to "inward_lean",
        "knee_valgus" to "knee_valgus",
        "fall_line_index" to "fall_line",
        "flexion_range" to "knee_flex_amp",
        "flexion_rate" to "knee_flex_freq",
    )

    private val METRIC_DISPLAY = mapOf(
        "stance_width" to "Stance width",
        "stance_width_var" to "Stance width change",
        "wedge_angle" to "Wedge angle",
        "shin_angle_fore_aft" to "Shin angle",
        "hip_over_foot" to "Hips over the feet",
        "com_vertical_travel" to "Up-and-down movement",
        "edge_angle_proxy" to "Edge angle (proxy)",
        "inclination" to "Inclination",
        "angulation" to "Angulation",
        "banking_index" to "Banking share",
        "separation_angle" to "Upper-lower separation",
        "upper_body_quiet" to "Quiet upper body",
        "knee_valgus" to "Knee tracking",
        "turn_rate" to "Turn rate",
        "turn_duration_var" to "Rhythm evenness",
        "turn_amplitude" to "Turn amplitude",
        "turn_shape_index" to "Turn shape",
        "edge_change_duration" to "Edge-change time",
        "flexion_range" to "Knee flex range",
        "flexion_rate" to "Knee flex rate",
        "pressure_peak_phase" to "Pressure peak in the turn",
        "stem_count" to "Stemmed transitions",
        "backseat_count" to "Back-seat finishes",
        "rotation_count" to "Turns led by the shoulders",
        "braking_count" to "Braking turns",
        "asymmetry_index" to "Left-right asymmetry",
        "hands_in_view" to "Hands in view",
        "pole_touch_rate" to "Pole touch per turn",
        "pole_touch_timing" to "Pole touch timing",
        "fall_line_index" to "Fall-line",
        "turn_count" to "Turns detected",
    )

    fun measurementKey(spec: CheckpointSpec): String? {
        if (!spec.signal.isNullOrBlank()) {
            return spec.signal
        }
        val metric = spec.metric ?: return null
        return METRIC_TO_SIGNAL[metric]
    }

    fun metricValue(pack: FeaturePack, metricId: String): Double? {
        val signal = METRIC_TO_SIGNAL[metricId] ?: return null
        return SportsSignals.signalValue(pack, signal)
    }

    fun displayName(metricId: String, lang: String): String {
        val base = metricId.removeSuffix("_left").removeSuffix("_right")
        val key = METRIC_DISPLAY[base] ?: humanize(base)
        return I18n.t(key, lang = lang)
    }

    private fun humanize(id: String): String {
        return id.split('_').joinToString(" ") { part ->
            part.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        }
    }
}
