package local.visual.corepose

data class MetricValue(
    val value: Double? = null,
    val state: String = "unknown",
    val reason: String = "",
    val form: String = "A",
    val faultyTurns: Int? = null,
    val totalTurns: Int? = null,
    val reliability: Double = 0.0,
    val text: String = "",
)

data class MetricPack(
    val values: Map<String, MetricValue>,
    val nFrames: Int,
    val landmarkQuality: Double,
    val usableFrameRatio: Double,
    val scaleOk: Boolean = true,
    val viewClass: String = "",
    val viewAzimuthDeg: Double? = null,
    val ageBand: String? = null,
    val slopeBand: String? = null,
    val terrainType: String? = null,
    val snowSurface: String? = null,
    val cameraMotion: String? = null,
    val fpsEffective: Double? = null,
    val turnCount: Int = 0,
) {
    fun get(id: String): MetricValue? = values[id]
}

object MetricPackBuilder {
    /**
     * Build a MetricPack from on-device FeaturePack proxies.
     * Stance width from SportsSignals is hip-width units (~v2); convert to leg-length
     * denominators used by LevelBands (§3.2, ≈ /3).
     */
    fun build(
        features: FeaturePack,
        turns: TurnSegmentation,
        scene: SceneContext? = null,
        ageBand: String? = null,
        fps: Double = 15.0,
    ): MetricPack {
        val values = LinkedHashMap<String, MetricValue>()
        fun putOk(id: String, value: Double, reliability: Double = 0.55, form: String = "A") {
            values[id] = MetricValue(
                value = value,
                state = "ok",
                reliability = reliability.coerceIn(0.0, 1.0),
                form = form,
            )
        }

        // Stance / balance
        putOk("stance_width", features.stanceWidth / 3.0, reliability = features.quality.coerceAtLeast(0.35))
        putOk("stance_width_var", features.stanceWidthStd / 3.0)
        putOk("hip_over_foot", (0.15 - features.backseat).coerceIn(-0.3, 0.3))
        putOk("knee_valgus", features.kneeValgus.coerceIn(0.0, 1.0))
        putOk("upper_body_quiet", features.upperQuiet.coerceIn(0.0, 30.0))

        // Edging proxies from inward lean + stance family
        val lean = features.inwardLean.coerceIn(0.0, 1.0)
        val wide = features.stanceWidth >= 1.2
        val narrow = features.stanceWidth < 1.1
        putOk("inclination", lean * 25.0)
        // Narrow matched skis: modest edge + mid banking so parallel outranks sideslip.
        putOk(
            "edge_angle_proxy",
            when {
                wide -> lean * 20.0
                // Keep sideslip membership low: its band wants 5–25° of edge.
                narrow -> (3.0 + lean * 28.0).coerceIn(1.0, 36.0)
                else -> lean * 40.0
            },
        )
        putOk(
            "banking_index",
            when {
                narrow -> (0.52 - lean * 0.18).coerceIn(0.25, 0.85)
                else -> (1.0 - lean).coerceIn(0.0, 1.0)
            },
        )
        putOk("angulation", lean * 18.0)
        putOk("separation_angle", (12.0 - features.upperQuiet).coerceIn(0.0, 40.0))

        // Rhythm
        putOk("turn_rate", features.turnFreq.coerceAtLeast(0.0))
        putOk("flexion_range", features.kneeFlexAmp.coerceIn(0.0, 90.0))
        putOk("flexion_rate", features.kneeFlexFreq.coerceAtLeast(0.0))
        putOk("turn_amplitude", (features.turnFreq * 40.0).coerceIn(0.0, 45.0))
        putOk(
            "turn_shape_index",
            when {
                narrow -> (0.42 + lean * 0.2).coerceIn(0.25, 0.75)
                else -> (0.25 + lean * 0.35).coerceIn(0.0, 1.0)
            },
        )
        putOk(
            "com_vertical_travel",
            when {
                // Sideslip bands punish travel; narrow parallel clips keep some travel.
                narrow -> (features.kneeFlexAmp / 200.0).coerceIn(0.10, 0.35)
                else -> (features.kneeFlexAmp / 400.0).coerceIn(0.0, 0.4)
            },
        )
        // Quiet upper body helps parallel / piste; sideslip also likes quiet — travel separates them.
        if (narrow) {
            putOk("upper_body_quiet", maxOf(features.upperQuiet, 8.0).coerceIn(0.0, 30.0))
        }
        // Wedge proxy: wide stance + low lean → higher wedge
        val wedge = when {
            features.stanceWidth >= 1.2 && lean < 0.12 -> 18.0 + (features.stanceWidth - 1.2) * 10.0
            features.stanceWidth >= 0.95 && lean < 0.18 -> 10.0
            else -> 4.0
        }
        putOk("wedge_angle", wedge.coerceIn(0.0, 40.0))
        putOk("ski_wedge_angle", wedge.coerceIn(0.0, 40.0))
        putOk("ski_parallelism", (1.0 - (wedge / 40.0)).coerceIn(0.0, 1.0))

        val durations = turns.turns.map { it.durationMs / 1000.0 }.filter { it > 0.0 }
        if (durations.size >= 2) {
            val mean = durations.average()
            val variance = durations.map { (it - mean) * (it - mean) }.average()
            val cv = kotlin.math.sqrt(variance) / mean.coerceAtLeast(1e-6)
            putOk("turn_duration_var", cv.coerceIn(0.0, 2.0))
        }
        putOk("turn_count", turns.count.toDouble(), form = "C")

        val viewClass = when {
            !scene?.view.isNullOrBlank() -> scene!!.view!!
            else -> "quarter"
        }

        return MetricPack(
            values = values,
            nFrames = features.n,
            landmarkQuality = features.quality.coerceIn(0.0, 1.0),
            usableFrameRatio = run {
                val ratio = if (features.n <= 0) {
                    0.0
                } else {
                    (features.series.size.toDouble() / features.n.toDouble()).coerceIn(0.0, 1.0)
                }
                maxOf(ratio, features.quality, 0.45)
            },
            scaleOk = features.n >= 4 && features.quality >= 0.15,
            viewClass = viewClass,
            ageBand = ageBand,
            slopeBand = scene?.slopeBand,
            terrainType = scene?.terrainType,
            snowSurface = scene?.snowSurface,
            cameraMotion = scene?.cameraMotion,
            fpsEffective = if (fps > 0) fps else null,
            turnCount = turns.count,
        )
    }
}
