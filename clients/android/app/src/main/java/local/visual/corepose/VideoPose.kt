package local.visual.corepose

import android.graphics.Bitmap
import android.graphics.Matrix
import android.media.MediaMetadataRetriever
import android.os.Build
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker

data class PoseLandmarkers(
    val video: PoseLandmarker,
    val crop: PoseLandmarker,
) {
    fun close() {
        video.close()
        crop.close()
    }
}

object VideoPose {
    const val MAX_MS = 120_000L

    fun analyze(
        retriever: MediaMetadataRetriever,
        markers: PoseLandmarkers,
        device: String,
        startMs: Long = 0L,
        endMs: Long = MAX_MS,
        seeds: List<SeedMark> = emptyList(),
        seedBox: NormBox? = null,
        fpsIn: Double = 30.0,
        onProgress: (doneMs: Long, totalMs: Long) -> Unit,
    ): List<PoseFrame> {
        val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            ?.toLongOrNull()
            ?.coerceAtLeast(0L)
            ?: 0L
        val fps = if (fpsIn > 1.0) fpsIn else 30.0
        val lo = startMs.coerceAtLeast(0L)
        val hi = endMs.coerceAtMost(durationMs.coerceAtMost(lo + MAX_MS)).coerceAtLeast(lo)
        val rotation = if (Build.VERSION.SDK_INT >= 27) {
            0
        } else {
            retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)
                ?.toIntOrNull()
                ?: 0
        }
        val timedSeeds = ClipRange.collectSeeds(seeds, seedBox)
        val halfMs = ClipRange.halfMs(fps)
        val stepMs = ClipRange.strideMs(fps)
        val locator = PoseLocator(device)
        val frames = ArrayList<PoseFrame>()
        var tMs = lo
        while (tMs <= hi) {
            onProgress(tMs - lo, (hi - lo).coerceAtLeast(1L))
            val option = MediaMetadataRetriever.OPTION_CLOSEST
            val raw = retriever.getFrameAtTime(tMs * 1000, option)
            if (raw != null) {
                val bmp = raw.rotated(rotation)
                if (bmp !== raw) {
                    raw.recycle()
                }
                frames.add(locator.inferFrame(bmp, tMs.toDouble(), timedSeeds, seedBox, halfMs, markers))
                bmp.recycle()
            }
            tMs += stepMs
        }
        return PoseTrack.fillLowScore(frames)
    }

    fun analyzeBitmap(
        bitmap: Bitmap,
        markers: PoseLandmarkers,
        device: String,
        seeds: List<SeedMark> = emptyList(),
        seedBox: NormBox? = null,
    ): List<PoseFrame> {
        val locator = PoseLocator(device)
        val timed = ClipRange.collectSeeds(seeds, seedBox)
        return PoseTrack.fillLowScore(
            listOf(locator.inferFrame(bitmap, 0.0, timed, seedBox, 1e9, markers)),
        )
    }
}

class PoseLocator(private val device: String) {
    private var hist: FloatArray? = null
    private var box: PixelBox? = null
    private var lastMapped: MappedPeople? = null
    private var lastTs = -1L

    fun inferFrame(
        bmp: Bitmap,
        tMs: Double,
        seeds: List<SeedMark>,
        seedBox: NormBox?,
        halfMs: Double,
        markers: PoseLandmarkers,
    ): PoseFrame {
        val w = bmp.width
        val h = bmp.height
        val pixels = IntArray(w * h)
        bmp.getPixels(pixels, 0, w, 0, 0, w, h)
        val hit = ClipRange.seedAt(tMs, seeds, halfMs)
        when {
            hit != null -> {
                box = PersonRoi.denormBox(hit.box, w, h)
                hist = PersonRoi.buildHist(pixels, w, h, box!!)
            }
            hist == null && seedBox != null -> {
                box = PersonRoi.denormBox(seedBox, w, h)
                hist = PersonRoi.buildHist(pixels, w, h, box!!)
            }
            hist != null && box != null -> {
                box = PersonRoi.search(pixels, w, h, hist!!, box!!)
            }
        }
        val mapped = detect(bmp, tMs.toLong(), box, markers)
        if (mapped.poses.isNotEmpty() && mapped.bboxes.isNotEmpty()) {
            val det = mapped.bboxes[0]
            box = PixelBox(det.x1.toDouble(), det.y1.toDouble(), det.x2.toDouble(), det.y2.toDouble())
            val nextHist = PersonRoi.buildHist(pixels, w, h, box!!)
            hist = hist?.let { PersonRoi.blendHist(it, nextHist) } ?: nextHist
            lastMapped = mapped
        } else {
            lastMapped = null
        }
        val pose = mapped.poses.firstOrNull()
        val blaze = mapped.blazePeople.firstOrNull().orEmpty()
        return PoseFrame(
            tMs.toLong(),
            if (pose != null) listOf(pose) else emptyList(),
            w,
            h,
            blaze,
            mapped.bboxes.firstOrNull(),
        )
    }

