package local.visual.corepose

import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.util.AttributeSet
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView

class ReportPanelView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : LinearLayout(context, attrs) {
    var onSeek: ((Int) -> Unit)? = null
    var onCorrectResult: (() -> Unit)? = null
    var knowledgePack: KnowledgePack? = null

    private data class ChapterSpec(val titleKey: String, val collapsible: Boolean = false)

    private val chapterSpecs = listOf(
        ChapterSpec("Summary"),
        ChapterSpec("Why this stage"),
        ChapterSpec("Core metrics"),
        ChapterSpec("Turn-by-turn"),
        ChapterSpec("Checkpoints"),
        ChapterSpec("Skill tree"),
        ChapterSpec("Stage tutorial", collapsible = true),
        ChapterSpec("Drills", collapsible = true),
        ChapterSpec("Faults and fixes", collapsible = true),
        ChapterSpec("Terrain and venue", collapsible = true),
        ChapterSpec("Equipment", collapsible = true),
        ChapterSpec("Filming and disclaimer"),
    )

    private val empty = TextView(context)
    private val chapters = Array(chapterSpecs.size) { LinearLayout(context) }
    private val titles = Array(chapterSpecs.size) { TextView(context) }
    private val blocks = Array(chapterSpecs.size) { LinearLayout(context) }
    private val collapsed = BooleanArray(chapterSpecs.size) { chapterSpecs[it].collapsible }
    private var report: StageReport? = null

