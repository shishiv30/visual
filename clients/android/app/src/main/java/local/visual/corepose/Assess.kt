package local.visual.corepose

object Assess {
    const val UNKNOWN = "unknown"
    const val SYS_CATEGORY = "unknown"
    const val CONF_GATE = 0.35
    const val QUALITY_GATE = 0.2

    fun classify(pack: FeaturePack): Triple<String, String, Double> {
        if (pack.n < 4 || pack.quality < QUALITY_GATE) {
            return Triple(SYS_CATEGORY, UNKNOWN, 0.0)
        }
        if (pack.kneeFlexAmp > 50.0 && pack.kneeFlexFreq > 0.8) {
            return mogulStage(pack)
        }
        if (pack.inwardLean >= 0.18 && pack.stanceWidth < 1.2) {
            val stage = when {
                pack.turnFreq >= 0.45 -> "carve_short"
                pack.turnFreq >= 0.32 -> "carve_medium"
                else -> "carve_long"
            }
            return Triple("alpine_piste", stage, 0.5)
        }
        if (pack.kneeFlexAmp > 35.0 && pack.kneeFlexFreq > 0.6 && pack.stanceWidth >= 1.2) {
            return mogulStage(pack)
        }
        if (pack.stanceWidth >= 1.2 && pack.kneeFlexFreq <= 0.6) {
            val conf = minOf(1.0, 0.4 + (pack.stanceWidth - 1.2))
            val stage = if (pack.turnFreq < 0.18) "pizza_glide" else "pizza"
            return Triple("alpine_piste", stage, conf)
        }
        if (pack.stanceWidthStd >= 0.22 && pack.stanceWidth >= 0.95 && pack.inwardLean < 0.18) {
            return Triple("alpine_piste", "wedge_christie", 0.55)
        }
        if (pack.stanceWidth < 1.1 && pack.turnFreq >= 0.45) {
            return Triple("alpine_piste", "skid_short", 0.5)
        }
        if (pack.stanceWidth < 1.1) {
            return Triple("alpine_piste", "parallel", 0.55)
        }
        return Triple(SYS_CATEGORY, UNKNOWN, 0.25)
    }