    private fun detect(
        bmp: Bitmap,
        tMs: Long,
        roi: PixelBox?,
        markers: PoseLandmarkers,
    ): MappedPeople {
        var mapped: MappedPeople? = null
        if (roi != null) {
            val cropped = detectCrop(bmp, roi, markers.crop)
            val ok = PoseFilter.isPlausible(cropped, bmp.width, bmp.height) || cropped.poses.isNotEmpty()
            if (ok && !PoseFilter.cropDisagreesWithPrev(lastMapped, cropped)) {
                mapped = cropped
            }
        }
        if (mapped == null) {
            mapped = detectFull(bmp, tMs, markers.video)
            mapped = PoseFilter.pickPrimary(mapped, lastMapped?.bboxes?.firstOrNull())
            if (!PoseFilter.isPlausible(mapped, bmp.width, bmp.height)) {
                val retryBox = mapped.bboxes.firstOrNull() ?: lastMapped?.bboxes?.firstOrNull()
                if (retryBox != null) {
                    val retry = detectCrop(bmp, PoseFilter.cropBoxForRetry(retryBox, bmp.width, bmp.height), markers.crop)
                    val retryOk = PoseFilter.isPlausible(retry, bmp.width, bmp.height) || retry.poses.isNotEmpty()
                    if (retryOk && !PoseFilter.cropDisagreesWithPrev(lastMapped, retry)) {
                        mapped = retry
                    }
                }
                if (!PoseFilter.isPlausible(mapped, bmp.width, bmp.height) && mapped.poses.isEmpty()) {
                    mapped = MappedPeople(emptyList(), emptyList(), emptyList())
                }
            }
        }
        return PoseFilter.emaSmooth(lastMapped, mapped)
    }

    private fun detectCrop(src: Bitmap, roi: PixelBox, marker: PoseLandmarker): MappedPeople {
        val spec = PersonRoi.cropRect(roi, src.width, src.height)
        val cw = (spec.x2 - spec.ox).coerceAtLeast(2)
        val ch = (spec.y2 - spec.oy).coerceAtLeast(2)
        var crop = if (cw >= src.width - 1 && ch >= src.height - 1) {
            src
        } else {
            Bitmap.createBitmap(src, spec.ox, spec.oy, cw, ch)
        }
        if (spec.scale > 1.0 + 1e-6) {
            val sw = (cw * spec.scale).toInt().coerceAtLeast(2)
            val sh = (ch * spec.scale).toInt().coerceAtLeast(2)
            val next = Bitmap.createScaledBitmap(crop, sw, sh, true)
            if (crop !== src) {
                crop.recycle()
            }
            crop = next
        }
        val result = marker.detect(BitmapImageBuilder(crop).build())
        val mapped = PoseMapper.fromLandmarks(result.landmarks(), crop.width, crop.height, device)
        if (crop !== src) {
            crop.recycle()
        }
        val picked = PoseFilter.pickPrimary(mapped, lastMapped?.bboxes?.firstOrNull())
        return remap(picked, spec)
    }

    private fun detectFull(src: Bitmap, tMs: Long, marker: PoseLandmarker): MappedPeople {
        val ts = maxOf(tMs, lastTs + 1)
        lastTs = ts
        val result = marker.detectForVideo(BitmapImageBuilder(src).build(), ts)
        return PoseMapper.fromLandmarks(result.landmarks(), src.width, src.height, device)
    }

    private fun remap(mapped: MappedPeople, spec: CropSpec): MappedPeople {
        fun pt(x: Float, y: Float): Pair<Float, Float> {
            val (nx, ny) = PersonRoi.remapPoint(x.toDouble(), y.toDouble(), spec.ox, spec.oy, spec.scale)
            return nx.toFloat() to ny.toFloat()
        }
        val poses = mapped.poses.map { pose ->
            CocoPose(
                pose.keypoints.map { kp ->
                    val (x, y) = pt(kp.x, kp.y)
                    CocoKeypoint(x, y, kp.confidence)
                },
            )
        }
        val blaze = mapped.blazePeople.map { person ->
            person.map { joint ->
                val (x, y) = pt(joint.x, joint.y)
                BlazeJoint(x, y, joint.z, joint.confidence)
            }
        }
        val boxes = mapped.bboxes.map { box ->
            val (x1, y1) = pt(box.x1, box.y1)
            val (x2, y2) = pt(box.x2, box.y2)
            BBox(x1, y1, x2, y2)
        }
        return MappedPeople(poses, blaze, boxes)
    }
}

private fun Bitmap.rotated(degrees: Int): Bitmap {
    if (degrees % 360 == 0) {
        return this
    }
    val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
    return Bitmap.createBitmap(this, 0, 0, width, height, matrix, true)
}
