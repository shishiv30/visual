package local.visual.corepose

import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper

/**
 * Off-main-thread, latest-wins video frame loader for scrubbing.
 *
 * `MediaMetadataRetriever.getFrameAtTime(OPTION_CLOSEST)` decodes from the previous sync frame
 * up to the target and routinely costs 50–300 ms on phone/action-cam footage. Calling it on the
 * UI thread for every ACTION_MOVE starves touch delivery (handles lag, then jump), which made
 * the trim strip nearly impossible to place precisely.
 *
 * This class:
 *  - decodes on its own thread and posts results to the main thread;
 *  - coalesces requests — only the newest pending request is decoded, stale ones are dropped;
 *  - while scrubbing (`precise = false`) decodes the nearest sync frame (fast), then refines to
 *    the exact frame once the finger rests for [SETTLE_MS];
 *  - for `precise = true` (tap, release) decodes the exact frame straight away.
 */
class FrameScrubber(
    private val maxW: Int,
    private val maxH: Int,
    private val onFrame: (tMs: Int, bmp: Bitmap) -> Unit,
) {
    private data class Req(val tMs: Int, val precise: Boolean, val seq: Long, val gen: Int)

    private val thread = HandlerThread("frame-scrubber").apply { start() }
    private val bg = Handler(thread.looper)
    private val main = Handler(Looper.getMainLooper())
    private val lock = Any()

    // Guarded by [lock].
    private var pending: Req? = null
    private var drainQueued = false
    private var seq = 0L
    private var gen = 0

    // Background-thread only.
    private var retriever: MediaMetadataRetriever? = null

    // Main-thread only.
    private var deliveredSeq = -1L
    private var lastTMs = -1
    private var lastPrecise = false

    private val settle = Runnable { request(lastTMs, precise = true) }

    fun bind(path: String) {
        val g = synchronized(lock) {
            gen += 1
            pending = null
            gen
        }
        main.removeCallbacks(settle)
        lastTMs = -1
        bg.post {
            retriever?.release()
            retriever = null
            if (g != currentGen()) return@post
            val next = MediaMetadataRetriever()
            try {
                next.setDataSource(path)
                retriever = next
            } catch (_: Exception) {
                next.release()
            }
        }
    }

    /** Request the frame at [tMs]. Safe to call on every touch move. Main thread only. */
    fun request(tMs: Int, precise: Boolean) {
        if (tMs < 0) return
        if (tMs == lastTMs && (lastPrecise || !precise)) {
            return
        }
        main.removeCallbacks(settle)
        lastTMs = tMs
        lastPrecise = precise
        synchronized(lock) {
            seq += 1
            pending = Req(tMs, precise, seq, gen)
            if (drainQueued) return
            drainQueued = true
        }
        bg.post(::drain)
        if (!precise) {
            main.postDelayed(settle, SETTLE_MS)
        }
    }

    fun release() {
        synchronized(lock) {
            gen += 1
            pending = null
        }
        main.removeCallbacks(settle)
        bg.post {
            retriever?.release()
            retriever = null
            thread.quitSafely()
        }
    }

    private fun currentGen(): Int = synchronized(lock) { gen }

    private fun drain() {
        val req = synchronized(lock) {
            val r = pending
            pending = null
            drainQueued = false
            r
        } ?: return
        val src = retriever ?: return
        if (req.gen != currentGen()) return
        val option = if (req.precise) {
            MediaMetadataRetriever.OPTION_CLOSEST
        } else {
            MediaMetadataRetriever.OPTION_CLOSEST_SYNC
        }
        val bmp = try {
            decode(src, req.tMs * 1000L, option)
        } catch (_: Exception) {
            null
        } ?: return
        main.post {
            // Drop results that a newer request has already superseded on screen, or that belong
            // to a previous video.
            if (req.gen != currentGen() || req.seq < deliveredSeq) {
                bmp.recycle()
                return@post
            }
            deliveredSeq = req.seq
            onFrame(req.tMs, bmp)
        }
    }

    private fun decode(src: MediaMetadataRetriever, us: Long, option: Int): Bitmap? {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1 && maxW > 0 && maxH > 0) {
            return src.getScaledFrameAtTime(us, option, maxW, maxH)
        }
        return src.getFrameAtTime(us, option)
    }

    companion object {
        const val SETTLE_MS = 120L
    }
}
