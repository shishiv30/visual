package local.visual.corepose

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import kotlin.math.hypot
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
    private val knobPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF00FF00.toInt()
        style = Paint.Style.FILL
    }

    /**
     * NEW_PENDING: finger down outside the box, not yet moved past touch slop - a plain tap must
     * not wipe the existing box. CORNER: resize from the grabbed corner. MOVE: drag the whole box.
     */
    private enum class Mode { NONE, NEW_PENDING, NEW, CORNER, MOVE }

    private val density = resources.displayMetrics.density
    private val slop = ViewConfiguration.get(context).scaledTouchSlop.toFloat()
    private val cornerHit = 32f * density
    private val knobR = 5f * density

    private var frame: Bitmap? = null
    private var originX = 0f
    private var originY = 0f
    private var mode = Mode.NONE
    private var rect = RectF()
    private val startRect = RectF()
    private var anchorX = 0f
    private var anchorY = 0f
    private var grabDx = 0f
    private var grabDy = 0f
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
                parent.requestDisallowInterceptTouchEvent(true)
                val n = sorted(rect)
                startRect.set(n)
                mode = Mode.NEW_PENDING
                if (n.width() >= 8f && n.height() >= 8f) {
                    val corner = nearestCorner(n, event.x, event.y)
                    if (corner != null) {
                        // Resize: the opposite corner stays put; keep the finger's offset to the
                        // corner so it does not jump under the fingertip.
                        mode = Mode.CORNER
                        anchorX = if (corner.first == n.left) n.right else n.left
                        anchorY = if (corner.second == n.top) n.bottom else n.top
                        grabDx = corner.first - event.x
                        grabDy = corner.second - event.y
                        performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
                    } else if (n.contains(event.x, event.y)) {
                        mode = Mode.MOVE
                    }
                }
                return true
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                // Second finger: abandon the gesture and restore the box.
                if (mode != Mode.NONE) {
                    rect.set(startRect)
                    mode = Mode.NONE
                    invalidate()
                }
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (mode == Mode.NONE) {
                    return false
                }
                if (mode == Mode.NEW_PENDING) {
                    if (hypot(event.x - originX, event.y - originY) <= slop) {
                        return true
                    }
                    mode = Mode.NEW
                }
                applyDrag(event.x, event.y)
                invalidate()
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                if (mode != Mode.NONE && mode != Mode.NEW_PENDING) {
                    rect.set(startRect)
                    invalidate()
                }
                mode = Mode.NONE
                parent.requestDisallowInterceptTouchEvent(false)
                return true
            }
            MotionEvent.ACTION_UP -> {
                val was = mode
                mode = Mode.NONE
                parent.requestDisallowInterceptTouchEvent(false)
                if (was == Mode.NONE || was == Mode.NEW_PENDING) {
                    // A tap: keep whatever box is there.
                    return true
                }
                mode = was
                applyDrag(event.x, event.y)
                mode = Mode.NONE
                if (boxNorm() != null) {
                    rect.set(sorted(rect))
                    boxCommitted?.invoke()
                } else {
                    // Too small to be a person box: restore instead of leaving a stray sliver.
                    rect.set(startRect)
                }
                invalidate()
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    private fun applyDrag(x: Float, y: Float) {
        val img = imageRect()
        when (mode) {
            Mode.NEW -> rect.set(
                originX.coerceIn(img.left, img.right),
                originY.coerceIn(img.top, img.bottom),
                x.coerceIn(img.left, img.right),
                y.coerceIn(img.top, img.bottom),
            )
            Mode.CORNER -> rect.set(
                anchorX,
                anchorY,
                (x + grabDx).coerceIn(img.left, img.right),
                (y + grabDy).coerceIn(img.top, img.bottom),
            )
            Mode.MOVE -> {
                val w = startRect.width()
                val h = startRect.height()
                val l = (startRect.left + x - originX).coerceIn(img.left, max(img.left, img.right - w))
                val t = (startRect.top + y - originY).coerceIn(img.top, max(img.top, img.bottom - h))
                rect.set(l, t, l + w, t + h)
            }
            else -> Unit
        }
    }

    /** Corner of [n] within reach of (x, y), nearest first. */
    private fun nearestCorner(n: RectF, x: Float, y: Float): Pair<Float, Float>? {
        val corners = listOf(n.left to n.top, n.right to n.top, n.right to n.bottom, n.left to n.bottom)
        // Small boxes: shrink the reach so the inside stays grabbable for moving.
        val reach = min(cornerHit, min(n.width(), n.height()) / 3f + 12f * density)
        return corners
            .map { it to hypot(it.first - x, it.second - y) }
            .filter { it.second <= reach }
            .minByOrNull { it.second }
            ?.first
    }

    /** On-screen rectangle of the letterboxed frame; the whole view when there is no frame. */
    private fun imageRect(): RectF {
        val bmp = frame ?: return RectF(0f, 0f, width.toFloat(), height.toFloat())
        val box = OverlayMath.contain(bmp.width, bmp.height, width, height)
        return RectF(box.dx, box.dy, box.dx + bmp.width * box.scale, box.dy + bmp.height * box.scale)
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
            if (mode != Mode.NEW) {
                // Corner knobs signal that the box can be resized / moved, not only redrawn.
                canvas.drawCircle(n.left, n.top, knobR, knobPaint)
                canvas.drawCircle(n.right, n.top, knobR, knobPaint)
                canvas.drawCircle(n.right, n.bottom, knobR, knobPaint)
                canvas.drawCircle(n.left, n.bottom, knobR, knobPaint)
            }
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
