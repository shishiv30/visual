package local.visual.corepose

/** Port of core/sports/classify.py classify_v3. */
object ClassifyV3 {
    const val W_FIT = 0.55
    const val W_GATE = 0.30
    const val W_PRIOR = 0.15
    const val SEPARATION_SPAN = 0.15
    const val SEPARATION_FLOOR = 0.40
    const val CONF_GATE = 0.35
    const val MIN_FRAMES = 6
    const val MIN_LANDMARK_QUALITY = 0.20
    const val MIN_USABLE_FRAME_RATIO = 0.40
    const val QUALITY_REF = 0.70
    const val USABLE_REF = 0.80
    const val VIEW_PENALTY_SINGLE_PLANE = 0.80
    const val PRIOR_NEUTRAL = 0.50
    const val PRIOR_ADJACENT = 0.40
    const val PRIOR_PASSED_PENALTY = 0.30
    const val PRIOR_TERRAIN_MATCH = 0.15
    const val PRIOR_TERRAIN_STEP = 0.12
    const val FIT_COVERAGE_FLOOR = 0.5

    const val REASON_TOO_FEW_FRAMES = "too_few_frames"
    const val REASON_LOW_QUALITY = "low_landmark_quality"
    const val REASON_FEW_USABLE_FRAMES = "few_usable_frames"
    const val REASON_NO_BODY_SCALE = "no_body_scale"
    const val REASON_NOTHING_MEASURED = "no_measurable_metrics"
    const val REASON_NO_CANDIDATES = "no_candidate_stage"
    const val REASON_NOT_APPLICABLE_AGE = "not_applicable_age_band"
    const val REASON_PARALLEL_STANCE = "parallel_stance_detected"

    private val BAND_ORDINAL = mapOf("green" to 0, "blue" to 1, "black" to 2, "double-black" to 3)
    private val TERRAIN_BAND = mapOf(
        "green" to "green",
        "blue" to "blue",
        "park" to "blue",
        "red" to "black",
        "black" to "black",
        "mogul" to "black",
        "offpiste" to "black",
        "any" to "",
    )
    private val TERRAIN_TYPE_LEVEL_TERRAINS = mapOf(
        "mogul" to setOf("mogul", "any"),
        "piste" to setOf("green", "blue", "red", "black", "double-black", "any"),
        "park" to setOf("park", "any"),
        "offpiste" to setOf("offpiste", "any"),
    )

    data class CandidateScore(
        val level: LevelSpec,
        val fit: Double,
        val gate: Double,
        val prior: Double,
        val score: Double,
        val memberships: Map<String, Double>,
        val rejectedReason: String = "",
    ) {
        val eligible: Boolean get() = rejectedReason.isEmpty()
    }

    fun unusableReason(pack: MetricPack): String {
        if (pack.nFrames < MIN_FRAMES) return REASON_TOO_FEW_FRAMES
        if (!pack.scaleOk) return REASON_NO_BODY_SCALE
        if (pack.landmarkQuality < MIN_LANDMARK_QUALITY) return REASON_LOW_QUALITY
        if (pack.usableFrameRatio < MIN_USABLE_FRAME_RATIO) return REASON_FEW_USABLE_FRAMES
        return ""
    }

    fun qualityFactor(pack: MetricPack): Double {
        val quality = (pack.landmarkQuality / QUALITY_REF).coerceIn(0.0, 1.0)
        val usable = (pack.usableFrameRatio / USABLE_REF).coerceIn(0.0, 1.0)
        val view = if (pack.viewClass == "quarter") 1.0 else VIEW_PENALTY_SINGLE_PLANE
        return (quality * usable * view).coerceIn(0.0, 1.0)
    }

    fun candidateLevels(curriculum: Curriculum, pack: MetricPack): List<LevelSpec> {
        val allowed = pack.terrainType?.let { TERRAIN_TYPE_LEVEL_TERRAINS[it] }
        val out = ArrayList<LevelSpec>()
        val order = curriculum.levelIds.ifEmpty { curriculum.levels.keys.toList() }
        for (levelId in order) {
            val level = curriculum.levels[levelId] ?: continue
            if (!level.inScope) continue
            val tier = level.tier ?: "full"
            if (tier == "catalog") continue
            if (tier == "scene") {
                if (!sceneRequiresSatisfied(level, pack)) continue
            } else if (allowed != null && level.terrain !in allowed) {
                continue
            }
            out.add(level)
        }
        return out
    }

    fun missingSceneFacts(curriculum: Curriculum, pack: MetricPack): List<String> {
        val out = ArrayList<String>()
        for (levelId in curriculum.levelIds.ifEmpty { curriculum.levels.keys }) {
            val level = curriculum.levels[levelId] ?: continue
            if ((level.tier ?: "full") != "scene") continue
            if (sceneRequiresSatisfied(level, pack)) continue
            for (token in level.requiresScene) {
                val fact = token.substringBefore(":")
                val known = when (fact) {
                    "terrain_type" -> !pack.terrainType.isNullOrBlank()
                    "slope_band" -> !pack.slopeBand.isNullOrBlank()
                    "snow_surface" -> !pack.snowSurface.isNullOrBlank()
                    else -> false
                }
                if (!known && fact !in out) out.add(fact)
            }
        }
        return out
    }

