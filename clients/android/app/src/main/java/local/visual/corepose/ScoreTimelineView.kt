package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View

class ScoreTimelineView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    var onSeek: ((Int) -> Unit)? = null

    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ReportTheme.LIGHT_PURPLE
        strokeWidth = 3f * resources.displayMetrics.density
        style = Paint.Style.STROKE
    }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x55CE93D8.toInt()
        style = Paint.Style.FILL
    }
    private val axis = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF6F6F6F.toInt()
        strokeWidth = 1f * resources.displayMetrics.density
    }
    private val path = Path()
    private val fillPath = Path()
    private var points: List<FrameScorePoint> = emptyList()

    fun setPoints(next: List<FrameScorePoint>) {
        points = next
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        setMeasuredDimension(width.coerceAtLeast(1), dp(140))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val pad = dp(8).toFloat()
        val w = width - pad * 2
        val h = height - pad * 2
        canvas.drawLine(pad, pad, pad, pad + h, axis)
        canvas.drawLine(pad, pad + h, pad + w, pad + h, axis)
        if (points.size < 2 || w <= 1f) {
            return
        }
        val t0 = points.first().tMs
        val t1 = points.last().tMs.coerceAtLeast(t0 + 1.0)
        path.reset()
        fillPath.reset()
        points.forEachIndexed { i, pt ->
            val x = pad + ((pt.tMs - t0) / (t1 - t0)).toFloat() * w
            val y = pad + h - (pt.score.coerceIn(0.0, 100.0) / 100.0).toFloat() * h
            if (i == 0) {
                path.moveTo(x, y)
                fillPath.moveTo(x, pad + h)
                fillPath.lineTo(x, y)
            } else {
                path.lineTo(x, y)
                fillPath.lineTo(x, y)
            }
        }
        val lastX = pad + w
        fillPath.lineTo(lastX, pad + h)
        fillPath.close()
        canvas.drawPath(fillPath, fill)
        canvas.drawPath(path, line)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN || event.actionMasked == MotionEvent.ACTION_UP) {
            parent.requestDisallowInterceptTouchEvent(true)
            val pad = dp(8).toFloat()
            val t0 = points.firstOrNull()?.tMs ?: return true
            val t1 = (points.lastOrNull()?.tMs ?: t0).coerceAtLeast(t0 + 1.0)
            val frac = ((event.x - pad) / (width - pad * 2).coerceAtLeast(1f)).coerceIn(0f, 1f)
            val tMs = t0 + frac * (t1 - t0)
            if (event.actionMasked == MotionEvent.ACTION_UP) {
                onSeek?.invoke(tMs.toInt())
            }
            return true
        }
        return super.onTouchEvent(event)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