    fun assessClip(
        clipId: String,
        frames: List<AssessFrame>,
        fps: Double,
        curriculum: Curriculum,
        lang: String,
        scene: SceneContext? = null,
        knowledge: KnowledgePack? = null,
        history: StageHistory? = null,
        athleteAgeBand: String? = null,
    ): StageReport {
        val features = SportsSignals.extractFeatures(frames, fps)
        val turns = Turns.segment(frames, fps)
        val metricsPack = MetricPackBuilder.build(features, turns, scene, athleteAgeBand, fps)
        val nameFor: (String) -> String = { lid ->
            curriculum.levels[lid]?.let { text(it.name, lang) } ?: lid
        }
        var classification = ClassifyV3.classify(metricsPack, curriculum, history, nameFor)
        // If classify_v3 cannot score (sparse proxies), fall back to legacy ladder for stage id.
        if (classification.method == "unusable" || classification.chosenId.isBlank()) {
            val (legacyCat, legacyStage, legacyConf) = classify(features)
            if (legacyStage != UNKNOWN && curriculum.levels[legacyStage] != null) {
                val legacyLevel = curriculum.levels.getValue(legacyStage)
                classification = Classification(
                    method = "legacy_ladder",
                    chosenId = legacyStage,
                    confidence = legacyConf,
                    candidates = listOf(
                        Candidate(
                            stageId = legacyStage,
                            stageName = text(legacyLevel.name, lang),
                            score = legacyConf,
                            tier = legacyLevel.tier ?: "full",
                        ),
                    ),
                    ambiguous = legacyConf < CONF_GATE,
                    unusableReason = classification.unusableReason,
                )
            }
        }
        val stage = curriculum.levels[classification.chosenId]
        if (
            classification.method == "unusable" ||
            stage == null ||
            !stage.inScope ||
            classification.chosenId == UNKNOWN
        ) {
            return unknownReport(
                clipId, curriculum, lang, features, scene, turns, classification, metricsPack, history,
            )
        }
        val confidence = classification.confidence
        val scored = ScoreLevel.scoreLevel(metricsPack, stage, knowledge, lang)
        val results = ArrayList<KeypointResult>()
        var heuristic = stage.heuristicNotFisCarve
        for (cid in stage.checkpoints) {
            val spec = curriculum.checkpoints[cid] ?: continue
            results.add(evalCheckpoint(spec, features, curriculum, lang, turns))
            heuristic = heuristic || spec.heuristicNotFisCarve
        }
        val score = ScoreLevel.stageScore(scored, confidence)
        val requiredOk = requiredOk(results, stage, curriculum)
        val ready = ScoreLevel.readyForNextStage(
            scored, confidence, score, curriculum.passScore,
        ) && requiredOk
        val nextIds = ArrayList<String>()
        val nextNames = ArrayList<String>()
        val nextPlans = ArrayList<LevelPlan>()
        if (ready) {
            for (nid in stage.nextLevels) {
                val nxt = curriculum.levels[nid] ?: continue
                if (!nxt.inScope) continue
                nextIds.add(nid)
                nextNames.add(text(nxt.name, lang))
                nextPlans.add(levelPlan(nxt, curriculum, lang))
            }
        }
        val weakestRow = ScoreLevel.weakest(scored)
        val weakCheckpoint = if (ready) "" else weakestId(results)
        val catLoc = curriculum.categories[stage.categoryId]
        val catName = if (catLoc != null) text(catLoc, lang) else stage.categoryId
        val terrain = curriculum.terrains[stage.terrain]
        val sysDrill = curriculum.drills[curriculum.sysDrill]
        val kbStageId = KnowledgePackLoader.resolveKbStage(knowledge, stage.id, stage.kbStage)
        val focus = KnowledgeFocusBuilder.build(knowledge, kbStageId, scored, weakestRow, lang)
        val tree = SkillTree.buildTree(
            curriculum, stage.id, history, athleteAgeBand, lang, nameFor,
        )
        val filming = buildFilming(metricsPack, classification, lang)
        val trainingFocus = weakestRow?.let {
            I18n.t("Focus on {name}", mapOf("name" to it.report.name), lang = lang)
        }.orEmpty()
        val howToAdvance = when {
            ready && nextNames.isNotEmpty() ->
                I18n.t("Ready for {name}", mapOf("name" to nextNames[0]), lang = lang)
            weakestRow != null ->
                I18n.t("Improve {name} to advance", mapOf("name" to weakestRow.report.name), lang = lang)
            else -> ""
        }
        return StageReport(
            schemaVersion = "3.0.0",
            clipId = clipId,
            categoryId = stage.categoryId,
            stageId = stage.id,
            categoryName = catName,
            stageName = text(stage.name, lang),
            confidence = confidence.coerceIn(0.0, 1.0),
            readyForNextStage = ready,
            disclaimer = text(curriculum.disclaimer, lang),
            stageFocus = text(stage.desc, lang),
            trainingFocus = trainingFocus,
            howToAdvance = howToAdvance,
            score0100 = score,
            terrainId = stage.terrain,
            terrainName = if (terrain != null) text(terrain.name, lang) else "",
            terrainDesc = if (terrain != null) text(terrain.desc, lang) else "",
            weakestCheckpointId = weakCheckpoint,
            nextLevelIds = nextIds,
            nextLevelNames = nextNames,
            nextPlans = nextPlans,
            sessionPlan = stage.sessionDrills.mapNotNull { did ->
                curriculum.drills[did]?.let { drillPayload(it, curriculum, lang) }
            },
            treePath = SkillTree.treePathProjection(curriculum, stage.id, nameFor),
            filmSteps = sysDrill?.training?.map { text(it, lang) } ?: emptyList(),
            keypoints = results,
            scoreSeries = scoreSeries(stage, features, curriculum),
            heuristicNotFisCarve = heuristic,
            posture = Posture.scores(features, results),
            kbStage = kbStageId,
            tier = stage.tier ?: "full",
            classification = classification,
            metrics = scored.map { it.report },
            turns = Turns.toSummary(turns),
            tree = tree,
            knowledgeRef = if (kbStageId.isNotBlank() && knowledge != null) {
                KnowledgeRef(
                    kbStage = kbStageId,
                    packVersion = knowledge.packVersion,
                    levelId = stage.id,
                )
            } else {
                null
            },
            knowledgeFocus = focus,
            scene = SceneSummary(
                snowSurface = scene?.snowSurface.orEmpty(),
                slopeBand = scene?.slopeBand.orEmpty(),
                viewClass = metricsPack.viewClass,
                cameraMotion = scene?.cameraMotion.orEmpty(),
                fpsEffective = metricsPack.fpsEffective,
                missing = ClassifyV3.missingSceneFacts(curriculum, metricsPack),
                terrainType = scene?.terrainType.orEmpty(),
            ),
            filming = filming,
        )
    }