    fun classify(
        pack: MetricPack,
        curriculum: Curriculum,
        history: StageHistory? = null,
        nameFor: (String) -> String = { it },
        maxCandidates: Int = 4,
    ): Classification {
        val blocked = unusableReason(pack)
        if (blocked.isNotEmpty()) {
            return Classification(method = "unusable", confidence = 0.0, unusableReason = blocked)
        }
        val rows = scoreCandidates(pack, curriculum, history)
        val eligible = rows.filter { it.eligible }
        if (eligible.isEmpty()) {
            val reason = if (rows.isNotEmpty()) REASON_NOTHING_MEASURED else REASON_NO_CANDIDATES
            return Classification(
                method = "unusable",
                confidence = 0.0,
                unusableReason = reason,
                candidates = rows.take(maxCandidates).map { rowToCandidate(it, nameFor(it.level.id)) },
            )
        }
        val top = eligible[0]
        val runner = eligible.getOrNull(1)
        val separation = top.score - (runner?.score ?: 0.0)
        val separationFactor = (separation / SEPARATION_SPAN).coerceIn(SEPARATION_FLOOR, 1.0)
        val factor = qualityFactor(pack)
        val confidence = (top.score * factor * separationFactor).coerceIn(0.0, 1.0)
        val ambiguous = confidence < CONF_GATE
        var shown = eligible.take(if (ambiguous) 2 else maxCandidates)
        if (!ambiguous) {
            val ageRejected = rows.filter {
                !it.eligible && it.rejectedReason == REASON_NOT_APPLICABLE_AGE
            }.take(2)
            shown = shown + ageRejected
        }
        val candidates = shown.map { row ->
            val sep = if (row === top) {
                "" to ""
            } else {
                separatingMetric(top, row) to MetricsBridge.displayName(separatingMetric(top, row), "en")
            }
            rowToCandidate(row, nameFor(row.level.id), sep)
        }
        return Classification(
            method = "scored_candidates",
            chosenId = top.level.id,
            confidence = round4(confidence),
            separation = round4(separation),
            qualityFactor = round4(factor),
            candidates = candidates,
            ambiguous = ambiguous,
        )
    }

    fun scoreCandidates(
        pack: MetricPack,
        curriculum: Curriculum,
        history: StageHistory? = null,
    ): List<CandidateScore> {
        val ageBand = pack.ageBand
        val excluded = evaluateExclusionRules(pack, curriculum.exclusionRules)
        val rows = ArrayList<CandidateScore>()
        for (level in candidateLevels(curriculum, pack)) {
            val (memberships, _) = memberships(pack, level, ageBand)
            val fit = fit(memberships, level.coreMetrics.size)
            val gate = gateRatio(pack, level, ageBand)
            var prior = prior(level, pack, curriculum, history)
            var rejected = ""
            if (ageExcluded(level, ageBand)) {
                rejected = REASON_NOT_APPLICABLE_AGE
                prior = 0.0
            } else if (level.id in excluded) {
                rejected = excluded.getValue(level.id)
            } else if (memberships.isEmpty()) {
                rejected = REASON_NOTHING_MEASURED
            }
            rows.add(
                CandidateScore(
                    level = level,
                    fit = fit,
                    gate = gate,
                    prior = prior,
                    score = W_FIT * fit + W_GATE * gate + W_PRIOR * prior,
                    memberships = memberships,
                    rejectedReason = rejected,
                ),
            )
        }
        return rows.sortedWith(compareByDescending<CandidateScore> { it.eligible }.thenByDescending { it.score })
    }

    private fun memberships(
        pack: MetricPack,
        level: LevelSpec,
        ageBand: String?,
    ): Pair<Map<String, Double>, Int> {
        val out = LinkedHashMap<String, Double>()
        for (metricId in level.coreMetrics) {
            val band = LevelBands.bandFor(level.id, metricId, ageBand)
            val eval = evaluateBand(band, pack.get(metricId))
            val m = eval.membership ?: continue
            out[metricId] = m
        }
        return out to out.size
    }

    private fun fit(memberships: Map<String, Double>, coreCount: Int): Double {
        if (memberships.isEmpty() || coreCount <= 0) return 0.0
        val mean = memberships.values.average()
        val coverage = memberships.size.toDouble() / coreCount.toDouble()
        return mean * (FIT_COVERAGE_FLOOR + (1.0 - FIT_COVERAGE_FLOOR) * coverage)
    }

    private fun gateRatio(pack: MetricPack, level: LevelSpec, ageBand: String?): Double {
        val gates = level.gateMetrics
        if (gates.isEmpty()) return 0.0
        var passed = 0
        for (metricId in gates) {
            val band = LevelBands.bandFor(level.id, metricId, ageBand)
            if (evaluateBand(band, pack.get(metricId)).passing) passed += 1
        }
        return passed.toDouble() / gates.size.toDouble()
    }

