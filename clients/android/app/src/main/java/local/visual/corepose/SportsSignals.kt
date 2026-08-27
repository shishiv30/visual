package local.visual.corepose

data class BlazeJoint(
    val x: Float,
    val y: Float,
    val z: Float = 0f,
    val confidence: Float,
)

data class BBox(
    val x1: Float,
    val y1: Float,
    val x2: Float,
    val y2: Float,
)

data class FrameSample(
    val tMs: Double,
    val stanceWidth: Double? = null,
    val kneeFlex: Double? = null,
    val inwardLean: Double? = null,
    val backseat: Double? = null,
    val kneeValgus: Double? = null,
    val hipIrProxy: Double? = null,
    val handsLow: Double? = null,
    val gazeOk: Double? = null,
    val quiet: Double? = null,
    val hipX: Double? = null,
    val hipY: Double? = null,
)

data class FeaturePack(
    val n: Int,
    val fps: Double,
    val stanceWidth: Double,
    val stanceWidthStd: Double,
    val kneeFlexMean: Double,
    val kneeFlexAmp: Double,
    val kneeFlexFreq: Double,
    val upperQuiet: Double,
    val inwardLean: Double,
    val turnFreq: Double,
    val fallLine: Double,
    val backseat: Double,
    val kneeValgus: Double,
    val hipIrProxy: Double,
    val handsLow: Double,
    val gazeOk: Double?,
    val footOk: Boolean,
    val quality: Double,
    val series: List<FrameSample>,
    val hipXMean: Double = 0.0,
)

data class AssessFrame(
    val tMs: Double,
    val blaze33: List<BlazeJoint>,
)

object SportsSignals {
    const val L_SHOULDER = 11
    const val R_SHOULDER = 12
    const val L_HIP = 23
    const val R_HIP = 24
    const val L_KNEE = 25
    const val R_KNEE = 26
    const val L_ANKLE = 27
    const val R_ANKLE = 28
    const val L_FOOT = 31
    const val R_FOOT = 32
    const val L_WRIST = 15
    const val R_WRIST = 16
    const val NOSE = 0
    const val CONF_MIN = 0.25

    private val clipSignals = setOf(
        "stance_width",
        "stance_width_std",
        "knee_flex_mean",
        "knee_flex_amp",
        "knee_flex_freq",
        "upper_quiet",
        "inward_lean",
        "turn_freq",
        "fall_line",
        "backseat",
        "knee_valgus",
        "hip_ir_proxy",
        "hands_low",
        "gaze_ok",
    )