    private fun buildFilming(
        pack: MetricPack,
        classification: Classification,
        lang: String,
    ): List<FilmingIssue> {
        val issues = ArrayList<FilmingIssue>()
        if (pack.turnCount < 8) {
            issues.add(
                FilmingIssue(
                    code = "few_turns",
                    message = I18n.t("Film at least 8 linked turns when you can.", lang = lang),
                    severity = "info",
                ),
            )
        }
        if (classification.unusableReason.isNotBlank()) {
            issues.add(
                FilmingIssue(
                    code = classification.unusableReason,
                    message = I18n.t("Clip quality limited stage detection.", lang = lang),
                    severity = "warn",
                ),
            )
        }
        if (pack.viewClass != "quarter" && pack.viewClass.isNotBlank()) {
            issues.add(
                FilmingIssue(
                    code = "view",
                    message = I18n.t("A three-quarter view shows more of the technique.", lang = lang),
                    severity = "info",
                ),
            )
        }
        return issues
    }

    private fun mogulStage(pack: FeaturePack): Triple<String, String, Double> {
        val stage = if (pack.fallLine < 0.85 && pack.kneeFlexFreq > 1.1) {
            "mogul_fallline"
        } else {
            "mogul_absorb"
        }
        return Triple("alpine_moguls", stage, minOf(1.0, 0.45 + pack.kneeFlexFreq / 4.0))
    }

    private fun text(item: LocText, lang: String): String = CurriculumLoader.locText(item, lang)

    private fun requiredOk(
        results: List<KeypointResult>,
        stage: LevelSpec,
        cur: Curriculum,
    ): Boolean {
        val byId = results.associateBy { it.id }
        var scored = 0
        for (cid in stage.checkpoints) {
            val spec = cur.checkpoints[cid] ?: continue
            if (!spec.required) {
                continue
            }
            val item = byId[cid]
            if (item == null || item.score == null) {
                continue
            }
            scored += 1
            if (item.score < cur.checkpointPass) {
                return false
            }
        }
        return scored > 0
    }

    private fun weakestId(results: List<KeypointResult>): String {
        val known = results.filter { it.score != null }
        if (known.isEmpty()) {
            return results.firstOrNull()?.id.orEmpty()
        }
        return known.minBy { it.score ?: 0.0 }.id
    }

    private fun stageScore(
        results: List<KeypointResult>,
        confidence: Double,
        cur: Curriculum,
    ): Double {
        val pts = results.mapNotNull { item ->
            val spec = cur.checkpoints[item.id]
            if (item.score != null && spec != null && spec.required) item.score else null
        }
        if (pts.isEmpty()) {
            return 0.0
        }
        val raw = pts.average()
        return kotlin.math.round(raw * (0.8 + 0.2 * confidence) * 10.0) / 10.0
    }

