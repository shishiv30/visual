package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View

/** Lightweight horizontal turn strip (Windows TurnStripChart analogue). */
class TurnStripView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    var onSeek: ((Int) -> Unit)? = null

    private val fillLeft = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFF5E35B1.toInt() }
    private val fillRight = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFFCE93D8.toInt() }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF757575.toInt()
        style = Paint.Style.STROKE
        strokeWidth = resources.displayMetrics.density
    }
    private var turns: List<TurnRecord> = emptyList()
    private val rect = RectF()

    fun setTurns(next: List<TurnRecord>) {
        turns = next
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        setMeasuredDimension(width.coerceAtLeast(1), dp(36))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (turns.isEmpty()) {
            return
        }
        val pad = dp(4).toFloat()
        val gap = dp(2).toFloat()
        val n = turns.size
        val avail = (width - pad * 2 - gap * (n - 1).coerceAtLeast(0)).coerceAtLeast(1f)
        val cell = avail / n
        val top = pad
        val bottom = height - pad
        turns.forEachIndexed { i, turn ->
            val left = pad + i * (cell + gap)
            rect.set(left, top, left + cell, bottom)
            val paint = if (turn.side.equals("L", ignoreCase = true) || turn.side.equals("left", ignoreCase = true)) {
                if (turn.flags.isNotEmpty()) {
                    fillLeft.apply { color = 0xFFC62828.toInt() }
                } else {
                    fillLeft.apply { color = 0xFF5E35B1.toInt() }
                }
            } else {
                if (turn.flags.isNotEmpty()) {
                    fillRight.apply { color = 0xFFE57373.toInt() }
                } else {
                    fillRight.apply { color = 0xFFCE93D8.toInt() }
                }
            }
            canvas.drawRoundRect(rect, dp(4).toFloat(), dp(4).toFloat(), paint)
            canvas.drawRoundRect(rect, dp(4).toFloat(), dp(4).toFloat(), border)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_UP && turns.isNotEmpty()) {
            val pad = dp(4).toFloat()
            val gap = dp(2).toFloat()
            val n = turns.size
            val avail = (width - pad * 2 - gap * (n - 1).coerceAtLeast(0)).coerceAtLeast(1f)
            val cell = avail / n
            val idx = ((event.x - pad) / (cell + gap)).toInt().coerceIn(0, n - 1)
            onSeek?.invoke(turns[idx].tStartMs.toInt())
            return true
        }
        return event.actionMasked == MotionEvent.ACTION_DOWN || super.onTouchEvent(event)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
