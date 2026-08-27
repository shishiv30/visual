package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

class ScoreRingView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val track = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        color = ReportTheme.RING_TRACK
    }
    private val arc = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        color = ReportTheme.TITLE
    }
    private val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ReportTheme.PAPER
        textAlign = Paint.Align.CENTER
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ReportTheme.TITLE
        textAlign = Paint.Align.CENTER
    }
    private val oval = RectF()

    private var score: Double? = 0.0
    private var caption = ""

    fun setScore(next: Double?, label: String, ringColor: Int) {
        score = next
        caption = label
        arc.color = ringColor
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(dp(120))
        setMeasuredDimension(width, dp(148))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val density = resources.displayMetrics.density
        val stroke = 10f * density
        track.strokeWidth = stroke
        arc.strokeWidth = stroke
        valuePaint.textSize = 22f * density
        labelPaint.textSize = 12f * density
        val pad = stroke + 8f * density
        val ringSize = minOf(width.toFloat() - pad * 2f, height.toFloat() - 36f * density)
        val cx = width / 2f
        val top = 8f * density
        oval.set(cx - ringSize / 2f, top, cx + ringSize / 2f, top + ringSize)
        val value = score ?: 0.0
        val frac = (value / 100.0).coerceIn(0.0, 1.0).toFloat()
        val zeroRing = score == null || frac <= 0f
        track.color = if (zeroRing) ReportTheme.TITLE else ReportTheme.RING_TRACK
        canvas.drawArc(oval, 0f, 360f, false, track)
        if (!zeroRing) {
            canvas.drawArc(oval, -90f, 360f * frac, false, arc)
        }
        val text = if (score == null) "—" else score!!.toInt().toString()
        canvas.drawText(text, cx, oval.centerY() + valuePaint.textSize / 3f, valuePaint)
        val lines = wrap(caption, width - dp(16))
        var y = oval.bottom + 16f * density
        for (line in lines.take(2)) {
            canvas.drawText(line, cx, y, labelPaint)
            y += labelPaint.textSize + 2f * density
        }
    }

    private fun wrap(text: String, maxWidth: Int): List<String> {
        if (text.isEmpty()) {
            return emptyList()
        }
        val words = text.split(" ")
        val lines = ArrayList<String>()
        var cur = StringBuilder()
        for (word in words) {
            val next = if (cur.isEmpty()) word else "$cur $word"
            if (labelPaint.measureText(next) > maxWidth && cur.isNotEmpty()) {
                lines.add(cur.toString())
                cur = StringBuilder(word)
            } else {
                cur = StringBuilder(next)
            }
        }
        if (cur.isNotEmpty()) {
            lines.add(cur.toString())
        }
        return lines
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