    private fun continuousScore(value: Double, spec: Threshold): Double {
        return when (spec.op) {
            "gte" -> {
                val band = maxOf(kotlin.math.abs(spec.value) * 0.4, 0.08)
                piecewise(value, spec.value - band, spec.value, spec.value + band)
            }
            "lte" -> {
                val band = maxOf(kotlin.math.abs(spec.value) * 0.4, 0.08)
                val mirrored = spec.value - (value - spec.value)
                piecewise(mirrored, spec.value - band, spec.value, spec.value + band)
            }
            "between" -> {
                val hi = spec.hi ?: spec.value
                val lo = spec.value
                if (value in lo..hi) {
                    val mid = 0.5 * (lo + hi)
                    val span = maxOf((hi - lo) / 2.0, 1e-6)
                    val dist = kotlin.math.abs(value - mid) / span
                    kotlin.math.round((100.0 - 40.0 * dist) * 10.0) / 10.0
                } else {
                    val outside = if (value < lo) lo - value else value - hi
                    val width = maxOf(hi - lo, 0.08)
                    kotlin.math.round(maxOf(0.0, 60.0 * (1.0 - outside / width)) * 10.0) / 10.0
                }
            }
            else -> 0.0
        }
    }

    private fun piecewise(value: Double, lo: Double, mid: Double, hi: Double): Double {
        if (value <= lo) {
            return 0.0
        }
        if (value >= hi) {
            return 100.0
        }
        if (value < mid) {
            val t = (value - lo) / maxOf(mid - lo, 1e-6)
            return kotlin.math.round(60.0 * t * 10.0) / 10.0
        }
        val t = (value - mid) / maxOf(hi - mid, 1e-6)
        return kotlin.math.round((60.0 + 40.0 * t) * 10.0) / 10.0
    }

    private fun evalCheckpoint(
        spec: CheckpointSpec,
        pack: FeaturePack,
        cur: Curriculum,
        lang: String,
        turns: TurnSegmentation,
    ): KeypointResult {
        val key = MetricsBridge.measurementKey(spec)
        val value = if (key != null) SportsSignals.signalValue(pack, key) else null
        val score: Double?
        val status: KeypointStatus
        if (value == null) {
            status = KeypointStatus.UNKNOWN
            score = null
        } else {
            score = continuousScore(value, spec.threshold)
            status = if (score >= cur.checkpointPass) KeypointStatus.PASS else KeypointStatus.FAIL
        }
        val drills = if (status == KeypointStatus.FAIL) {
            spec.drills.mapNotNull { did -> cur.drills[did]?.let { drillPayload(it, cur, lang) } }
        } else {
            emptyList()
        }
        val evidence = if (status != KeypointStatus.UNKNOWN && key != null) {
            evidenceMs(spec, pack, passing = status == KeypointStatus.PASS, signal = key)
        } else {
            null
        }
        val desc = text(spec.desc, lang)
        return KeypointResult(
            id = spec.id,
            name = text(spec.name, lang),
            status = status,
            score = score,
            value = value,
            evidenceMs = evidence,
            good = desc,
            bad = desc,
            drills = drills,
            metricId = spec.metric.orEmpty(),
            totalTurns = turns.count.takeIf { it > 0 },
        )
    }

