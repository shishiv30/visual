package local.visual.corepose

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.media.MediaMetadataRetriever
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.view.ViewConfiguration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.Future
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

class TimelineStripView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    enum class DragKind { NONE, IN_HANDLE, OUT_HANDLE, PLAYHEAD, PAN }

    var onPlayhead: ((Int) -> Unit)? = null
    var onRange: ((Int, Int) -> Unit)? = null

    private val density = resources.displayMetrics.density
    private val rulerH = dp(22)
    private val filmH = dp(56)
    private val cellW = dp(88)
    private val edgePad = dp(20)
    private val handleStroke = 8f * density
    private val handleWing = 14f * density
    private val handleHit = dp(28)
    private val playheadHit = dp(8)
    private val panSlop = ViewConfiguration.get(context).scaledTouchSlop.toFloat()
    private val barH = dp(12)

    private val ink = Color.parseColor("#121212")
    private val paper = Color.parseColor("#F5F5F5")
    private val blue = Color.parseColor("#5E35B1")
    private val passGreen = Color.parseColor("#CE93D8")
    private val dim = Color.argb(140, 0, 0, 0)
    private val tick = Color.parseColor("#6F6F6F")
    private val rulerBg = Color.parseColor("#1A1A1A")
    private val filmBg = Color.parseColor("#242424")
    private val cellFill = Color.parseColor("#2A2A2A")
    private val cellBorder = Color.parseColor("#121212")

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = paper
        textSize = 11f * density
    }
    private val bitmapPaint = Paint(Paint.FILTER_BITMAP_FLAG)
    private val diamondPath = Path()

    private var durationMs = 1
    private var inMs = 0
    private var outMs = 1
    private var playheadMs = 0
    private var zoom = 1.0
    private var scrollXpx = 0.0
    private var path: String? = null
    private var retriever: MediaMetadataRetriever? = null
    private val retrieverLock = Any()
    private val thumbs = ConcurrentHashMap<Int, Bitmap>()
    private val inflight = ConcurrentHashMap<Int, Future<*>>()
    private var keyframesMs: List<Int> = emptyList()
    private var drag = DragKind.NONE
    private var pressX = 0f
    private var pressScroll = 0.0
    private var panning = false
    private var trimEnabled = true
    private var thumbExecutor = Executors.newSingleThreadExecutor()

    private val scaleDetector = ScaleGestureDetector(
        context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                applyZoom(zoom * detector.scaleFactor, detector.focusX.toDouble())
                return true
            }
        },
    )

    fun bindVideo(mediaPath: String, duration: Int) {
        clear()
        path = mediaPath
        durationMs = max(1, duration)
        inMs = 0
        outMs = durationMs
        playheadMs = 0
        zoom = 1.0
        scrollXpx = 0.0
        val next = MediaMetadataRetriever()
        try {
            next.setDataSource(mediaPath)
            synchronized(retrieverLock) {
                retriever = next
            }
        } catch (_: Exception) {
            next.release()
        }
        visibility = VISIBLE
        invalidate()
    }

    fun clear() {
        path = null
        synchronized(retrieverLock) {
            retriever?.release()
            retriever = null
        }
        inflight.values.forEach { it.cancel(true) }
        inflight.clear()
        thumbs.values.forEach { bmp ->
            if (!bmp.isRecycled) {
                bmp.recycle()
            }
        }
        thumbs.clear()
        keyframesMs = emptyList()
        invalidate()
    }

    fun setRange(startMs: Int, endMs: Int?) {
        val clamped = TimelineMath.clampRange(startMs, endMs, durationMs)
        inMs = clamped.first
        outMs = clamped.second
        invalidate()
    }

    fun setPlayheadMs(tMs: Int) {
        playheadMs = tMs.coerceIn(0, durationMs)
        invalidate()
    }

    fun setKeyframes(timesMs: List<Int>) {
        keyframesMs = timesMs.map { it }.distinct().sorted()
        invalidate()
    }

    fun setTrimEnabled(enabled: Boolean) {
        trimEnabled = enabled
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        setMeasuredDimension(width, rulerH + filmH + barH)
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        clear()
        thumbExecutor.shutdownNow()
        thumbExecutor = Executors.newSingleThreadExecutor()
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (path == null) {
            return false
        }
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                pressX = event.x
                pressScroll = scrollXpx
                panning = false
                parent.requestDisallowInterceptTouchEvent(true)
                val hit = hit(event.x)
                if (hit == DragKind.IN_HANDLE || hit == DragKind.OUT_HANDLE) {
                    drag = hit
                    if (hit == DragKind.IN_HANDLE) {
                        emitPlayhead(inMs)
                    } else {
                        emitPlayhead(outMs)
                    }
                    return true
                }
                val keyMs = hitKeyframe(event.x)
                if (keyMs != null) {
                    drag = DragKind.NONE
                    emitPlayhead(keyMs)
                    return true
                }
                drag = if (hit == DragKind.NONE) DragKind.PLAYHEAD else hit
                when (drag) {
                    DragKind.PLAYHEAD -> {
                        if (hit == DragKind.NONE) {
                            seekToX(event.x)
                        }
                    }
                    else -> Unit
                }
                return true
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                drag = DragKind.NONE
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (scaleDetector.isInProgress) {
                    return true
                }
                val dx = event.x - pressX
                if (drag == DragKind.PLAYHEAD && !panning && zoom > 1.0 + 1e-6 && abs(dx) > panSlop) {
                    drag = DragKind.PAN
                    panning = true
                }
                when (drag) {
                    DragKind.PAN -> setScroll(pressScroll - dx)
                    DragKind.IN_HANDLE -> {
                        val clamped = TimelineMath.clampRange(msOf(event.x), outMs, durationMs)
                        inMs = clamped.first
                        outMs = clamped.second
                        emitPlayhead(inMs)
                        onRange?.invoke(inMs, outMs)
                    }
                    DragKind.OUT_HANDLE -> {
                        val clamped = TimelineMath.clampRange(inMs, msOf(event.x), durationMs)
                        inMs = clamped.first
                        outMs = clamped.second
                        emitPlayhead(outMs)
                        onRange?.invoke(inMs, outMs)
                    }
                    DragKind.PLAYHEAD -> seekToX(event.x)
                    DragKind.NONE -> Unit
                }
                invalidate()
                return true
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                drag = DragKind.NONE
                panning = false
                parent.requestDisallowInterceptTouchEvent(false)
                return true
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(ink)
        if (path == null) {
            return
        }
        paintRuler(canvas)
        paintFilm(canvas)
        paintDim(canvas)
        paintTrimEdge(canvas, inMs, start = true)
        paintTrimEdge(canvas, outMs, start = false)
        paintKeyframes(canvas)
        val x = xOf(playheadMs.toDouble())
        strokePaint.color = paper
        strokePaint.strokeWidth = 2f
        strokePaint.strokeCap = Paint.Cap.BUTT
        canvas.drawLine(x, 0f, x, (rulerH + filmH).toFloat(), strokePaint)
        paintScrollBar(canvas)
    }

    private fun paintRuler(canvas: Canvas) {
        fillPaint.color = rulerBg
        canvas.drawRect(contentLeft(), 0f, contentRight(), rulerH.toFloat(), fillPaint)
        val span = durationMs.toDouble()
        val step = TimelineMath.rulerTickMs(span, viewportW(), zoom)
        val fine = step < 1000.0
        strokePaint.color = tick
        strokePaint.strokeWidth = 1f
        var tMs = 0.0
        while (tMs <= span + 0.1) {
            val x = xOf(tMs)
            if (x >= -40f && x <= width + 40f) {
                canvas.drawLine(x, (rulerH - 6).toFloat(), x, rulerH.toFloat(), strokePaint)
                canvas.drawText(
                    TimelineMath.formatRulerTime(tMs, fine),
                    x + 3f,
                    14f * density,
                    textPaint,
                )
            }
            tMs += step
        }
        val endX = xOf(span)
        if (abs(endX - xOf(max(0.0, tMs - step))) > 40f) {
            canvas.drawLine(endX, (rulerH - 6).toFloat(), endX, rulerH.toFloat(), strokePaint)
            val label = TimelineMath.formatRulerTime(span, fine)
            canvas.drawText(label, endX - textPaint.measureText(label), 14f * density, textPaint)
        }
    }

    private fun paintFilm(canvas: Canvas) {
        fillPaint.color = filmBg
        canvas.drawRect(
            contentLeft(),
            rulerH.toFloat(),
            contentRight(),
            (rulerH + filmH).toFloat(),
            fillPaint,
        )
        val content = TimelineMath.contentWidthPx(viewportW(), zoom)
        val n = max(1, (content / cellW).roundToInt())
        val cell = content / n
        val startI = max(0, (scrollXpx / cell).toInt() - 1)
        val endI = min(n, ((scrollXpx + viewportW()) / cell).toInt() + 2)
        strokePaint.color = cellBorder
        strokePaint.strokeWidth = 1f
        for (i in startI until endI) {
            val x0 = contentLeft() + (i * cell - scrollXpx).toFloat()
            val tMs = (i + 0.5) / n * durationMs
            val dest = RectF(x0, rulerH.toFloat(), (x0 + cell).toFloat(), (rulerH + filmH).toFloat())
            val pix = thumbAt(tMs.toInt())
            if (pix == null || pix.isRecycled) {
                fillPaint.color = cellFill
                canvas.drawRect(dest, fillPaint)
            } else {
                canvas.drawBitmap(pix, null, dest, bitmapPaint)
            }
            canvas.drawRect(dest, strokePaint)
        }
    }

    private fun paintDim(canvas: Canvas) {
        fillPaint.color = dim
        val leftW = max(contentLeft(), xOf(inMs.toDouble()))
        canvas.drawRect(contentLeft(), rulerH.toFloat(), leftW, (rulerH + filmH).toFloat(), fillPaint)
        val rightX = xOf(outMs.toDouble())
        canvas.drawRect(rightX, rulerH.toFloat(), contentRight(), (rulerH + filmH).toFloat(), fillPaint)
    }

    private fun paintTrimEdge(canvas: Canvas, tMs: Int, start: Boolean) {
        val x = xOf(tMs.toDouble())
        val top = rulerH.toFloat()
        val bot = (rulerH + filmH).toFloat()
        val half = handleStroke / 2f
        fillPaint.color = blue
        canvas.drawRect(x - half, top, x + half, bot, fillPaint)
        strokePaint.color = blue
        strokePaint.strokeWidth = handleStroke
        strokePaint.strokeCap = Paint.Cap.SQUARE
        if (start) {
            canvas.drawLine(x, top, x + handleWing, top, strokePaint)
            canvas.drawLine(x, bot, x + handleWing, bot, strokePaint)
        } else {
            canvas.drawLine(x, top, x - handleWing, top, strokePaint)
            canvas.drawLine(x, bot, x - handleWing, bot, strokePaint)
        }
    }

    private fun paintKeyframes(canvas: Canvas) {
        val y = (rulerH + 8).toFloat()
        fillPaint.color = passGreen
        strokePaint.color = ink
        strokePaint.strokeWidth = 1f
        strokePaint.style = Paint.Style.STROKE
        for (tMs in keyframesMs) {
            val x = xOf(tMs.toDouble())
            if (x < -12f || x > width + 12f) {
                continue
            }
            diamondPath.reset()
            diamondPath.moveTo(x, y - 6f)
            diamondPath.lineTo(x + 5f, y)
            diamondPath.lineTo(x, y + 6f)
            diamondPath.lineTo(x - 5f, y)
            diamondPath.close()
            canvas.drawPath(diamondPath, fillPaint)
            canvas.drawPath(diamondPath, strokePaint)
        }
        strokePaint.style = Paint.Style.STROKE
    }

    private fun paintScrollBar(canvas: Canvas) {
        val maximum = TimelineMath.maxScrollX(viewportW(), zoom)
        if (maximum <= 0) {
            return
        }
        val track = RectF(
            contentLeft(),
            (rulerH + filmH).toFloat(),
            contentRight(),
            (rulerH + filmH + barH).toFloat(),
        )
        fillPaint.color = Color.parseColor("#1A1A1A")
        canvas.drawRect(track, fillPaint)
        val inner = contentRight() - contentLeft()
        val thumbW = (viewportW() / (viewportW() + maximum) * inner).toFloat().coerceAtLeast(24f * density)
        val maxX = inner - thumbW
        val x = contentLeft() + if (maximum <= 0) 0f else (scrollXpx / maximum * maxX).toFloat()
        fillPaint.color = Color.parseColor("#5E35B1")
        canvas.drawRoundRect(x, track.top + 3f, x + thumbW, track.bottom - 3f, 4f, 4f, fillPaint)
    }

    private fun thumbAt(tMs: Int): Bitmap? {
        val key = (tMs / 80f).roundToInt() * 80
        val cached = thumbs[key]
        if (cached != null) {
            return cached
        }
        requestThumb(key)
        return null
    }

    private fun requestThumb(key: Int) {
        if (thumbs.containsKey(key) || inflight.containsKey(key)) {
            return
        }
        if (retriever == null) {
            return
        }
        inflight[key] = ensureExecutor().submit {
            val bmp = try {
                synchronized(retrieverLock) {
                    retriever?.getFrameAtTime(key * 1000L, MediaMetadataRetriever.OPTION_CLOSEST)
                }
            } catch (_: Exception) {
                null
            }
            val scaled = bmp?.let { scaleThumb(it) }
            post {
                inflight.remove(key)
                if (!isAttachedToWindow || path == null) {
                    if (scaled != null && !scaled.isRecycled) {
                        scaled.recycle()
                    }
                    return@post
                }
                if (scaled != null) {
                    thumbs[key]?.let { old ->
                        if (old != scaled && !old.isRecycled) {
                            old.recycle()
                        }
                    }
                    thumbs[key] = scaled
                    invalidate()
                }
            }
        }
    }

    private fun scaleThumb(src: Bitmap): Bitmap {
        val w = (cellW * 2).coerceAtLeast(1)
        val h = (filmH * 2).coerceAtLeast(1)
        val scaled = Bitmap.createScaledBitmap(src, w, h, true)
        if (scaled != src) {
            src.recycle()
        }
        return scaled
    }

    private fun hit(x: Float): DragKind {
        if (trimEnabled) {
            val inDist = abs(x - xOf(inMs.toDouble()))
            val outDist = abs(x - xOf(outMs.toDouble()))
            val inHit = inDist <= handleHit
            val outHit = outDist <= handleHit
            when {
                inHit && outHit -> {
                    return if (inDist <= outDist) DragKind.IN_HANDLE else DragKind.OUT_HANDLE
                }
                inHit -> return DragKind.IN_HANDLE
                outHit -> return DragKind.OUT_HANDLE
            }
        }
        if (abs(x - xOf(playheadMs.toDouble())) <= playheadHit) {
            return DragKind.PLAYHEAD
        }
        return DragKind.NONE
    }

    private fun hitKeyframe(x: Float): Int? {
        return TimelineMath.nearestKeyframeMs(
            (x - edgePad).toDouble(),
            keyframesMs,
            durationMs.toDouble(),
            viewportW(),
            zoom,
            scrollXpx,
            dp(10).toDouble(),
        )
    }

    private fun seekToX(x: Float) {
        emitPlayhead(msOf(x))
        invalidate()
    }

    private fun emitPlayhead(tMs: Int) {
        playheadMs = tMs.coerceIn(0, durationMs)
        onPlayhead?.invoke(playheadMs)
    }

    private fun applyZoom(nextZoom: Double, anchorX: Double) {
        val kept = TimelineMath.zoomKeepingMs(
            nextZoom,
            anchorX - edgePad,
            durationMs.toDouble(),
            viewportW(),
            zoom,
            scrollXpx,
        )
        zoom = kept.first
        scrollXpx = kept.second
        invalidate()
    }

    private fun setScroll(next: Double) {
        scrollXpx = TimelineMath.clampScrollX(next, viewportW(), zoom)
        invalidate()
    }

    private fun viewportW(): Int = max(1, width - 2 * edgePad)

    private fun contentLeft(): Float = edgePad.toFloat()

    private fun contentRight(): Float = (width - edgePad).toFloat()

    private fun xOf(tMs: Double): Float {
        return contentLeft() + TimelineMath.msToX(
            tMs,
            durationMs.toDouble(),
            viewportW(),
            zoom,
            scrollXpx,
        ).toFloat()
    }

    private fun msOf(x: Float): Int {
        return TimelineMath.xToMs(
            (x - edgePad).toDouble(),
            durationMs.toDouble(),
            viewportW(),
            zoom,
            scrollXpx,
        ).roundToInt()
    }

    private fun ensureExecutor() = synchronized(retrieverLock) {
        if (thumbExecutor.isShutdown) {
            thumbExecutor = Executors.newSingleThreadExecutor()
        }
        thumbExecutor
    }

    private fun dp(value: Int): Int = (value * density).roundToInt()
}
