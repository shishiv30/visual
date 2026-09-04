package local.visual.corepose

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

class PoseOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val bonePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFFA500.toInt()
        strokeWidth = 2f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val jointPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFF1744.toInt()
        style = Paint.Style.FILL
    }
    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF00FF00.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 3f * resources.displayMetrics.density
    }
    private val boxRect = RectF()

    private var poses: List<CocoPose> = emptyList()
    private var bbox: BBox? = null
    private var srcW = 1
    private var srcH = 1
    private var letterbox = true

    fun setPoses(
        next: List<CocoPose>,
        frameWidth: Int,
        frameHeight: Int,
        box: BBox? = null,
    ) {
        poses = next
        bbox = box ?: next.firstOrNull()?.let { OverlayMath.bboxFromPose(it) }
        srcW = frameWidth.coerceAtLeast(1)
        srcH = frameHeight.coerceAtLeast(1)
        postInvalidateOnAnimation()
    }

    fun setLetterbox(enabled: Boolean) {
        letterbox = enabled
        postInvalidateOnAnimation()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val vw = width
        val vh = height
        val box = bbox
        if (box != null) {
            val (l, t) = OverlayMath.mapPoint(box.x1, box.y1, srcW, srcH, vw, vh, letterbox)
            val (r, b) = OverlayMath.mapPoint(box.x2, box.y2, srcW, srcH, vw, vh, letterbox)
            boxRect.set(l, t, r, b)
            canvas.drawRect(boxRect, boxPaint)
        }
        for (pose in poses) {
            for (seg in OverlayMath.visibleSegments(pose, srcW, srcH, vw, vh, letterbox)) {
                canvas.drawLine(seg.x1, seg.y1, seg.x2, seg.y2, bonePaint)
            }
            for (joint in OverlayMath.visibleJoints(pose, srcW, srcH, vw, vh, letterbox)) {
                canvas.drawCircle(joint.x, joint.y, 2f, jointPaint)
            }
        }
    }
}