    private fun evidenceMs(
        spec: CheckpointSpec,
        pack: FeaturePack,
        passing: Boolean,
        signal: String,
    ): Double? {
        if (pack.series.isEmpty()) {
            return null
        }
        // Restrict the candidate pool to frames whose core landmarks (shoulders,
        // hips, knees, ankles) were confidently tracked, so a weakly-tracked
        // ankle/knee/hip never gets shown as photographic evidence of a fault
        // that was actually a skeleton glitch. Falls back to every sample if no
        // frame in the clip clears that stricter bar, so a low-quality clip
        // still gets an evidence link rather than none at all. This does not
        // change the metric's computed value/score -- only which frame is shown.
        val reliableSeries = pack.series.filter { it.reliable }
        val candidates = reliableSeries.ifEmpty { pack.series }
        val instant = ArrayList<Pair<Double, Double>>()
        for (sample in candidates) {
            val value = SportsSignals.sampleSignal(sample, signal) ?: continue
            instant.add(sample.tMs to continuousScore(value, spec.threshold))
        }
        if (instant.isNotEmpty()) {
            return if (passing) instant.maxBy { it.second }.first else instant.minBy { it.second }.first
        }
        if (signal in setOf("turn_freq", "fall_line")) {
            val scored = candidates.mapNotNull { s ->
                val hx = s.hipX ?: return@mapNotNull null
                s.tMs to kotlin.math.abs(hx - pack.hipXMean)
            }
            if (scored.isEmpty()) {
                return candidates.first().tMs
            }
            return scored.maxBy { it.second }.first
        }
        if (signal in setOf("knee_flex_freq", "knee_flex_amp")) {
            val scored = candidates.mapNotNull { s ->
                val flex = s.kneeFlex ?: return@mapNotNull null
                s.tMs to flex
            }
            if (scored.isEmpty()) {
                return candidates.first().tMs
            }
            return scored.maxBy { it.second }.first
        }
        if (signal == "stance_width_std") {
            val scored = candidates.mapNotNull { s ->
                val w = s.stanceWidth ?: return@mapNotNull null
                s.tMs to kotlin.math.abs(w - pack.stanceWidth)
            }
            if (scored.isEmpty()) {
                return candidates.first().tMs
            }
            return scored.maxBy { it.second }.first
        }
        return candidates.first().tMs
    }

    private fun scoreSeries(
        stage: LevelSpec,
        pack: FeaturePack,
        cur: Curriculum,
    ): List<FrameScorePoint> {
        val specs = stage.checkpoints.mapNotNull { cid ->
            val spec = cur.checkpoints[cid]
            if (spec != null && spec.required) spec else null
        }
        val points = ArrayList<FrameScorePoint>()
        for (sample in pack.series) {
            val scores = ArrayList<Double>()
            for (spec in specs) {
                val key = MetricsBridge.measurementKey(spec) ?: continue
                var value = SportsSignals.sampleSignal(sample, key)
                if (value == null) {
                    value = SportsSignals.signalValue(pack, key)
                }
                if (value == null) {
                    continue
                }
                scores.add(continuousScore(value, spec.threshold))
            }
            if (scores.isEmpty()) {
                continue
            }
            points.add(
                FrameScorePoint(
                    tMs = sample.tMs,
                    score = kotlin.math.round(scores.average() * 10.0) / 10.0,
                ),
            )
        }
        return points
    }

    private fun venuePayload(cur: Curriculum, venueId: String, lang: String): VenuePayload? {
        val venue = cur.venues[venueId] ?: return null
        return VenuePayload(
            id = venue.id,
            name = text(venue.name, lang),
            desc = text(venue.desc, lang),
            tips = text(venue.tips, lang),
            terrain = venue.terrain,
        )
    }

    private fun drillPayload(drill: DrillSpec, cur: Curriculum, lang: String): DrillPayload {
        val venues = drill.venueIds.mapNotNull { venuePayload(cur, it, lang) }
        val training = drill.training.map { text(it, lang) }
        return DrillPayload(
            id = drill.id,
            title = text(drill.name, lang),
            name = text(drill.name, lang),
            desc = text(drill.desc, lang),
            steps = training,
            training = training,
            venues = venues,
        )
    }

    private fun levelPlan(stage: LevelSpec, cur: Curriculum, lang: String): LevelPlan {
        val drills = stage.sessionDrills.mapNotNull { did ->
            cur.drills[did]?.let { drillPayload(it, cur, lang) }
        }
        val venues = stage.venueIds.mapNotNull { venuePayload(cur, it, lang) }
        return LevelPlan(
            levelId = stage.id,
            levelName = text(stage.name, lang),
            drills = drills,
            venues = venues,
        )
    }

