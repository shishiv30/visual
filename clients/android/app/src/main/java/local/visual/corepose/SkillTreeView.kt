package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Typeface
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.max
import kotlin.math.roundToInt

/** Branch order below the piste spine, app-spec.md §5 / design doc §8. */
private val BRANCH_ORDER = listOf("moguls", "offpiste", "park", "race")

/** branch id -> English display key (already in locales/strings.json). */
private val BRANCH_LABELS = mapOf(
    "piste" to "Piste",
    "moguls" to "Moguls",
    "offpiste" to "Off-piste",
    "park" to "Park",
    "race" to "Race",
)

/**
 * One rendered row of the skill tree: either a node, or a disclosure row
 * standing in for a collapsed run of a side branch's rows.
 */
private sealed class TreeRow {
    /** Indent is derivable (0 for piste, 1 for every side branch) — not stored. */
    data class Node(val node: TreeNodeV3) : TreeRow()
    data class BranchHeader(val branch: String, val count: Int) : TreeRow()
}

/**
 * Lay the whole progression out as rows: piste spine (indent 0, never
 * collapsed), then each side branch (indent 1) as one contiguous run.
 *
 * Android's tree has no order_tree_rows/indent concept of its own (unlike
 * the desktop client) — this is the Kotlin equivalent, built fresh for the
 * branch-collapsing readability follow-up. Like desktop, no branch ever
 * needs to nest inside another, so indent is always 0 or 1.
 */
private fun buildTreeRows(nodes: List<TreeNodeV3>): List<TreeRow> {
    val rows = ArrayList<TreeRow>()
    val byBranch = nodes.groupBy { it.branch }
    val piste = byBranch["piste"].orEmpty().sortedWith(compareBy({ it.depth }, { it.name }))
    for (node in piste) {
        rows.add(TreeRow.Node(node))
    }
    // Known branches keep their fixed reading order; any branch id outside
    // that order (future-proofing) still renders, grouped at the end (in
    // first-seen order) rather than silently dropped.
    val known = BRANCH_ORDER.toSet() + "piste"
    val extraBranches = nodes.map { it.branch }.filter { it !in known }.distinct()
    val sideBranches = BRANCH_ORDER + extraBranches
    for (branch in sideBranches) {
        val group = byBranch[branch].orEmpty().sortedWith(compareBy({ it.depth }, { it.name }))
        if (group.isEmpty()) continue
        rows.add(TreeRow.BranchHeader(branch, group.size))
        for (node in group) {
            rows.add(TreeRow.Node(node))
        }
    }
    return rows
}

object SkillTreeLayout {
    const val ROW_DP = 36
    const val DOT_RADIUS_DP = 5f
    const val LINE_X_DP = 8f
    const val TEXT_GAP_DP = 12f
    const val DASH_DP = 3f
    const val GAP_DP = 3f
    const val CURRENT = 0xFFE1BEE7.toInt()
    const val COMPLETED = 0xFFCE93D8.toInt()
    const val INFERRED = 0xFFB39DDB.toInt()
    const val AVAILABLE = 0xFF9E9E9E.toInt()
    const val LOCKED = 0xFF757575.toInt()
    const val NA = 0xFF616161.toInt()
    const val LINE = 0xFFF5F5F5.toInt()
    /** Legacy path-route pending color (tests + setRoute). */
    const val PENDING = LOCKED

    enum class Kind { CURRENT, COMPLETED, PENDING }

    fun currentIndex(nodes: List<TreeNode>): Int {
        val i = nodes.indexOfFirst { it.current }
        return if (i >= 0) i else max(0, nodes.lastIndex)
    }

    fun kind(index: Int, currentIndex: Int): Kind {
        return when {
            index == currentIndex -> Kind.CURRENT
            index < currentIndex -> Kind.COMPLETED
            else -> Kind.PENDING
        }
    }

    fun color(kind: Kind): Int {
        return when (kind) {
            Kind.CURRENT -> CURRENT
            Kind.COMPLETED -> COMPLETED
            Kind.PENDING -> PENDING
        }
    }

    fun color(state: NodeState): Int {
        return when (state) {
            NodeState.CURRENT -> CURRENT
            NodeState.COMPLETED -> COMPLETED
            NodeState.INFERRED -> INFERRED
            NodeState.AVAILABLE -> AVAILABLE
            NodeState.NOT_APPLICABLE -> NA
            NodeState.LOCKED -> LOCKED
        }
    }

    fun heightPx(count: Int, density: Float): Int {
        val n = max(1, count)
        return (n * ROW_DP * density).roundToInt()
    }

