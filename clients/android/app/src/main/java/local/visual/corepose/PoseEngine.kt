package local.visual.corepose

import android.content.Context
import android.os.Build
import android.util.Log
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import java.util.concurrent.atomic.AtomicReference

class PoseEngine(private val context: Context) {
    val device = AtomicReference("cpu")

    fun create(mode: RunningMode, numPoses: Int = 2): PoseLandmarker {
        val preferCpu = isEmulator()
        val first = if (preferCpu) Delegate.CPU else Delegate.GPU
        return try {
            build(first, mode, numPoses).also {
                device.set(if (first == Delegate.GPU) "gpu" else "cpu")
            }
        } catch (exc: Exception) {
            Log.w(TAG, "pose landmarker $first failed, trying fallback", exc)
            val second = if (first == Delegate.GPU) Delegate.CPU else Delegate.GPU
            build(second, mode, numPoses).also {
                device.set(if (second == Delegate.GPU) "gpu" else "cpu")
            }
        }
    }

    fun createPair(): PoseLandmarkers {
        return PoseLandmarkers(
            video = create(RunningMode.VIDEO, numPoses = 2),
            crop = create(RunningMode.IMAGE, numPoses = 1),
        )
    }

    private fun build(delegate: Delegate, mode: RunningMode, numPoses: Int): PoseLandmarker {
        val builder = PoseLandmarker.PoseLandmarkerOptions.builder()
            .setBaseOptions(
                BaseOptions.builder()
                    .setModelAssetPath("pose_landmarker_full.task")
                    .setDelegate(delegate)
                    .build(),
            )
            .setRunningMode(mode)
            .setNumPoses(numPoses)
            .setMinPoseDetectionConfidence(0.5f)
            .setMinPosePresenceConfidence(0.5f)
            .setMinTrackingConfidence(0.5f)
        return PoseLandmarker.createFromOptions(context, builder.build())
    }

    companion object {
        private const val TAG = "CorePose"

        fun isEmulator(): Boolean {
            val fingerprint = Build.FINGERPRINT
            return fingerprint.startsWith("generic") ||
                fingerprint.contains("emulator") ||
                Build.MODEL.contains("sdk_gphone") ||
                Build.PRODUCT.contains("sdk") ||
                Build.HARDWARE.contains("ranchu") ||
                Build.HARDWARE.contains("goldfish")
        }
    }
}