    private fun treePath(cur: Curriculum, stageId: String, lang: String): List<TreeNode> {
        val parent = HashMap<String, String>()
        for ((lid, spec) in cur.levels) {
            for (nid in spec.nextLevels) {
                parent.putIfAbsent(nid, lid)
            }
        }
        val chain = ArrayList<String>()
        var cursor = stageId
        val seen = HashSet<String>()
        while (cursor.isNotEmpty() && cursor !in seen) {
            seen.add(cursor)
            chain.add(cursor)
            cursor = parent[cursor].orEmpty()
        }
        chain.reverse()
        val nodes = ArrayList<TreeNode>()
        for (lid in chain) {
            val spec = cur.levels[lid] ?: continue
            nodes.add(TreeNode(id = lid, name = text(spec.name, lang), current = lid == stageId))
        }
        cursor = stageId
        val seenFuture = nodes.map { it.id }.toMutableSet()
        while (true) {
            val spec = cur.levels[cursor] ?: break
            if (spec.nextLevels.isEmpty()) {
                break
            }
            val nxt = spec.nextLevels[0]
            if (nxt in seenFuture) {
                break
            }
            val nextSpec = cur.levels[nxt] ?: break
            nodes.add(TreeNode(id = nxt, name = text(nextSpec.name, lang), current = false))
            seenFuture.add(nxt)
            cursor = nxt
        }
        return nodes
    }

    private fun unknownReport(
        clipId: String,
        cur: Curriculum,
        lang: String,
        pack: FeaturePack,
        scene: SceneContext? = null,
        turns: TurnSegmentation = TurnSegmentation(emptyList()),
        classification: Classification? = null,
        metricsPack: MetricPack? = null,
        history: StageHistory? = null,
    ): StageReport {
        val drill = cur.drills[cur.sysDrill]
        val payload = if (drill != null) drillPayload(drill, cur, lang) else DrillPayload()
        val nameFor: (String) -> String = { lid ->
            cur.levels[lid]?.let { text(it.name, lang) } ?: lid
        }
        return StageReport(
            schemaVersion = "3.0.0",
            clipId = clipId,
            categoryId = SYS_CATEGORY,
            stageId = UNKNOWN,
            categoryName = I18n.t("Unknown", lang = lang),
            stageName = I18n.t("Re-film", lang = lang),
            confidence = minOf(pack.quality, 0.34),
            readyForNextStage = false,
            disclaimer = text(cur.disclaimer, lang),
            weakestCheckpointId = "KP-SYS-01",
            filmSteps = drill?.training?.map { text(it, lang) } ?: emptyList(),
            keypoints = listOf(
                KeypointResult(
                    id = "KP-SYS-01",
                    name = if (drill != null) text(drill.name, lang) else "",
                    status = KeypointStatus.UNKNOWN,
                    good = if (drill != null) text(drill.name, lang) else "",
                    bad = I18n.t(
                        "Stage cannot be judged when the shot is unstable, occluded, or out of curriculum scope.",
                        lang = lang,
                    ),
                    drills = listOf(payload),
                ),
            ),
            posture = Posture.scores(pack, emptyList()),
            classification = classification,
            scene = SceneSummary(
                snowSurface = scene?.snowSurface.orEmpty(),
                slopeBand = scene?.slopeBand.orEmpty(),
                viewClass = metricsPack?.viewClass.orEmpty(),
                cameraMotion = scene?.cameraMotion.orEmpty(),
                fpsEffective = metricsPack?.fpsEffective,
                missing = metricsPack?.let { ClassifyV3.missingSceneFacts(cur, it) }.orEmpty(),
                terrainType = scene?.terrainType.orEmpty(),
            ),
            turns = Turns.toSummary(turns),
            tree = SkillTree.buildTree(cur, UNKNOWN, history, null, lang, nameFor),
            filming = listOf(
                FilmingIssue(
                    code = classification?.unusableReason?.ifBlank { "unusable" } ?: "unusable",
                    message = I18n.t("Clip quality limited stage detection.", lang = lang),
                    severity = "warn",
                ),
            ),
        )
    }
}
