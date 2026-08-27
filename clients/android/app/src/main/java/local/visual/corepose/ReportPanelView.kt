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

    private val empty = TextView(context)
    private val chapters = Array(5) { LinearLayout(context) }
    private val titles = Array(5) { TextView(context) }
    private val blocks = Array(5) { LinearLayout(context) }
    private var report: StageReport? = null

    init {
        orientation = VERTICAL
        val pad = dp(ReportTheme.REPORT_INSET)
        setPadding(pad, pad, pad, pad)
        empty.setTextColor(ReportTheme.TITLE)
        empty.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
        addView(empty, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        for (i in 0 until 5) {
            titles[i].setTextColor(ReportTheme.TITLE)
            titles[i].setTextSize(TypedValue.COMPLEX_UNIT_SP, 32f)
            titles[i].setPadding(0, 0, 0, dp(ReportTheme.SPACE_TEXT))
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
        titles[0].text = I18n.t("Summary")
        titles[1].text = I18n.t("Checkpoints")
        titles[2].text = I18n.t("Next steps")
        titles[3].text = I18n.t("Skill tree")
        titles[4].text = I18n.t("Filming and scoring")
        bind(report)
    }

    private fun finishChapter(index: Int) {
        applyVerticalGaps(chapters[index], dp(ReportTheme.SPACE_PANEL))
    }

    fun bind(next: StageReport?) {
        report = next
        val has = next != null
        empty.visibility = if (has) GONE else VISIBLE
        for (i in 0 until 5) {
            blocks[i].visibility = if (has) VISIBLE else GONE
            chapters[i].removeAllViews()
        }
        if (next == null) {
            return
        }
        fillCh1(next)
        fillCh2(next)
        fillCh3(next)
        fillCh4(next)
        fillCh5(next)
    }

    private fun fillCh1(report: StageReport) {
        val overview = card()
        overview.addView(iconRow(listOf(ReportTheme.medalColor(report.stageId) to "trophy"), report.stageName))
        if (report.stageFocus.isNotBlank()) {
            overview.addView(meta(report.stageFocus))
        }
        chapters[0].addView(wrapCard(overview), panelParams())

        val terrain = card()
        val gate = if (report.readyForNextStage) {
            I18n.t("Passed this level. Choose a next level on the skill tree.")
        } else {
            I18n.t("Not passed — train the lowest-scoring checkpoint.")
        }
        val trail = report.terrainName.ifBlank { I18n.t("—") }
        val line = "${I18n.t("Suggested trail rating")}: $trail · $gate"
        val diamonds = ReportTheme.terrainDiamondColors(report.terrainId).map { it to "diamond" }
        terrain.addView(iconRow(diamonds, line))
        if (report.terrainDesc.isNotBlank()) {
            terrain.addView(meta(report.terrainDesc))
        }
        chapters[0].addView(wrapCard(terrain), panelParams())

        addRingRow(
            chapters[0],
            listOf(
                Triple(report.score0100, I18n.t("Heuristic score (0-100, not FIS)"), ReportTheme.scorePurple(report.score0100)),
                Triple(report.confidence * 100.0, I18n.t("Confidence"), ReportTheme.scorePurple(report.confidence * 100.0)),
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

        val kps = ReportTheme.sortedKeypoints(report.keypoints)
        val perRow = if (kps.size >= 5) 3 else 2
        addRingRow(
            chapters[0],
            kps.map { item ->
                Triple(item.score, item.name.ifBlank { item.id }, ReportTheme.scorePurple(item.score))
            },
            perRow,
        )

        val timelineCard = card()
        timelineCard.addView(meta(I18n.t("Stability over time (time × frame score)")))
        val chart = ScoreTimelineView(context)
        chart.setPoints(report.scoreSeries)
        chart.onSeek = { ms -> onSeek?.invoke(ms) }
        timelineCard.addView(chart, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        chapters[0].addView(wrapCard(timelineCard), panelParams())
        finishChapter(0)
    }

    private fun fillCh2(report: StageReport) {
        val kps = ReportTheme.sortedKeypoints(report.keypoints)
        val perRow = if (kps.size >= 5) 3 else 2
        var row: LinearLayout? = null
        kps.forEachIndexed { i, item ->
            if (i % perRow == 0) {
                row = equalHeightRow()
                chapters[1].addView(row, panelParams())
            }
            val card = card()
            val ring = ScoreRingView(context)
            ring.setScore(item.score, item.name.ifBlank { item.id }, ReportTheme.scorePurple(item.score))
            card.addView(ring, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            val detail = if (item.status == KeypointStatus.PASS) item.good else item.bad
            card.addView(advice(detail))
            if (item.evidenceMs != null) {
                card.addView(seekLink(ReportTheme.formatEvidenceMs(item.evidenceMs), item.evidenceMs.toInt()))
            }
            val cell = wrapCard(card)
            row?.addView(cell, rowCellParams(i, perRow))
        }
        finishChapter(1)
    }

    private fun fillCh3(report: StageReport) {
        if (report.readyForNextStage) {
            val ready = card()
            ready.addView(advice(I18n.t("Passed this level. Choose a next level on the skill tree.")))
            chapters[2].addView(wrapCard(ready), panelParams())
            for (plan in report.nextPlans) {
                chapters[2].addView(wrapCard(planCard(plan)), panelParams())
            }
            finishChapter(2)
            return
        }
        val summary = card()
        val lines = ArrayList<String>()
        lines.add(I18n.t("Not passed — train the lowest-scoring checkpoint."))
        val weak = report.keypoints.firstOrNull { it.id == report.weakestCheckpointId }
        if (weak != null) {
            lines.add("${I18n.t("Weakest checkpoint")}: ${weak.name}")
            lines.add(weak.bad)
        }
        addLines(summary, lines, paper = true)
        chapters[2].addView(wrapCard(summary), panelParams())
        if (weak?.evidenceMs != null) {
            val linkCard = card()
            linkCard.addView(
                seekLink(
                    "${I18n.t("Problem frame")} ${ReportTheme.formatEvidenceMs(weak.evidenceMs)}",
                    weak.evidenceMs.toInt(),
                ),
            )
            chapters[2].addView(wrapCard(linkCard), panelParams())
        }
        if (weak != null) {
            chapters[2].addView(wrapCard(drillsCard(weak.drills, weak.name)), panelParams())
        }
        val failItems = ReportTheme.sortedKeypoints(report.keypoints).filter {
            it.status == KeypointStatus.FAIL && (weak == null || it.id != weak.id)
        }
        for (item in failItems) {
            chapters[2].addView(wrapCard(drillsCard(item.drills, item.name)), panelParams())
        }
        finishChapter(2)
    }

    private fun fillCh4(report: StageReport) {
        val card = card()
        val tree = SkillTreeView(context)
        tree.setRoute(report.treePath)
        card.addView(tree, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        if (report.readyForNextStage && report.nextLevelNames.isNotEmpty()) {
            card.addView(meta("${I18n.t("Next stage")}: ${report.nextLevelNames.joinToString(" · ")}"))
        }
        chapters[3].addView(wrapCard(card), panelParams())
        finishChapter(3)
    }

    private fun fillCh5(report: StageReport) {
        val lines = ArrayList<String>()
        lines.add(report.disclaimer)
        if (report.heuristicNotFisCarve) {
            lines.add(I18n.t("Carve points are heuristics, not FIS carving scores."))
        }
        for (step in report.filmSteps) {
            lines.add("• $step")
        }
        val card = card()
        addLines(card, lines, paper = false)
        chapters[4].addView(wrapCard(card), panelParams())
        finishChapter(4)
    }

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