    fun extractFeatures(frames: List<AssessFrame>, fpsIn: Double): FeaturePack {
        val fps = if (fpsIn > 1.0) fpsIn else 15.0
        val stance = ArrayList<Double>()
        val knees = ArrayList<Double>()
        val leans = ArrayList<Double>()
        val quiet = ArrayList<Double>()
        val hipsX = ArrayList<Double>()
        val hipsY = ArrayList<Double>()
        val back = ArrayList<Double>()
        val vis = ArrayList<Double>()
        val valgus = ArrayList<Double>()
        val hipIr = ArrayList<Double>()
        val hands = ArrayList<Double>()
        val gaze = ArrayList<Double>()
        val series = ArrayList<FrameSample>()
        var footHits = 0
        for (frame in frames) {
            val lh = xy(frame, L_HIP) ?: continue
            val rh = xy(frame, R_HIP) ?: continue
            val la = xy(frame, L_ANKLE)
            val ra = xy(frame, R_ANKLE)
            val lk = xy(frame, L_KNEE)
            val rk = xy(frame, R_KNEE)
            val ls = xy(frame, L_SHOULDER)
            val rs = xy(frame, R_SHOULDER)
            val lf = xy(frame, L_FOOT)
            val rf = xy(frame, R_FOOT)
            val lw = xy(frame, L_WRIST)
            val rw = xy(frame, R_WRIST)
            val nose = xy(frame, NOSE)
            val hipW = kotlin.math.abs(lh[0] - rh[0]) + 1e-3
            if (la != null && ra != null) {
                stance.add(kotlin.math.abs(la[0] - ra[0]) / hipW)
            }
            if (lf != null && rf != null) {
                footHits += 1
            }
            if (lk != null && rk != null && la != null && ra != null) {
                val kneeSpan = kotlin.math.abs(lk[0] - rk[0])
                val ankleSpan = kotlin.math.abs(la[0] - ra[0]) + 1e-3
                hipIr.add(maxOf(0.0, 1.0 - kneeSpan / ankleSpan))
                valgus.add((kotlin.math.abs(lk[0] - la[0]) + kotlin.math.abs(rk[0] - ra[0])) / (2.0 * hipW))
            }
            if (lk != null && la != null) {
                knees.add(SportsMath.angleDeg(lh[0], lh[1], lk[0], lk[1], la[0], la[1]))
            }
            if (rk != null && ra != null) {
                knees.add(SportsMath.angleDeg(rh[0], rh[1], rk[0], rk[1], ra[0], ra[1]))
            }
            if (ls != null && rs != null) {
                val shoulderMid = 0.5 * (ls[0] + rs[0])
                val hipMid = 0.5 * (lh[0] + rh[0])
                leans.add((shoulderMid - hipMid) / hipW)
                val shAng = kotlin.math.atan2(rs[1] - ls[1], rs[0] - ls[0] + 1e-6)
                val hpAng = kotlin.math.atan2(rh[1] - lh[1], rh[0] - lh[0] + 1e-6)
                quiet.add(kotlin.math.abs(shAng - hpAng))
                vis.add(minOf(ls[2], rs[2], lh[2], rh[2]))
                if (lw != null && rw != null) {
                    val shY = 0.5 * (ls[1] + rs[1])
                    val wrY = 0.5 * (lw[1] + rw[1])
                    hands.add(if (wrY >= shY) 1.0 else 0.0)
                }
            }
            if (nose != null) {
                gaze.add(if (nose[2] >= 0.4) 1.0 else 0.0)
            }
            hipsX.add(0.5 * (lh[0] + rh[0]))
            hipsY.add(0.5 * (lh[1] + rh[1]))
            if (la != null && ra != null) {
                val ankleY = 0.5 * (la[1] + ra[1])
                val hipY = 0.5 * (lh[1] + rh[1])
                val torso = kotlin.math.abs(
                    hipsY.last() - (if (ls != null && rs != null) (ls[1] + rs[1]) * 0.5 else hipY),
                ) + 1e-3
                back.add((hipY - ankleY) / torso)
            }
            val frameFlex = ArrayList<Double>()
            if (lk != null && la != null) {
                val leftK = SportsMath.angleDeg(lh[0], lh[1], lk[0], lk[1], la[0], la[1])
                if (leftK.isFinite()) {
                    frameFlex.add(180.0 - leftK)
                }
            }
            if (rk != null && ra != null) {
                val rightK = SportsMath.angleDeg(rh[0], rh[1], rk[0], rk[1], ra[0], ra[1])
                if (rightK.isFinite()) {
                    frameFlex.add(180.0 - rightK)
                }
            }
            val flexNow = if (frameFlex.isEmpty()) null else frameFlex.average()
            series.add(
                FrameSample(
                    tMs = frame.tMs,
                    stanceWidth = if (la != null && ra != null) stance.last() else null,
                    kneeFlex = flexNow,
                    inwardLean = if (ls != null && rs != null) leans.last() else null,
                    backseat = if (la != null && ra != null) back.last() else null,
                    kneeValgus = if (valgus.isNotEmpty() && lk != null && rk != null && la != null && ra != null) valgus.last() else null,
                    hipIrProxy = if (hipIr.isNotEmpty() && lk != null && rk != null && la != null && ra != null) hipIr.last() else null,
                    handsLow = if (lw != null && rw != null) hands.last() else null,
                    gazeOk = if (nose != null) gaze.last() else null,
                    quiet = if (ls != null && rs != null) quiet.last() else null,
                    hipX = hipsX.lastOrNull(),
                    hipY = hipsY.lastOrNull(),
                ),
            )
        }
        val n = maxOf(series.size, 1)
        val stanceA = if (stance.isEmpty()) doubleArrayOf(1.0) else stance.toDoubleArray()
        val kneeFinite = knees.filter { it.isFinite() }
        val kneeA = if (kneeFinite.isEmpty()) doubleArrayOf(160.0) else kneeFinite.toDoubleArray()
        val flex = DoubleArray(kneeA.size) { 180.0 - kneeA[it] }
        val quietA = if (quiet.isEmpty()) doubleArrayOf(0.2) else quiet.toDoubleArray()
        val leanA = if (leans.isEmpty()) doubleArrayOf(0.0) else leans.toDoubleArray()
        val hx = hipsX.toDoubleArray()
        val hy = hipsY.toDoubleArray()
        val turnFreq = if (hx.size > 4) {
            val mu = SportsMath.mean(hx)
            SportsMath.zeroCrossFreq(DoubleArray(hx.size) { hx[it] - mu }, fps)
        } else {
            0.0
        }
        val kneeFreq = if (flex.size > 4) {
            val mu = SportsMath.mean(flex)
            SportsMath.zeroCrossFreq(DoubleArray(flex.size) { flex[it] - mu }, fps)
        } else {
            0.0
        }
        var fall = 0.0
        if (hx.size > 2 && hy.size > 2) {
            val dx = SportsMath.std(hx)
            val dy = SportsMath.std(hy) + 1e-3
            fall = dx / dy
        }
        val backA = if (back.isEmpty()) doubleArrayOf(0.0) else back.toDoubleArray()
        val quality = if (vis.isEmpty()) 0.0 else vis.average()
        val valA = if (valgus.isEmpty()) doubleArrayOf(0.2) else valgus.toDoubleArray()
        val irA = if (hipIr.isEmpty()) doubleArrayOf(0.0) else hipIr.toDoubleArray()
        val handA = hands.toDoubleArray()
        val gazeScore = if (gaze.isEmpty()) null else gaze.average()
        return FeaturePack(
            n = n,
            fps = fps,
            stanceWidth = SportsMath.median(stanceA),
            stanceWidthStd = SportsMath.std(stanceA),
            kneeFlexMean = SportsMath.median(flex),
            kneeFlexAmp = SportsMath.percentile(flex, 90.0) - SportsMath.percentile(flex, 10.0),
            kneeFlexFreq = kneeFreq,
            upperQuiet = SportsMath.std(quietA),
            inwardLean = SportsMath.mean(DoubleArray(leanA.size) { kotlin.math.abs(leanA[it]) }),
            turnFreq = turnFreq,
            fallLine = fall,
            backseat = SportsMath.median(backA),
            kneeValgus = SportsMath.median(valA),
            hipIrProxy = SportsMath.median(irA),
            handsLow = if (handA.isEmpty()) 0.0 else SportsMath.mean(handA),
            gazeOk = gazeScore,
            footOk = footHits >= maxOf(2, n / 8),
            quality = quality,
            series = series,
            hipXMean = if (hx.isEmpty()) 0.0 else SportsMath.mean(hx),
        )
    }

