package local.visual.corepose

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.media.MediaMetadataRetriever
import android.net.Uri
import java.io.File
import java.io.FileOutputStream

class Ingest(
    private val context: android.content.Context,
    private val library: Library,
) {
    fun fromUri(uri: Uri, trimStartMs: Long = 0L, trimEndMs: Long? = null): ClipMeta {
        val mime = context.contentResolver.getType(uri).orEmpty()
        val name = uri.lastPathSegment.orEmpty().lowercase()
        val image = mime.startsWith("image/") || IMAGE_EXT.any { name.endsWith(it) }
        return if (image) fromImage(uri) else fromVideo(uri, trimStartMs, trimEndMs)
    }

    /** Returns the duration in ms for the given URI without copying the file, or null if unreadable. */
    fun probeDurationMs(uri: Uri): Long? {
        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(context, uri)
            retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull()
        } catch (_: Exception) {
            null
        } finally {
            retriever.release()
        }
    }

    fun fromFile(file: File, image: Boolean = false): ClipMeta {
        return if (image) {
            val clipId = library.newClipId()
            val dir = library.clipDir(clipId)
            dir.mkdirs()
            val dest = File(dir, "clip.jpg")
            file.copyTo(dest, overwrite = true)
            finishImage(clipId, dest)
        } else {
            val clipId = library.newClipId()
            val dir = library.clipDir(clipId)
            dir.mkdirs()
            val dest = File(dir, "clip.mp4")
            file.copyTo(dest, overwrite = true)
            finishVideo(clipId, dest)
        }
    }

    private fun fromVideo(uri: Uri, trimStartMs: Long = 0L, trimEndMs: Long? = null): ClipMeta {
        val clipId = library.newClipId()
        val dir = library.clipDir(clipId)
        dir.mkdirs()
        val dest = File(dir, "clip.mp4")
        copyUri(uri, dest)
        return finishVideo(clipId, dest, trimStartMs, trimEndMs)
    }

    private fun fromImage(uri: Uri): ClipMeta {
        val clipId = library.newClipId()
        val dir = library.clipDir(clipId)
        dir.mkdirs()
        val dest = File(dir, "clip.jpg")
        copyUri(uri, dest)
        return finishImage(clipId, dest)
    }

    private fun finishVideo(
        clipId: String,
        dest: File,
        trimStartMs: Long = 0L,
        trimEndMs: Long? = null,
    ): ClipMeta {
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(dest.absolutePath)
            var width = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)
                ?.toIntOrNull()
                ?: 1
            var height = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)
                ?.toIntOrNull()
                ?: 1
            val rotation = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)
                ?.toIntOrNull()
                ?: 0
            if (rotation == 90 || rotation == 270) {
                val tmp = width
                width = height
                height = tmp
            }
            val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
                ?.toLongOrNull()
                ?: 0L
            val fps = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE)
                ?.toDoubleOrNull()
                ?: 30.0
            val thumbAtMs = trimStartMs.coerceAtLeast(0L)
            writeThumbAt(retriever, library.thumbFile(clipId), thumbAtMs)
            // Determine effective play window from trim params or auto-cap
            val effectiveStart = trimStartMs.coerceAtLeast(0L).coerceAtMost(durationMs)
            val effectiveEnd: Long? = when {
                trimEndMs != null -> trimEndMs.coerceAtMost(durationMs)
                durationMs > Library.MAX_MS -> effectiveStart + Library.MAX_MS
                else -> null
            }
            val meta = ClipMeta(
                clipId = clipId,
                createdAt = Library.createdAtIso(),
                displayName = Library.displayNameNow(),
                durationMs = durationMs.toInt(),
                width = width.coerceAtLeast(1),
                height = height.coerceAtLeast(1),
                fps = fps,
                kind = ClipKind.VIDEO,
                status = ClipStatus.PENDING,
                playStartMs = effectiveStart.toInt(),
                playEndMs = effectiveEnd?.toInt(),
            )
            library.saveMeta(meta)
            return meta
        } finally {
            retriever.release()
        }
    }

    private fun finishImage(clipId: String, dest: File): ClipMeta {
        val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(dest.absolutePath, opts)
        val bmp = BitmapFactory.decodeFile(dest.absolutePath)
        if (bmp != null) {
            writeThumbBitmap(bmp, library.thumbFile(clipId))
            bmp.recycle()
        }
        val meta = ClipMeta(
            clipId = clipId,
            createdAt = Library.createdAtIso(),
            displayName = Library.displayNameNow(),
            durationMs = 0,
            width = opts.outWidth.coerceAtLeast(1),
            height = opts.outHeight.coerceAtLeast(1),
            fps = 1.0,
            kind = ClipKind.IMAGE,
            status = ClipStatus.PENDING,
        )
        library.saveMeta(meta)
        return meta
    }

    private fun copyUri(uri: Uri, dest: File) {
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(dest).use { output -> input.copyTo(output) }
        } ?: throw IllegalStateException("Could not read video.")
    }

    private fun writeThumbAt(retriever: MediaMetadataRetriever, dest: File, atMs: Long) {
        val frame = retriever.getFrameAtTime(atMs * 1000L, MediaMetadataRetriever.OPTION_CLOSEST)
            ?: retriever.getFrameAtTime(0L, MediaMetadataRetriever.OPTION_CLOSEST)
            ?: return
        writeThumbBitmap(frame, dest)
        frame.recycle()
    }

    private fun writeThumbBitmap(src: Bitmap, dest: File) {
        val w = 256
        val h = 144
        val out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(out)
        canvas.drawColor(Color.BLACK)
        val scale = maxOf(w.toFloat() / src.width, h.toFloat() / src.height)
        val dw = src.width * scale
        val dh = src.height * scale
        val dx = (w - dw) / 2f
        val dy = (h - dh) / 2f
        val matrix = Matrix().apply {
            postScale(scale, scale)
            postTranslate(dx, dy)
        }
        canvas.drawBitmap(src, matrix, Paint(Paint.FILTER_BITMAP_FLAG))
        FileOutputStream(dest).use { out.compress(Bitmap.CompressFormat.JPEG, 80, it) }
        out.recycle()
    }

    companion object {
        private val IMAGE_EXT = listOf(".jpg", ".jpeg", ".png", ".webp", ".bmp")
    }
}
