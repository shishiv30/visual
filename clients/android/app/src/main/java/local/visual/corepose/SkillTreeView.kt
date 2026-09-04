package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Typeface
import android.util.AttributeSet
import android.view.View
import kotlin.math.max
import kotlin.math.roundToInt

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
        // Prefer piste branch + current branch peers; keep layout readable on phone.
        val currentBranch = next.firstOrNull { it.state == NodeState.CURRENT }?.branch ?: "piste"
        val focused = next.filter {
            it.branch == currentBranch ||
                it.state == NodeState.CURRENT ||
                it.state == NodeState.COMPLETED ||
                it.state == NodeState.INFERRED ||
                it.state == NodeState.AVAILABLE
        }.ifEmpty { next }
        treeNodes.addAll(focused.sortedWith(compareBy({ it.depth }, { it.name })))
        requestLayout()
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val density = resources.displayMetrics.density
        val width = MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(suggestedMinimumWidth)
        val count = if (treeNodes.isNotEmpty()) treeNodes.size else pathNodes.size
        val height = SkillTreeLayout.heightPx(count, density)
        setMeasuredDimension(width, height)
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
        val n = treeNodes.size
        if (n == 0) return
        val cx = SkillTreeLayout.LINE_X_DP * density
        val row = SkillTreeLayout.ROW_DP * density
        val r = SkillTreeLayout.DOT_RADIUS_DP * density
        if (n > 1) {
            canvas.drawLine(cx, row / 2f, cx, (n - 1) * row + row / 2f, linePaint)
        }
        treeNodes.forEachIndexed { i, node ->
            val color = SkillTreeLayout.color(node.state)
            val cy = i * row + row / 2f
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