    fun signalValue(pack: FeaturePack, name: String): Double? {
        val mapping: Map<String, Double?> = mapOf(
            "stance_width" to pack.stanceWidth,
            "stance_width_std" to pack.stanceWidthStd,
            "knee_flex_mean" to pack.kneeFlexMean,
            "knee_flex_amp" to pack.kneeFlexAmp,
            "knee_flex_freq" to pack.kneeFlexFreq,
            "upper_quiet" to pack.upperQuiet,
            "inward_lean" to pack.inwardLean,
            "turn_freq" to pack.turnFreq,
            "fall_line" to pack.fallLine,
            "backseat" to pack.backseat,
            "knee_valgus" to pack.kneeValgus,
            "hip_ir_proxy" to pack.hipIrProxy,
            "hands_low" to pack.handsLow,
            "gaze_ok" to pack.gazeOk,
        )
        if (name !in clipSignals || name !in mapping) {
            return null
        }
        if (name.startsWith("stance") && !pack.footOk) {
            return null
        }
        if (name in setOf("knee_valgus", "hip_ir_proxy") && !pack.footOk) {
            return null
        }
        return mapping[name]
    }

    fun sampleSignal(sample: FrameSample, name: String): Double? {
        return when (name) {
            "stance_width" -> sample.stanceWidth
            "knee_flex_mean" -> sample.kneeFlex
            "inward_lean" -> sample.inwardLean?.let { kotlin.math.abs(it) }
            "backseat" -> sample.backseat
            "knee_valgus" -> sample.kneeValgus
            "hip_ir_proxy" -> sample.hipIrProxy
            "hands_low" -> sample.handsLow
            "gaze_ok" -> sample.gazeOk
            "upper_quiet" -> sample.quiet
            else -> null
        }
    }

    private fun xy(frame: AssessFrame, index: Int): DoubleArray? {
        if (frame.blaze33.size < 33) {
            return null
        }
        val joint = frame.blaze33[index]
        if (joint.confidence < CONF_MIN) {
            return null
        }
        return doubleArrayOf(joint.x.toDouble(), joint.y.toDouble(), joint.confidence.toDouble())
    }
}