    private fun prior(
        level: LevelSpec,
        pack: MetricPack,
        curriculum: Curriculum,
        history: StageHistory?,
    ): Double {
        var prior = PRIOR_NEUTRAL
        if (history != null && !history.isEmpty) {
            val passed = history.passedLevels()
            val adjacent = HashSet<String>()
            for (lid in passed) {
                curriculum.levels[lid]?.nextLevels?.let { adjacent.addAll(it) }
            }
            val prereq = level.prerequisites.levels.toSet()
            if (level.id !in passed && (level.id in adjacent || (prereq.isNotEmpty() && prereq.all { it in passed }))) {
                prior += PRIOR_ADJACENT
            }
            if (level.id in passed) prior -= PRIOR_PASSED_PENALTY
        }
        val band = pack.slopeBand.orEmpty()
        val expected = TERRAIN_BAND[level.terrain].orEmpty()
        if (band.isNotBlank() && expected.isNotBlank()) {
            val distance = kotlin.math.abs(
                (BAND_ORDINAL[expected] ?: 0) - (BAND_ORDINAL[band] ?: 0),
            )
            prior += if (distance == 0) PRIOR_TERRAIN_MATCH else -PRIOR_TERRAIN_STEP * distance
        }
        return prior.coerceIn(0.0, 1.0)
    }

    private fun ageExcluded(level: LevelSpec, ageBand: String?): Boolean {
        if (ageBand.isNullOrBlank()) return false
        return level.profileNotes.any { it.id == ageBand && it.status == "not_applicable" }
    }

    private fun evaluateExclusionRules(
        pack: MetricPack,
        rules: List<ExclusionRule>,
    ): Map<String, String> {
        val rejected = LinkedHashMap<String, String>()
        val effective = if (rules.isEmpty()) {
            listOf(
                ExclusionRule(
                    whenMetrics = mapOf("stance_width_lte" to 0.37, "wedge_angle_lte" to 10.0),
                    rejectLevels = listOf("pizza_glide", "pizza", "wedge_christie"),
                    reason = REASON_PARALLEL_STANCE,
                ),
            )
        } else {
            rules
        }
        for (rule in effective) {
            if (rule.whenMetrics.all { (key, threshold) -> whenHolds(pack, key, threshold) }) {
                for (lid in rule.rejectLevels) {
                    rejected[lid] = rule.reason
                }
            }
        }
        return rejected
    }

    private fun whenHolds(pack: MetricPack, key: String, threshold: Double): Boolean {
        val (metricId, op) = when {
            key.endsWith("_lte") -> key.dropLast(4) to "lte"
            key.endsWith("_gte") -> key.dropLast(4) to "gte"
            else -> return false
        }
        val value = pack.get(metricId)?.takeIf { it.state == "ok" }?.value ?: return false
        return if (op == "lte") value <= threshold else value >= threshold
    }

    private fun sceneRequiresSatisfied(level: LevelSpec, pack: MetricPack): Boolean {
        if (level.requiresScene.isEmpty()) return true
        for (token in level.requiresScene) {
            val parts = token.split(":", limit = 2)
            val fact = parts[0]
            val allowed = if (parts.size > 1) parts[1].split("|") else emptyList()
            val value = when (fact) {
                "terrain_type" -> pack.terrainType
                "slope_band" -> pack.slopeBand
                "snow_surface" -> pack.snowSurface
                else -> null
            }
            if (value.isNullOrBlank()) return false
            if (allowed.isNotEmpty() && value !in allowed) return false
        }
        return true
    }

    private fun separatingMetric(top: CandidateScore, other: CandidateScore): String {
        val shared = top.memberships.keys.intersect(other.memberships.keys)
        val pool = if (shared.isNotEmpty()) shared else (top.memberships.keys + other.memberships.keys)
        var bestId = ""
        var bestGap = -1.0
        for (metricId in pool.sorted()) {
            val gap = kotlin.math.abs(
                (top.memberships[metricId] ?: 0.0) - (other.memberships[metricId] ?: 0.0),
            )
            if (gap > bestGap) {
                bestGap = gap
                bestId = metricId
            }
        }
        return bestId
    }

    private fun rowToCandidate(
        row: CandidateScore,
        name: String,
        separating: Pair<String, String> = "" to "",
    ): Candidate {
        return Candidate(
            stageId = row.level.id,
            stageName = name,
            score = round4(row.score),
            fit = round4(row.fit),
            gateRatio = round4(row.gate),
            prior = round4(row.prior),
            tier = row.level.tier ?: "full",
            separatingMetricId = separating.first,
            separatingMetricName = separating.second,
            rejectedReason = row.rejectedReason,
        )
    }

    private fun round4(v: Double): Double = kotlin.math.round(v * 10000.0) / 10000.0
}