    init {
        orientation = VERTICAL
        val pad = dp(ReportTheme.REPORT_INSET)
        setPadding(pad, pad, pad, pad)
        empty.setTextColor(ReportTheme.TITLE)
        empty.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
        addView(empty, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        for (i in chapterSpecs.indices) {
            titles[i].setTextColor(ReportTheme.TITLE)
            titles[i].setTextSize(TypedValue.COMPLEX_UNIT_SP, 32f)
            titles[i].setPadding(0, 0, 0, dp(ReportTheme.SPACE_TEXT))
            if (chapterSpecs[i].collapsible) {
                titles[i].setOnClickListener {
                    collapsed[i] = !collapsed[i]
                    chapters[i].visibility = if (collapsed[i]) GONE else VISIBLE
                }
            }
            chapters[i].orientation = VERTICAL
            blocks[i].orientation = VERTICAL
            blocks[i].addView(titles[i], LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            blocks[i].addView(chapters[i], LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            addView(
                blocks[i],
                LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply {
                    topMargin = if (i == 0) 0 else dp(ReportTheme.SPACE_CHAPTER)
                },
            )
        }
        retranslate()
        bind(null)
    }

    fun retranslate() {
        empty.text = I18n.t("No stage report yet. Analyze a clip offline first.")
        for (i in chapterSpecs.indices) {
            titles[i].text = I18n.t(chapterSpecs[i].titleKey)
        }
        bind(report)
    }

    private fun finishChapter(index: Int): Boolean {
        applyVerticalGaps(chapters[index], dp(ReportTheme.SPACE_PANEL))
        val has = chapters[index].childCount > 0
        blocks[index].visibility = if (has) VISIBLE else GONE
        if (has && chapterSpecs[index].collapsible) {
            chapters[index].visibility = if (collapsed[index]) GONE else VISIBLE
        }
        return has
    }

    fun bind(next: StageReport?) {
        report = next
        val has = next != null
        empty.visibility = if (has) GONE else VISIBLE
        for (i in chapterSpecs.indices) {
            blocks[i].visibility = GONE
            chapters[i].removeAllViews()
        }
        if (next == null) {
            return
        }
        fillSummary(next)
        fillWhy(next)
        fillMetrics(next)
        fillTurns(next)
        fillCheckpoints(next)
        fillTree(next)
        fillTutorial(next)
        fillDrills(next)
        fillFaults(next)
        fillTerrain(next)
        fillEquipment(next)
        fillFilming(next)
    }

    private fun fillSummary(report: StageReport) {
        val ambiguous = report.classification?.ambiguous == true
        val title = if (ambiguous) {
            val names = report.classification?.candidates
                ?.take(2)
                ?.map { it.stageName.ifBlank { it.stageId } }
                ?.filter { it.isNotBlank() }
                .orEmpty()
            if (names.isNotEmpty()) {
                "${I18n.t("Possible stage")}: ${names.joinToString(" · ")}"
            } else {
                report.stageName
            }
        } else {
            report.stageName
        }
        val overview = card()
        overview.addView(iconRow(listOf(ReportTheme.medalColor(report.stageId) to "trophy"), title))
        if (report.stageFocus.isNotBlank()) {
            overview.addView(meta(report.stageFocus))
        }
        chapters[0].addView(wrapCard(overview), panelParams())

        val trailCard = card()
        val trail = report.terrainName.ifBlank { I18n.t("—") }
        val diamonds = ReportTheme.terrainDiamondColors(report.terrainId).map { it to "diamond" }
        trailCard.addView(iconRow(diamonds, "${I18n.t("Suggested trail rating")}: $trail"))
        if (report.terrainDesc.isNotBlank()) {
            trailCard.addView(meta(report.terrainDesc))
        }
        chapters[0].addView(wrapCard(trailCard), panelParams())

        val gateCard = card()
        val gate = if (report.readyForNextStage) {
            I18n.t("Passed this level. Choose a next level on the skill tree.")
        } else {
            I18n.t("Not passed — train the lowest-scoring checkpoint.")
        }
        gateCard.addView(advice(gate))
        chapters[0].addView(wrapCard(gateCard), panelParams())

        val confLabel = if (ambiguous) {
            I18n.t("Leading candidate")
        } else {
            I18n.t("Confidence")
        }
        addRingRow(
            chapters[0],
            listOf(
                Triple(report.score0100, I18n.t("Heuristic score (0-100, not FIS)"), ReportTheme.scorePurple(report.score0100)),
                Triple(report.confidence * 100.0, confLabel, ReportTheme.scorePurple(report.confidence * 100.0)),
            ),
        )

        val posture = report.posture
        if (posture != null) {
            val note = card()
            note.addView(
                meta(
                    I18n.t(
                        "Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure.",
                    ),
                ),
            )
            chapters[0].addView(wrapCard(note), panelParams())
            addRingRow(
                chapters[0],
                listOf(
                    Triple(posture.stability, I18n.t("Stability"), ReportTheme.scorePurple(posture.stability)),
                    Triple(posture.coordination, I18n.t("Coordination"), ReportTheme.scorePurple(posture.coordination)),
                    Triple(posture.control, I18n.t("Control"), ReportTheme.scorePurple(posture.control)),
                    Triple(posture.balance, I18n.t("Balance"), ReportTheme.scorePurple(posture.balance)),
                ),
            )
        }

        if (report.scoreSeries.isNotEmpty()) {
            val timelineCard = card()
            timelineCard.addView(meta(I18n.t("Stability over time (time × frame score)")))
            val chart = ScoreTimelineView(context)
            chart.setPoints(report.scoreSeries)
            chart.onSeek = { ms -> onSeek?.invoke(ms) }
            timelineCard.addView(chart, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            chapters[0].addView(wrapCard(timelineCard), panelParams())
        }

        val correct = TextView(context).apply {
            text = I18n.t("Correct result")
            setTextColor(ReportTheme.LINK)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setOnClickListener { onCorrectResult?.invoke() }
        }
        val correctCard = card()
        correctCard.addView(correct)
        chapters[0].addView(wrapCard(correctCard), panelParams())
        finishChapter(0)
    }

    private fun fillWhy(report: StageReport) {
        val info = report.classification
        val scene = report.scene
        if (info == null && scene == null) {
            finishChapter(1)
            return
        }
        if (info != null) {
            if (info.ambiguous) {
                val note = card()
                note.addView(advice(I18n.t("Possible stage — confidence is below the gate, so both candidates are shown.")))
                chapters[1].addView(wrapCard(note), panelParams())
            }
            val ranked = info.candidates.take(2)
            ranked.forEachIndexed { i, c ->
                val card = card()
                val rank = if (i == 0) I18n.t("Best match") else I18n.t("Runner-up")
                val label = c.stageName.ifBlank { c.stageId }
                card.addView(advice("$rank: $label"))
                card.addView(
                    meta(
                        "fit ${pct(c.fit)} · gate ${pct(c.gateRatio)} · prior ${pct(c.prior)} · score ${pct(c.score)}",
                    ),
                )
                if (c.separatingMetricName.isNotBlank() || c.separatingMetricId.isNotBlank()) {
                    val sep = c.separatingMetricName.ifBlank {
                        MetricsBridge.displayName(c.separatingMetricId, I18n.language())
                    }
                    card.addView(meta("${I18n.t("Separating metric")}: $sep"))
                }
                if (c.rejectedReason.isNotBlank()) {
                    card.addView(meta(c.rejectedReason))
                }
                chapters[1].addView(wrapCard(card), panelParams())
            }
            if (info.qualityFactor > 0 && info.qualityFactor < 0.999) {
                val q = card()
                q.addView(meta("${I18n.t("Quality factor")}: ${pct(info.qualityFactor)}"))
                chapters[1].addView(wrapCard(q), panelParams())
            }
        }
        if (scene != null) {
            val chips = ArrayList<String>()
            sceneLabel(scene.viewClass, viewLabels)?.let { chips.add(it) }
            sceneLabel(scene.cameraMotion, cameraLabels)?.let { chips.add(it) }
            sceneLabel(scene.snowSurface, snowLabels)?.let { chips.add(it) }
            sceneLabel(scene.slopeBand, slopeLabels)?.let { chips.add(it) }
            sceneLabel(scene.terrainType, terrainLabels)?.let { chips.add(it) }
            scene.fpsEffective?.let { chips.add(String.format("%.0f fps", it)) }
            for (miss in scene.missing) {
                chips.add("${I18n.t("Needs a scene fact")}: $miss")
            }
            if (chips.isNotEmpty()) {
                val card = card()
                card.addView(meta(chips.joinToString(" · ")))
                chapters[1].addView(wrapCard(card), panelParams())
            }
        }
        finishChapter(1)
    }

    private fun pct(v: Double): String = "${(v * 100).toInt()}%"

    private val viewLabels = mapOf(
        "profile" to "Profile view",
        "quarter" to "Three-quarter view",
        "frontal" to "Front view",
    )
    private val cameraLabels = mapOf(
        "static" to "Static camera",
        "panning" to "Panning camera",
        "follow" to "Follow camera",
    )
    private val snowLabels = mapOf(
        "corduroy" to "Corduroy",
        "packed" to "Packed",
        "hardpack" to "Hardpack",
        "ice" to "Ice",
        "soft" to "Soft",
        "powder" to "Powder",
        "crud" to "Crud",
        "slush" to "Slush",
    )
    private val slopeLabels = mapOf(
        "green" to "Green run",
        "blue" to "Blue run",
        "black" to "Black run",
        "double-black" to "Double black run",
    )
    private val terrainLabels = mapOf(
        "piste" to "Groomed piste",
        "mogul" to "Mogul run",
        "park" to "Terrain park",
        "offpiste" to "Off-piste / powder",
    )

    private fun sceneLabel(raw: String, map: Map<String, String>): String? {
        if (raw.isBlank()) {
            return null
        }
        val key = map[raw] ?: return raw
        return I18n.t(key)
    }

    private fun fillMetrics(report: StageReport) {
        if (report.metrics.isEmpty()) {
            finishChapter(2)
            return
        }
        val legend = card()
        legend.addView(meta(I18n.t("Gate metrics decide advancement; diagnostic metrics explain the skiing.")))
        chapters[2].addView(wrapCard(legend), panelParams())
        val perRow = 2
        var row: LinearLayout? = null
        report.metrics.forEachIndexed { i, m ->
            if (i % perRow == 0) {
                row = equalHeightRow()
                chapters[2].addView(row, panelParams())
            }
            val card = card()
            val label = m.name.ifBlank { MetricsBridge.displayName(m.id, I18n.language()) }
            card.addView(advice(label))
            val kind = if (m.isGate) I18n.t("Gate") else I18n.t("Diagnostic")
            val rubric = when (m.rubric) {
                Rubric.STRONG -> I18n.t("Strong")
                Rubric.PASS -> I18n.t("Pass")
                Rubric.NOT_YET -> I18n.t("Not yet")
                else -> I18n.t("Not rated")
            }
            card.addView(meta("$kind · $rubric"))
            if (m.state == MetricState.OK && m.score != null) {
                val ring = ScoreRingView(context)
                ring.setScore(m.score, m.display.ifBlank { label }, ReportTheme.scorePurple(m.score))
                card.addView(ring, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            } else {
                val stateText = when (m.state) {
                    MetricState.NOT_APPLICABLE -> I18n.t("Not applicable")
                    else -> I18n.t("Not measured")
                }
                card.addView(meta(stateText))
                if (m.reason.isNotBlank()) card.addView(meta(m.reason))
            }
            if (m.standard.isNotBlank()) {
                card.addView(meta("${I18n.t("Standard")}: ${m.standard}"))
            }
            if (m.reliability > 0) {
                card.addView(meta("${I18n.t("Reliability")}: ${pct(m.reliability)}"))
            }
            if (m.leftValue != null || m.rightValue != null) {
                card.addView(
                    meta(
                        "L ${m.leftValue?.let { String.format("%.2f", it) } ?: "—"} · R ${
                            m.rightValue?.let { String.format("%.2f", it) } ?: "—"
                        }",
                    ),
                )
            }
            if (m.faultyTurns != null && m.totalTurns != null) {
                card.addView(
                    meta(
                        I18n.t(
                            "{n} of {total} turns",
                            mapOf("n" to m.faultyTurns.toString(), "total" to m.totalTurns.toString()),
                        ),
                    ),
                )
            }
            if (m.evidenceMs != null) {
                card.addView(seekLink(ReportTheme.formatEvidenceMs(m.evidenceMs), m.evidenceMs.toInt()))
            }
            row?.addView(wrapCard(card), rowCellParams(i, perRow))
        }
        finishChapter(2)
    }

    private fun fillTurns(report: StageReport) {
        val turns = report.turns
        if (turns == null || turns.count <= 0) {
            finishChapter(3)
            return
        }
        val card = card()
        card.addView(
            advice(
                I18n.t(
                    "{n} turns · {left} left / {right} right",
                    mapOf(
                        "n" to turns.count.toString(),
                        "left" to turns.leftCount.toString(),
                        "right" to turns.rightCount.toString(),
                    ),
                ),
            ),
        )
        turns.meanDurationS?.let { mean ->
            card.addView(
                meta(I18n.t("Mean turn {sec:.2f}s", mapOf("sec" to String.format("%.2f", mean)))),
            )
        }
        turns.durationCv?.let { cv ->
            card.addView(meta("${I18n.t("Rhythm CV")}: ${String.format("%.0f", cv * 100)}%"))
        }
        if (turns.faultCounts.isNotEmpty()) {
            val faults = turns.faultCounts.entries.joinToString(" · ") { (k, v) ->
                "${MetricsBridge.displayName(k, I18n.language())}: $v"
            }
            card.addView(meta(faults))
        }
        val strip = TurnStripView(context)
        strip.setTurns(turns.turns)
        strip.onSeek = { ms -> onSeek?.invoke(ms) }
        card.addView(strip, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        for (t in turns.turns.take(12)) {
            val dir = when (t.side.uppercase()) {
                "L" -> I18n.t("Left")
                "R" -> I18n.t("Right")
                else -> t.side
            }
            val flag = if (t.flags.isNotEmpty()) " · ${t.flags.joinToString(",")}" else ""
            card.addView(
                seekLink(
                    "#${t.index + 1} $dir · ${t.durationS.format1()}s$flag",
                    t.tStartMs.toInt(),
                ),
            )
        }
        chapters[3].addView(wrapCard(card), panelParams())
        finishChapter(3)
    }

    private fun fillCheckpoints(report: StageReport) {
        val kps = ReportTheme.sortedKeypoints(report.keypoints)
        if (kps.isEmpty()) {
            finishChapter(4)
            return
        }
        val weak = kps.firstOrNull { it.id == report.weakestCheckpointId } ?: kps.firstOrNull {
            it.status == KeypointStatus.FAIL
        }
        if (weak != null && !report.readyForNextStage) {
            val head = card()
            head.addView(advice("${I18n.t("Weakest checkpoint")}: ${weak.name.ifBlank { weak.id }}"))
            head.addView(meta(if (weak.status == KeypointStatus.PASS) I18n.t("Pass") else I18n.t("Not yet")))
            chapters[4].addView(wrapCard(head), panelParams())
        }
        val perRow = if (kps.size >= 5) 3 else 2
        var row: LinearLayout? = null
        kps.forEachIndexed { i, item ->
            if (i % perRow == 0) {
                row = equalHeightRow()
                chapters[4].addView(row, panelParams())
            }
            val card = card()
            val ring = ScoreRingView(context)
            ring.setScore(item.score, item.name.ifBlank { item.id }, ReportTheme.scorePurple(item.score))
            card.addView(ring, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            val status = when (item.status) {
                KeypointStatus.PASS -> I18n.t("Pass")
                KeypointStatus.FAIL -> I18n.t("Not yet")
                else -> I18n.t("Not measured")
            }
            card.addView(meta(status))
            val detail = if (item.status == KeypointStatus.PASS) item.good else item.bad
            card.addView(advice(detail))
            if (item.faultyTurns != null && item.totalTurns != null) {
                card.addView(
                    meta(
                        I18n.t(
                            "{n} of {total} turns",
                            mapOf("n" to item.faultyTurns.toString(), "total" to item.totalTurns.toString()),
                        ),
                    ),
                )
            }
            if (item.evidenceMs != null) {
                card.addView(seekLink(ReportTheme.formatEvidenceMs(item.evidenceMs), item.evidenceMs.toInt()))
            }
            if (item.drills.isNotEmpty() && item.status == KeypointStatus.FAIL) {
                addLines(card, drillLines(item.drills, emptyList()), paper = true)
            }
            row?.addView(wrapCard(card), rowCellParams(i, perRow))
        }
        finishChapter(4)
    }

    private fun fillTree(report: StageReport) {
        if (report.tree.isEmpty() && report.treePath.isEmpty() && report.nextPlans.isEmpty()) {
            finishChapter(5)
            return
        }
        if (report.tree.isNotEmpty()) {
            val card = card()
            val tree = SkillTreeView(context)
            tree.setTree(report.tree)
            card.addView(tree, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            if (report.nextLevelNames.isNotEmpty()) {
                card.addView(meta("${I18n.t("Next stage")}: ${report.nextLevelNames.joinToString(" · ")}"))
            }
            chapters[5].addView(wrapCard(card), panelParams())
        } else if (report.treePath.isNotEmpty()) {
            val card = card()
            val tree = SkillTreeView(context)
            tree.setRoute(report.treePath)
            card.addView(tree, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            chapters[5].addView(wrapCard(card), panelParams())
        }
        for (plan in report.nextPlans) {
            chapters[5].addView(wrapCard(planCard(plan)), panelParams())
        }
        finishChapter(5)
    }

    private fun kbStage(report: StageReport): KnowledgeStageSlice? {
        val pack = knowledgePack ?: return null
        val id = report.knowledgeRef?.kbStage?.ifBlank { report.kbStage }.orEmpty()
        if (id.isBlank()) return null
        return pack.stages[id]
    }

    private fun fillTutorial(report: StageReport) {
        val stage = kbStage(report)
        if (stage == null) {
            finishChapter(6)
            return
        }
        val lang = I18n.language()
        val focusIds = report.knowledgeFocus?.skillIds.orEmpty()
        val skills = if (focusIds.isNotEmpty()) {
            focusIds.mapNotNull { id -> stage.skillEntities.firstOrNull { it.id == id } }
        } else {
            stage.skillEntities
        }
        if (skills.isNotEmpty()) {
            for (skill in skills) {
                val card = card()
                card.addView(advice(KnowledgePackLoader.text(skill.name, lang)))
                val goal = KnowledgePackLoader.text(skill.description, lang)
                if (goal.isNotBlank()) card.addView(meta(goal))
                val why = KnowledgePackLoader.text(skill.why, lang)
                if (why.isNotBlank()) card.addView(meta(why))
                for (cue in skill.cues) {
                    val t = KnowledgePackLoader.text(cue, lang)
                    if (t.isNotBlank()) card.addView(advice("• $t"))
                }
                chapters[6].addView(wrapCard(card), panelParams())
            }
        } else {
            val lines = listOf(
                KnowledgePackLoader.text(stage.oneLine, lang),
                KnowledgePackLoader.text(stage.goal, lang),
                KnowledgePackLoader.text(stage.why, lang),
            ).filter { it.isNotBlank() }
            if (lines.isNotEmpty()) {
                val card = card()
                addLines(card, lines.map { "• $it" }, paper = true)
                chapters[6].addView(wrapCard(card), panelParams())
            }
        }
        finishChapter(6)
    }

    private fun fillDrills(report: StageReport) {
        val stage = kbStage(report) ?: run {
            finishChapter(7)
            return
        }
        val lang = I18n.language()
        val focusIds = report.knowledgeFocus?.drillIds.orEmpty()
        val drills = if (focusIds.isNotEmpty()) {
            focusIds.mapNotNull { id -> stage.drillEntities.firstOrNull { it.id == id } }
        } else {
            stage.drillEntities
        }
        if (drills.isEmpty()) {
            finishChapter(7)
            return
        }
        for (drill in drills.take(8)) {
            val card = card()
            card.addView(advice(KnowledgePackLoader.text(drill.name, lang)))
            val purpose = KnowledgePackLoader.text(drill.purpose, lang)
            if (purpose.isNotBlank()) card.addView(meta(purpose))
            val setup = KnowledgePackLoader.text(drill.setup, lang)
            if (setup.isNotBlank()) card.addView(meta("${I18n.t("Setup")}: $setup"))
            if (drill.dose.isNotBlank()) card.addView(meta("${I18n.t("Dose")}: ${drill.dose}"))
            for (step in drill.steps) {
                val t = KnowledgePackLoader.text(step, lang)
                if (t.isNotBlank()) card.addView(advice("• $t"))
            }
            chapters[7].addView(wrapCard(card), panelParams())
        }
        finishChapter(7)
    }

    private fun fillFaults(report: StageReport) {
        val stage = kbStage(report) ?: run {
            finishChapter(8)
            return
        }
        val lang = I18n.language()
        val focusIds = report.knowledgeFocus?.faultIds.orEmpty()
        val faults = if (focusIds.isNotEmpty()) {
            focusIds.mapNotNull { id -> stage.faultEntities.firstOrNull { it.id == id } }
        } else {
            stage.faultEntities
        }
        if (faults.isEmpty()) {
            finishChapter(8)
            return
        }
        for (fault in faults.take(8)) {
            val card = card()
            card.addView(advice(KnowledgePackLoader.text(fault.name, lang).ifBlank {
                KnowledgePackLoader.text(fault.looksLike, lang)
            }))
            val looks = KnowledgePackLoader.text(fault.looksLike, lang)
            if (looks.isNotBlank()) card.addView(meta(looks))
            val symptom = KnowledgePackLoader.text(fault.symptom, lang)
            if (symptom.isNotBlank()) card.addView(meta(symptom))
            val injury = KnowledgePackLoader.text(fault.injuryRisk, lang)
            if (injury.isNotBlank()) card.addView(meta(injury))
            for (cue in fault.cues) {
                val t = KnowledgePackLoader.text(cue, lang)
                if (t.isNotBlank()) card.addView(advice("• $t"))
            }
            chapters[8].addView(wrapCard(card), panelParams())
        }
        finishChapter(8)
    }

    private fun fillTerrain(report: StageReport) {
        val stage = kbStage(report)
        val lang = I18n.language()
        val entities = stage?.terrainEntities.orEmpty()
        val tactics = stage?.tactics.orEmpty()
        if (entities.isEmpty() && tactics.isEmpty() && report.terrainDesc.isBlank()) {
            finishChapter(9)
            return
        }
        if (report.terrainName.isNotBlank() || report.terrainDesc.isNotBlank()) {
            val card = card()
            if (report.terrainName.isNotBlank()) card.addView(advice(report.terrainName))
            if (report.terrainDesc.isNotBlank()) card.addView(meta(report.terrainDesc))
            chapters[9].addView(wrapCard(card), panelParams())
        }
        for (item in entities) {
            val card = card()
            val name = KnowledgePackLoader.text(item.name, lang)
            val desc = KnowledgePackLoader.text(item.desc, lang)
            if (name.isNotBlank()) card.addView(advice(name))
            if (desc.isNotBlank()) card.addView(meta(desc))
            chapters[9].addView(wrapCard(card), panelParams())
        }
        if (tactics.isNotEmpty()) {
            val card = card()
            for (t in tactics) {
                val line = KnowledgePackLoader.text(t, lang)
                if (line.isNotBlank()) card.addView(advice("• $line"))
            }
            chapters[9].addView(wrapCard(card), panelParams())
        }
        finishChapter(9)
    }

    private fun fillEquipment(report: StageReport) {
        val stage = kbStage(report)
        val lang = I18n.language()
        val entities = stage?.equipmentEntities.orEmpty()
        val profile = report.profileSummary
        if (entities.isEmpty() && profile == null) {
            finishChapter(10)
            return
        }
        for (item in entities) {
            val card = card()
            val name = KnowledgePackLoader.text(item.name, lang)
            val desc = KnowledgePackLoader.text(item.desc, lang)
            if (name.isNotBlank()) card.addView(advice(name))
            if (desc.isNotBlank()) card.addView(meta(desc))
            chapters[10].addView(wrapCard(card), panelParams())
        }
        if (profile != null && (profile.effects.isNotEmpty() || profile.isComplete)) {
            val card = card()
            if (profile.ageBand.isNotBlank()) card.addView(meta(profile.ageBand))
            for (effect in profile.effects) {
                card.addView(advice("• $effect"))
            }
            chapters[10].addView(wrapCard(card), panelParams())
        }
        finishChapter(10)
    }

    private fun fillFilming(report: StageReport) {
        val lines = ArrayList<String>()
        lines.add(report.disclaimer)
        if (report.heuristicNotFisCarve) {
            lines.add(I18n.t("Carve points are heuristics, not FIS carving scores."))
        }
        for (issue in report.filming) {
            val prefix = when (issue.severity) {
                "blocker" -> "⚠ "
                "warn" -> "! "
                else -> "• "
            }
            lines.add(prefix + issue.message.ifBlank { issue.code })
        }
        for (step in report.filmSteps) {
            lines.add("• $step")
        }
        if (lines.all { it.isBlank() }) {
            finishChapter(11)
            return
        }
        val card = card()
        addLines(card, lines, paper = false)
        chapters[11].addView(wrapCard(card), panelParams())
        finishChapter(11)
    }

    private fun Double.format1(): String = String.format("%.1f", this)

    private fun planCard(plan: LevelPlan): LinearLayout {
        val card = card()
        if (plan.levelName.isNotBlank()) {
            card.addView(iconRow(listOf(ReportTheme.medalColor(plan.levelId) to "trophy"), plan.levelName))
        }
        addLines(card, drillLines(plan.drills, plan.venues), paper = true)
        return card
    }

    private fun drillsCard(drills: List<DrillPayload>, title: String): LinearLayout {
        val card = card()
        val lines = ArrayList<String>()
        if (title.isNotBlank()) {
            lines.add(title)
        }
        lines.addAll(drillLines(drills, emptyList()))
        addLines(card, lines, paper = true)
        return card
    }

    private fun drillLines(drills: List<DrillPayload>, venues: List<VenuePayload>): List<String> {
        val lines = ArrayList<String>()
        for (drill in drills) {
            lines.add("${I18n.t("Drills")}: ${drill.title.ifBlank { drill.name }}")
            if (drill.desc.isNotBlank()) {
                lines.add(drill.desc)
            }
            val steps = if (drill.training.isNotEmpty()) drill.training else drill.steps
            for (step in steps) {
                lines.add("• $step")
            }
            for (venue in drill.venues) {
                lines.add("${I18n.t("Training venue")}: ${venue.name}")
                if (venue.tips.isNotBlank()) {
                    lines.add(venue.tips)
                }
            }
        }
        for (venue in venues) {
            lines.add("${I18n.t("Training venue")}: ${venue.name}")
            if (venue.desc.isNotBlank()) {
                lines.add(venue.desc)
            }
            if (venue.tips.isNotBlank()) {
                lines.add(venue.tips)
            }
        }
        return lines
    }

    private fun addRingRow(
        parent: LinearLayout,
        items: List<Triple<Double?, String, Int>>,
        perRow: Int = 2,
    ) {
        var row: LinearLayout? = null
        items.forEachIndexed { i, item ->
            if (i % perRow == 0) {
                row = equalHeightRow()
                parent.addView(row, panelParams())
            }
            val card = card()
            val ring = ScoreRingView(context)
            ring.setScore(item.first, item.second, item.third)
            card.addView(ring, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            row?.addView(wrapCard(card), rowCellParams(i, perRow))
        }
    }

    private fun addLines(parent: LinearLayout, lines: List<String>, paper: Boolean) {
        for (line in lines) {
            if (line.isBlank()) {
                continue
            }
            parent.addView(if (paper) advice(line) else meta(line))
        }
    }

    private fun applyVerticalGaps(parent: LinearLayout, gapPx: Int) {
        val n = parent.childCount
        for (i in 0 until n) {
            val child = parent.getChildAt(i)
            val lp = child.layoutParams as LayoutParams
            lp.bottomMargin = if (i == n - 1) 0 else gapPx
            child.layoutParams = lp
        }
    }

    private fun card(): LinearLayout {
        return LinearLayout(context).apply {
            orientation = VERTICAL
            val pad = dp(ReportTheme.PAGE_INSET)
            setPadding(pad, pad, pad, pad)
        }
    }

    private fun wrapCard(inner: View): LinearLayout {
        if (inner is LinearLayout) {
            applyVerticalGaps(inner, dp(ReportTheme.SPACE_TEXT))
        }
        val shell = LinearLayout(context)
        shell.orientation = VERTICAL
        shell.gravity = Gravity.TOP
        shell.background = GradientDrawable().apply {
            setColor(ReportTheme.CARD)
            cornerRadius = dp(10).toFloat()
        }
        shell.addView(inner, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        val spacer = View(context)
        spacer.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        shell.addView(spacer, LayoutParams(LayoutParams.MATCH_PARENT, 0, 1f))
        return shell
    }

    private fun equalHeightRow(): LinearLayout {
        return LinearLayout(context).apply {
            orientation = HORIZONTAL
            isBaselineAligned = false
            gravity = Gravity.TOP
        }
    }

    private fun rowCellParams(index: Int, perRow: Int): LayoutParams {
        return LayoutParams(0, LayoutParams.MATCH_PARENT, 1f).apply {
            marginEnd = if ((index + 1) % perRow == 0) 0 else dp(ReportTheme.SPACE_PANEL)
        }
    }

    private fun iconRow(icons: List<Pair<Int, String>>, text: String): LinearLayout {
        val row = LinearLayout(context)
        row.orientation = HORIZONTAL
        row.gravity = Gravity.CENTER_VERTICAL
        for ((color, kind) in icons) {
            val icon = TrophyView(context, kind == "diamond", color)
            row.addView(icon, LayoutParams(dp(22), dp(22)).apply { marginEnd = dp(8) })
        }
        val label = TextView(context)
        label.text = text
        label.setTextColor(ReportTheme.PAPER)
        label.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
        row.addView(label, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        return row
    }

    private fun meta(text: String): TextView {
        return TextView(context).apply {
            this.text = text
            setTextColor(ReportTheme.TITLE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
        }
    }

    private fun advice(text: String): TextView {
        return TextView(context).apply {
            this.text = text
            setTextColor(ReportTheme.PAPER)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setLineSpacing(0f, 1.2f)
        }
    }

    private fun seekLink(label: String, tMs: Int): TextView {
        return TextView(context).apply {
            text = label
            setTextColor(ReportTheme.LINK)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setOnClickListener { onSeek?.invoke(tMs) }
        }
    }

    private fun panelParams(): LayoutParams {
        return LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

class TrophyView(
    context: Context,
    private val diamond: Boolean,
    private val tint: Int,
) : View(context) {
    private val fillPaint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        color = tint
        style = android.graphics.Paint.Style.FILL
    }
    private val strokePaint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.STROKE
        strokeJoin = android.graphics.Paint.Join.MITER
    }
    private val path = android.graphics.Path()

    override fun onDraw(canvas: android.graphics.Canvas) {
        super.onDraw(canvas)
        path.reset()
        val w = width.toFloat()
        val h = height.toFloat()
        val outline = diamond && tint == ReportTheme.TERRAIN_BLACK
        val stroke = if (outline) 1f * resources.displayMetrics.density else 0f
        val pad = stroke / 2f + 1f
        if (diamond) {
            path.moveTo(w / 2f, pad)
            path.lineTo(w - pad, h / 2f)
            path.lineTo(w / 2f, h - pad)
            path.lineTo(pad, h / 2f)
            path.close()
        } else {
            path.moveTo(w * 0.25f, h * 0.15f)
            path.lineTo(w * 0.75f, h * 0.15f)
            path.lineTo(w * 0.68f, h * 0.45f)
            path.lineTo(w * 0.55f, h * 0.45f)
            path.lineTo(w * 0.55f, h * 0.72f)
            path.lineTo(w * 0.72f, h * 0.85f)
            path.lineTo(w * 0.28f, h * 0.85f)
            path.lineTo(w * 0.45f, h * 0.72f)
            path.lineTo(w * 0.45f, h * 0.45f)
            path.lineTo(w * 0.32f, h * 0.45f)
            path.close()
        }
        canvas.drawPath(path, fillPaint)
        if (outline) {
            strokePaint.color = 0xFFFFFFFF.toInt()
            strokePaint.strokeWidth = stroke
            canvas.drawPath(path, strokePaint)
        }
    }
}
