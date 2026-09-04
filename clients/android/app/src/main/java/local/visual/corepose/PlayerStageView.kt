package local.visual.corepose

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.util.AttributeSet
import android.widget.FrameLayout

class PlayerStageView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : FrameLayout(context, attrs) {
    var onTap: (() -> Unit)? = null
    private var srcW = 16
    private var srcH = 9

    init {
        setBackgroundColor(0xFF000000.toInt())
        setOnClickListener { onTap?.invoke() }
    }

    fun setAspect(width: Int, height: Int) {
        val nextW = width.coerceAtLeast(1)
        val nextH = height.coerceAtLeast(1)
        if (nextW == srcW && nextH == srcH) {
            return
        }
        srcW = nextW
        srcH = nextH
        requestLayout()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        val maxH = (360f * resources.displayMetrics.density).toInt()
        val minH = (160f * resources.displayMetrics.density).toInt()
        val aspect = srcH.toFloat() / srcW.toFloat()
        val height = (width * aspect).toInt().coerceIn(minH, maxH)
        val wSpec = MeasureSpec.makeMeasureSpec(width.coerceAtLeast(1), MeasureSpec.EXACTLY)
        val hSpec = MeasureSpec.makeMeasureSpec(height, MeasureSpec.EXACTLY)
        super.onMeasure(wSpec, hSpec)
        setMeasuredDimension(width.coerceAtLeast(1), height)
    }
}

object OverlayStamp {
    private val bones = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFFA500.toInt()
        strokeWidth = 2f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val joints = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFF1744.toInt()
        style = Paint.Style.FILL
    }
    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF00FF00.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }

    fun stamp(src: Bitmap, frame: PoseFrame?): Bitmap {
        val out = src.copy(Bitmap.Config.ARGB_8888, true)
        if (frame == null) {
            return out
        }
        val canvas = Canvas(out)
        val box = frame.bbox ?: frame.poses.firstOrNull()?.let { OverlayMath.bboxFromPose(it) }
        if (box != null) {
            val (l, t) = OverlayMath.mapContain(
                box.x1, box.y1, frame.width, frame.height, out.width, out.height,
            )
            val (r, b) = OverlayMath.mapContain(
                box.x2, box.y2, frame.width, frame.height, out.width, out.height,
            )
            canvas.drawRect(l, t, r, b, boxPaint)
        }
        for (pose in frame.poses) {
            for (seg in OverlayMath.visibleSegments(
                pose, frame.width, frame.height, out.width, out.height, true,
            )) {
                canvas.drawLine(seg.x1, seg.y1, seg.x2, seg.y2, bones)
            }
            for (joint in OverlayMath.visibleJoints(
                pose, frame.width, frame.height, out.width, out.height, true,
            )) {
                canvas.drawCircle(joint.x, joint.y, 2f, joints)
            }
        }
        return out
    }
}
