package local.visual.corepose

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.max
import kotlin.math.min

class SeedCanvasView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF00FF00.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2f * resources.displayMetrics.density
    }
    private val bitmapPaint = Paint(Paint.FILTER_BITMAP_FLAG)

    private var frame: Bitmap? = null
    private var originX = 0f
    private var originY = 0f
    private var dragging = false
    private var rect = RectF()
    var boxCommitted: (() -> Unit)? = null

    fun setFrame(bitmap: Bitmap?) {
        val relayout = frame?.width != bitmap?.width || frame?.height != bitmap?.height
        frame = bitmap
        if (relayout) {
            requestLayout()
        }
        invalidate()
    }

    fun setBoxNorm(box: NormBox?) {
        val bmp = frame
        if (box == null || bmp == null || width < 2 || height < 2) {
            rect.setEmpty()
            invalidate()
            return
        }
        val (l, t) = OverlayMath.mapContain(
            box.x1 * bmp.width,
            box.y1 * bmp.height,
            bmp.width,
            bmp.height,
            width,
            height,
        )
        val (r, b) = OverlayMath.mapContain(
            box.x2 * bmp.width,
            box.y2 * bmp.height,
            bmp.width,
            bmp.height,
            width,
            height,
        )
        rect.set(l, t, r, b)
        invalidate()
    }

    fun boxNorm(): NormBox? {
        val bmp = frame ?: return null
        if (width < 2 || height < 2) {
            return null
        }
        val n = sorted(rect)
        if (n.width() < 8f || n.height() < 8f) {
            return null
        }
        val (x1, y1) = OverlayMath.unmapContain(n.left, n.top, bmp.width, bmp.height, width, height)
        val (x2, y2) = OverlayMath.unmapContain(n.right, n.bottom, bmp.width, bmp.height, width, height)
        val nx1 = min(x1, x2) / bmp.width
        val ny1 = min(y1, y2) / bmp.height
        val nx2 = max(x1, x2) / bmp.width
        val ny2 = max(y1, y2) / bmp.height
        if (nx2 - nx1 < 0.02f || ny2 - ny1 < 0.02f) {
            return null
        }
        return NormBox(
            nx1.coerceIn(0f, 1f),
            ny1.coerceIn(0f, 1f),
            nx2.coerceIn(0f, 1f),
            ny2.coerceIn(0f, 1f),
        )
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                originX = event.x
                originY = event.y
                dragging = true
                parent.requestDisallowInterceptTouchEvent(true)
                rect.set(originX, originY, originX, originY)
                invalidate()
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (!dragging) {
                    return false
                }
                rect.set(originX, originY, event.x, event.y)
                invalidate()
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                dragging = false
                parent.requestDisallowInterceptTouchEvent(false)
                return true
            }
            MotionEvent.ACTION_UP -> {
                if (!dragging) {
                    return false
                }
                dragging = false
                parent.requestDisallowInterceptTouchEvent(false)
                rect.set(originX, originY, event.x, event.y)
                invalidate()
                if (boxNorm() != null) {
                    boxCommitted?.invoke()
                }
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val bmp = frame
        if (bmp != null && width > 0 && height > 0) {
            val box = OverlayMath.contain(bmp.width, bmp.height, width, height)
            val dest = RectF(
                box.dx,
                box.dy,
                box.dx + bmp.width * box.scale,
                box.dy + bmp.height * box.scale,
            )
            canvas.drawBitmap(bmp, null, dest, bitmapPaint)
        }
        val n = sorted(rect)
        if (n.width() >= 2f && n.height() >= 2f) {
            canvas.drawRect(n, boxPaint)
        }
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        val maxH = (360f * resources.displayMetrics.density).toInt()
        val bmp = frame
        val aspect = if (bmp != null && bmp.width > 0) {
            bmp.height.toFloat() / bmp.width
        } else {
            9f / 16f
        }
        val minH = (160f * resources.displayMetrics.density).toInt()
        val height = (width * aspect).toInt().coerceIn(minH, maxH)
        setMeasuredDimension(width.coerceAtLeast(1), height)
    }

    private fun sorted(src: RectF): RectF {
        return RectF(
            min(src.left, src.right),
            min(src.top, src.bottom),
            max(src.left, src.right),
            max(src.top, src.bottom),
        )
    }
}
