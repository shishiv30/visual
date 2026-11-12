package local.visual.corepose

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Rect
import android.graphics.RectF
import android.media.MediaMetadataRetriever
import android.os.Build
import android.util.AttributeSet
import android.view.HapticFeedbackConstants
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
    enum class DragKind { NONE, IN_HANDLE, OUT_HANDLE, EITHER_HANDLE, PLAYHEAD, TAP_OR_PAN, PAN }

    var onPlayhead: ((Int) -> Unit)? = null
    var onRange: ((Int, Int) -> Unit)? = null

    /**
     * true when a continuous drag (handle / playhead scrub) starts, false when it ends.
     * Listeners should decode cheap preview frames while true and the exact frame on false.
     */
    var onScrubbing: ((Boolean) -> Unit)? = null

    /** True while the user is dragging a handle or the playhead. */
    var isScrubbing: Boolean = false
        private set

    private val density = resources.displayMetrics.density
    private val rulerH = dp(22)
    private val filmH = dp(56)
    private val cellW = dp(88)
    private val edgePad = dp(20)
    private val handleStroke = 8f * density
    private val handleWing = 14f * density
    private val handleHit = dp(28)
    private val playheadHit = dp(16)
    private val scrubBand = dp(48).toDouble()
    private val autoScrollZone = dp(32).toDouble()
    private val autoScrollStep = dp(14).toDouble()
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
    private var lastX = 0f
    private var activePointer = MotionEvent.INVALID_POINTER_ID
    // Time value the current drag is steering; moved by finger deltas (not absolute x) so the
    // handle never jumps to the finger and fine-scrub rates can apply.
    private var grabMs = 0.0
    private var scrubRate = 1.0
    private var trimEnabled = true
    private val bubbleRect = RectF()
    private val autoScroll = object : Runnable {
        override fun run() {
            if (!stepAutoScroll()) {
                return
            }
            postOnAnimation(this)
        }
    }
    private var autoScrolling = false
    private var thumbExecutor = Executors.newSingleThreadExecutor()

    private val scaleDetector = ScaleGestureDetector(
        context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScaleBegin(detector: ScaleGestureDetector): Boolean {
                drag = DragKind.NONE
                endScrub()
                return true
            }

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
        drag = DragKind.NONE
        removeCallbacks(autoScroll)
        autoScrolling = false
        endScrub()
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

    fun playheadMs(): Int = playheadMs

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

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        super.onLayout(changed, left, top, right, bottom)
        // Android 10+ gesture navigation claims the screen edges for "back". The In/Out handles
        // default to t=0 and t=end, i.e. right next to both edges, so presses on them were being
        // stolen by the system. Opt the strip's two edge columns out of the back gesture.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val w = right - left
            val h = bottom - top
            val edge = edgePad + handleHit
            systemGestureExclusionRects = listOf(
                Rect(0, 0, min(w, edge), h),
                Rect(max(0, w - edge), 0, w, h),
            )
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (path == null) {
            return false
        }
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                activePointer = event.getPointerId(0)
                pressX = event.x
                lastX = event.x
                pressScroll = scrollXpx
                scrubRate = 1.0
                parent.requestDisallowInterceptTouchEvent(true)
                val hit = hit(event.x)
                if (hit == DragKind.IN_HANDLE || hit == DragKind.OUT_HANDLE || hit == DragKind.EITHER_HANDLE) {
                    drag = hit
                    grabMs = if (hit == DragKind.OUT_HANDLE) outMs.toDouble() else inMs.toDouble()
                    performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
                    beginScrub()
                    if (hit != DragKind.EITHER_HANDLE) {
                        emitPlayhead(grabMs.roundToInt())
                    }
                    invalidate()
                    return true
                }
                val keyMs = hitKeyframe(event.x)
                if (keyMs != null) {
                    drag = DragKind.NONE
                    emitPlayhead(keyMs)
                    invalidate()
                    return true
                }
                if (hit == DragKind.PLAYHEAD || zoom <= 1.0 + 1e-6) {
                    // Unzoomed: press anywhere = jump + scrub. On the playhead: scrub from it.
                    drag = DragKind.PLAYHEAD
                    if (hit != DragKind.PLAYHEAD) {
                        emitPlayhead(msOf(event.x))
                    }
                    grabMs = playheadMs.toDouble()
                    beginScrub()
                } else {
                    // Zoomed: a drag on empty film pans; only a clean tap seeks (on UP).
                    drag = DragKind.TAP_OR_PAN
                }
                invalidate()
                return true
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                drag = DragKind.NONE
                endScrub()
                return true
            }
            MotionEvent.ACTION_POINTER_UP -> {
                val upId = event.getPointerId(event.actionIndex)
                if (upId == activePointer) {
                    val keep = if (event.actionIndex == 0) 1 else 0
                    activePointer = event.getPointerId(keep)
                    lastX = event.getX(keep)
                }
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (scaleDetector.isInProgress) {
                    return true
                }
                val idx = event.findPointerIndex(activePointer)
                if (idx < 0) {
                    return true
                }
                val x = event.getX(idx)
                val y = event.getY(idx)
                val dx = x - lastX
                lastX = x
                if (drag == DragKind.EITHER_HANDLE) {
                    if (abs(x - pressX) <= panSlop / 2f) {
                        return true
                    }
                    // Handles overlap: the first move direction decides which one is grabbed.
                    drag = if (x < pressX) DragKind.IN_HANDLE else DragKind.OUT_HANDLE
                    grabMs = if (drag == DragKind.IN_HANDLE) inMs.toDouble() else outMs.toDouble()
                    applyDrag((x - pressX).toDouble())
                    invalidate()
                    return true
                }
                if (drag == DragKind.TAP_OR_PAN && abs(x - pressX) > panSlop) {
                    drag = DragKind.PAN
                }
                when (drag) {
                    DragKind.PAN -> setScroll(pressScroll - (x - pressX))
                    DragKind.IN_HANDLE, DragKind.OUT_HANDLE, DragKind.PLAYHEAD -> {
                        scrubRate = TimelineMath.scrubRate(
                            TimelineMath.offStripPx(y.toDouble(), 0.0, (rulerH + filmH).toDouble()),
                            scrubBand,
                        )
                        applyDrag(dx.toDouble())
                        ensureAutoScroll()
                    }
                    else -> Unit
                }
                invalidate()
                return true
            }
            MotionEvent.ACTION_UP -> {
                if (drag == DragKind.TAP_OR_PAN) {
                    emitPlayhead(msOf(event.x))
                }
                finishGesture()
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                finishGesture()
                return true
            }
        }
        return true
    }

    private fun finishGesture() {
        drag = DragKind.NONE
        activePointer = MotionEvent.INVALID_POINTER_ID
        parent.requestDisallowInterceptTouchEvent(false)
        endScrub()
        invalidate()
    }

    /** Move the dragged handle / playhead by a finger delta [dxPx], scaled by the scrub rate. */
    private fun applyDrag(dxPx: Double) {
        grabMs += TimelineMath.dxToMs(dxPx, durationMs.toDouble(), viewportW(), zoom, scrubRate)
        when (drag) {
            DragKind.IN_HANDLE -> {
                grabMs = grabMs.coerceIn(0.0, max(0, outMs - TimelineMath.MIN_RANGE_MS).toDouble())
                val clamped = TimelineMath.clampRange(grabMs.roundToInt(), outMs, durationMs)
                if (clamped.first != inMs || clamped.second != outMs) {
                    inMs = clamped.first
                    outMs = clamped.second
                    onRange?.invoke(inMs, outMs)
                }
                emitPlayhead(inMs)
            }
            DragKind.OUT_HANDLE -> {
                val lo = min(durationMs, inMs + TimelineMath.MIN_RANGE_MS).toDouble()
                grabMs = grabMs.coerceIn(lo, durationMs.toDouble())
                val clamped = TimelineMath.clampRange(inMs, grabMs.roundToInt(), durationMs)
                if (clamped.first != inMs || clamped.second != outMs) {
                    inMs = clamped.first
                    outMs = clamped.second
                    onRange?.invoke(inMs, outMs)
                }
                emitPlayhead(outMs)
            }
            DragKind.PLAYHEAD -> {
                grabMs = grabMs.coerceIn(0.0, durationMs.toDouble())
                emitPlayhead(grabMs.roundToInt())
            }
            else -> Unit
        }
    }

    private fun ensureAutoScroll() {
        if (autoScrolling || zoom <= 1.0 + 1e-6) {
            return
        }
        autoScrolling = true
        postOnAnimation(autoScroll)
    }

    /** One auto-scroll frame; returns false when auto-scrolling should stop. */
    private fun stepAutoScroll(): Boolean {
        val active = drag == DragKind.IN_HANDLE || drag == DragKind.OUT_HANDLE || drag == DragKind.PLAYHEAD
        if (!active || zoom <= 1.0 + 1e-6) {
            autoScrolling = false
            return false
        }
        val step = TimelineMath.edgeAutoScrollPx(
            (lastX - edgePad).toDouble(),
            viewportW(),
            autoScrollZone,
            autoScrollStep,
        )
        if (step != 0.0) {
            val before = scrollXpx
            setScroll(scrollXpx + step)
            val moved = scrollXpx - before
            if (moved != 0.0) {
                // Content slid under a still finger: carry the grabbed time with it (rate 1).
                val keep = scrubRate
                scrubRate = 1.0
                applyDrag(moved)
                scrubRate = keep
                invalidate()
            }
        }
        return true
    }

    private fun beginScrub() {
        if (!isScrubbing) {
            isScrubbing = true
            onScrubbing?.invoke(true)
        }
    }

    private fun endScrub() {
        scrubRate = 1.0
        if (isScrubbing) {
            isScrubbing = false
            onScrubbing?.invoke(false)
        }
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
        paintScrubBubble(canvas)
    }

    /** Exact time (and fine-scrub rate) above the finger while dragging — the finger hides the handle. */
    private fun paintScrubBubble(canvas: Canvas) {
        val tMs = when (drag) {
            DragKind.IN_HANDLE -> inMs
            DragKind.OUT_HANDLE -> outMs
            DragKind.PLAYHEAD -> playheadMs
            else -> return
        }
        val secs = tMs / 1000.0
        var label = String.format(java.util.Locale.US, "%d:%05.2f", (secs / 60).toInt(), secs % 60)
        if (scrubRate < 1.0) {
            label += "  " + rateLabel(scrubRate)
        }
        val padH = 6f * density
        val w = textPaint.measureText(label) + padH * 2
        val h = rulerH.toFloat() - 2f
        val cx = xOf(tMs.toDouble()).coerceIn(w / 2f, width - w / 2f)
        bubbleRect.set(cx - w / 2f, 1f, cx + w / 2f, 1f + h)
        fillPaint.color = blue
        canvas.drawRoundRect(bubbleRect, h / 2f, h / 2f, fillPaint)
        val baseline = bubbleRect.centerY() - (textPaint.descent() + textPaint.ascent()) / 2f
        canvas.drawText(label, bubbleRect.left + padH, baseline, textPaint)
    }

    private fun rateLabel(rate: Double): String = when {
        rate >= 0.5 -> "½×"
        rate >= 0.25 -> "¼×"
        else -> "⅒×"
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
        val active = (start && drag == DragKind.IN_HANDLE) || (!start && drag == DragKind.OUT_HANDLE)
        val half = handleStroke / 2f
        fillPaint.color = if (active) passGreen else blue
        canvas.drawRect(x - half, top, x + half, bot, fillPaint)
        strokePaint.color = fillPaint.color
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
                // Filmstrip cells don't need frame accuracy; the nearest sync frame decodes in a
                // fraction of the time and keeps the shared hardware decoder free for the preview.
                synchronized(retrieverLock) {
                    retriever?.getFrameAtTime(key * 1000L, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
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
                    // Handles nearly on top of each other: let the first move direction decide.
                    if (abs(inDist - outDist) < dp(8)) {
                        return DragKind.EITHER_HANDLE
                    }
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
