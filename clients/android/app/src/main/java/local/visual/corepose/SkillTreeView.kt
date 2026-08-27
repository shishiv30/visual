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
    const val ROW_DP = 32
    const val DOT_RADIUS_DP = 5f
    const val LINE_X_DP = 8f
    const val TEXT_GAP_DP = 12f
    const val DASH_DP = 3f
    const val GAP_DP = 3f
    const val CURRENT = 0xFFE1BEE7.toInt()
    const val COMPLETED = 0xFFCE93D8.toInt()
    const val PENDING = 0xFF757575.toInt()
    const val LINE = 0xFFF5F5F5.toInt()

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
    private val nodes = ArrayList<TreeNode>()
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

    fun setRoute(next: List<TreeNode>) {
        nodes.clear()
        nodes.addAll(next)
        requestLayout()
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val density = resources.displayMetrics.density
        val width = MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(suggestedMinimumWidth)
        val height = SkillTreeLayout.heightPx(nodes.size, density)
        setMeasuredDimension(width, height)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val density = resources.displayMetrics.density
        textPaint.textSize = 16f * density
        linePaint.strokeWidth = density.coerceAtLeast(1f)
        linePaint.pathEffect = DashPathEffect(
            floatArrayOf(
                SkillTreeLayout.DASH_DP * density,
                SkillTreeLayout.GAP_DP * density,
            ),
            0f,
        )
        strokePaint.strokeWidth = density.coerceAtLeast(1f)
        val n = nodes.size
        if (n == 0) {
            textPaint.color = SkillTreeLayout.PENDING
            textPaint.typeface = Typeface.DEFAULT
            val y = SkillTreeLayout.ROW_DP * density / 2f - (textPaint.descent() + textPaint.ascent()) / 2f
            canvas.drawText(I18n.t("—"), SkillTreeLayout.textX(density), y, textPaint)
            return
        }
        val currentI = SkillTreeLayout.currentIndex(nodes)
        val cx = SkillTreeLayout.LINE_X_DP * density
        val row = SkillTreeLayout.ROW_DP * density
        val r = SkillTreeLayout.DOT_RADIUS_DP * density
        if (n > 1) {
            val y0 = row / 2f
            val y1 = (n - 1) * row + row / 2f
            canvas.drawLine(cx, y0, cx, y1, linePaint)
        }
        nodes.forEachIndexed { i, node ->
            val kind = SkillTreeLayout.kind(i, currentI)
            val color = SkillTreeLayout.color(kind)
            val cy = i * row + row / 2f
            if (kind == SkillTreeLayout.Kind.PENDING) {
                strokePaint.color = color
                canvas.drawCircle(cx, cy, r, strokePaint)
            } else {
                fillPaint.color = color
                canvas.drawCircle(cx, cy, r, fillPaint)
            }
            textPaint.color = color
            textPaint.typeface = if (kind == SkillTreeLayout.Kind.PENDING) {
                Typeface.DEFAULT
            } else {
                Typeface.DEFAULT_BOLD
            }
            val textY = cy - (textPaint.descent() + textPaint.ascent()) / 2f
            canvas.drawText(node.name, SkillTreeLayout.textX(density), textY, textPaint)
        }
    }
}