    fun textX(density: Float): Float {
        return (LINE_X_DP + DOT_RADIUS_DP + TEXT_GAP_DP) * density
    }
}

class SkillTreeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val pathNodes = ArrayList<TreeNode>()
    private val treeNodes = ArrayList<TreeNodeV3>()
    private var rows: List<TreeRow> = emptyList()
    private var visibleRows: List<TreeRow> = emptyList()

    // Branch id -> expanded. Only the branch holding the `current` node
    // starts expanded; every other side branch starts collapsed. The piste
    // spine is indent 0 and never appears here — it's never collapsible.
    private val expandedBranches = HashMap<String, Boolean>()
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = SkillTreeLayout.LINE
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.BUTT
    }
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val subPaint = Paint(Paint.ANTI_ALIAS_FLAG)

    fun setRoute(next: List<TreeNode>) {
        pathNodes.clear()
        treeNodes.clear()
        pathNodes.addAll(next)
        requestLayout()
        invalidate()
    }

    fun setTree(next: List<TreeNodeV3>) {
        pathNodes.clear()
        treeNodes.clear()
        treeNodes.addAll(next)
        rows = buildTreeRows(next)
        // Default: only the branch containing the `current`-state node
        // starts expanded (app-spec.md §5 / design doc §8, readability
        // follow-up); the piste spine itself is never collapsed.
        val currentBranch = next.firstOrNull { it.state == NodeState.CURRENT }?.branch ?: "piste"
        expandedBranches.clear()
        for (row in rows) {
            if (row is TreeRow.BranchHeader) {
                expandedBranches[row.branch] = row.branch == currentBranch
            }
        }
        recomputeVisibleRows()
        isClickable = true
        isFocusable = true
        requestLayout()
        invalidate()
    }

    private fun recomputeVisibleRows() {
        visibleRows = rows.filter { row ->
            when (row) {
                is TreeRow.BranchHeader -> true
                is TreeRow.Node -> row.node.branch == "piste" || expandedBranches[row.node.branch] == true
            }
        }
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val density = resources.displayMetrics.density
        val width = MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(suggestedMinimumWidth)
        val count = if (treeNodes.isNotEmpty()) visibleRows.size else pathNodes.size
        val height = SkillTreeLayout.heightPx(count, density)
        setMeasuredDimension(width, height)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (treeNodes.isEmpty()) {
            return super.onTouchEvent(event)
        }
        if (event.action == MotionEvent.ACTION_UP) {
            val density = resources.displayMetrics.density
            val row = SkillTreeLayout.ROW_DP * density
            val index = (event.y / row).toInt()
            val tapped = visibleRows.getOrNull(index)
            if (tapped is TreeRow.BranchHeader) {
                expandedBranches[tapped.branch] = expandedBranches[tapped.branch] != true
                recomputeVisibleRows()
                requestLayout()
                invalidate()
                performClick()
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val density = resources.displayMetrics.density
        textPaint.textSize = 15f * density
        subPaint.textSize = 11f * density
        linePaint.strokeWidth = density.coerceAtLeast(1f)
        linePaint.pathEffect = DashPathEffect(
            floatArrayOf(
                SkillTreeLayout.DASH_DP * density,
                SkillTreeLayout.GAP_DP * density,
            ),
            0f,
        )
        strokePaint.strokeWidth = density.coerceAtLeast(1f)
        if (treeNodes.isNotEmpty()) {
            drawV3(canvas, density)
        } else {
            drawPath(canvas, density)
        }
    }

    private fun drawV3(canvas: Canvas, density: Float) {
        val n = visibleRows.size
        if (n == 0) return
        val cx = SkillTreeLayout.LINE_X_DP * density
        val row = SkillTreeLayout.ROW_DP * density
        if (n > 1) {
            canvas.drawLine(cx, row / 2f, cx, (n - 1) * row + row / 2f, linePaint)
        }
        visibleRows.forEachIndexed { i, item ->
            val cy = i * row + row / 2f
            when (item) {
                is TreeRow.Node -> drawTreeNode(canvas, item.node, cx, cy, density)
                is TreeRow.BranchHeader -> drawBranchHeader(canvas, item, cx, cy, density)
            }
        }
    }

    private fun drawTreeNode(canvas: Canvas, node: TreeNodeV3, cx: Float, cy: Float, density: Float) {
        val r = SkillTreeLayout.DOT_RADIUS_DP * density
        val color = SkillTreeLayout.color(node.state)
        when (node.state) {
            NodeState.LOCKED, NodeState.NOT_APPLICABLE, NodeState.AVAILABLE -> {
                strokePaint.color = color
                canvas.drawCircle(cx, cy, r, strokePaint)
            }
            else -> {
                fillPaint.color = color
                canvas.drawCircle(cx, cy, r, fillPaint)
            }
        }
        textPaint.color = color
        textPaint.typeface = if (node.state == NodeState.CURRENT || node.state == NodeState.COMPLETED) {
            Typeface.DEFAULT_BOLD
        } else {
            Typeface.DEFAULT
        }
        val label = buildString {
            append(node.name)
            if (node.gatesPassed.isNotBlank()) append("  ${node.gatesPassed}")
        }
        val textY = cy - (textPaint.descent() + textPaint.ascent()) / 2f - 4f * density
        canvas.drawText(label, SkillTreeLayout.textX(density), textY, textPaint)
        val detail = when {
            node.lockedReason.isNotBlank() -> node.lockedReason
            node.inferredReason.isNotBlank() -> node.inferredReason
            node.state == NodeState.CURRENT -> I18n.t("Current")
            node.state == NodeState.COMPLETED -> I18n.t("Completed")
            node.state == NodeState.AVAILABLE -> I18n.t("Available")
            else -> node.branch
        }
        if (detail.isNotBlank()) {
            subPaint.color = color
            canvas.drawText(
                detail,
                SkillTreeLayout.textX(density),
                textY + 14f * density,
                subPaint,
            )
        }
    }

    /** "{Branch} · N stages" disclosure row standing in for a collapsed branch. */
    private fun drawBranchHeader(canvas: Canvas, header: TreeRow.BranchHeader, cx: Float, cy: Float, density: Float) {
        val r = SkillTreeLayout.DOT_RADIUS_DP * density
        val color = SkillTreeLayout.AVAILABLE
        strokePaint.color = color
        canvas.drawCircle(cx, cy, r, strokePaint)
        textPaint.color = color
        textPaint.typeface = Typeface.DEFAULT_BOLD
        val expanded = expandedBranches[header.branch] == true
        val chevron = if (expanded) "▾" else "▸"
        val branchLabel = I18n.t(BRANCH_LABELS[header.branch] ?: header.branch)
        val countLabel = I18n.t("{n} stages", mapOf("n" to header.count.toString()))
        val label = "$chevron $branchLabel · $countLabel"
        val textY = cy - (textPaint.descent() + textPaint.ascent()) / 2f - 4f * density
        canvas.drawText(label, SkillTreeLayout.textX(density), textY, textPaint)
    }

    private fun drawPath(canvas: Canvas, density: Float) {
        val n = pathNodes.size
        if (n == 0) {
            textPaint.color = SkillTreeLayout.LOCKED
            textPaint.typeface = Typeface.DEFAULT
            val y = SkillTreeLayout.ROW_DP * density / 2f - (textPaint.descent() + textPaint.ascent()) / 2f
            canvas.drawText(I18n.t("—"), SkillTreeLayout.textX(density), y, textPaint)
            return
        }
        val currentI = pathNodes.indexOfFirst { it.current }.let { if (it >= 0) it else max(0, pathNodes.lastIndex) }
        val cx = SkillTreeLayout.LINE_X_DP * density
        val row = SkillTreeLayout.ROW_DP * density
        val r = SkillTreeLayout.DOT_RADIUS_DP * density
        if (n > 1) {
            canvas.drawLine(cx, row / 2f, cx, (n - 1) * row + row / 2f, linePaint)
        }
        pathNodes.forEachIndexed { i, node ->
            val state = when {
                i == currentI -> NodeState.CURRENT
                i < currentI -> NodeState.COMPLETED
                else -> NodeState.AVAILABLE
            }
            val color = SkillTreeLayout.color(state)
            val cy = i * row + row / 2f
            if (state == NodeState.AVAILABLE) {
                strokePaint.color = color
                canvas.drawCircle(cx, cy, r, strokePaint)
            } else {
                fillPaint.color = color
                canvas.drawCircle(cx, cy, r, fillPaint)
            }
            textPaint.color = color
            textPaint.typeface = if (state == NodeState.AVAILABLE) Typeface.DEFAULT else Typeface.DEFAULT_BOLD
            val textY = cy - (textPaint.descent() + textPaint.ascent()) / 2f
            canvas.drawText(node.name, SkillTreeLayout.textX(density), textY, textPaint)
        }
    }
}
