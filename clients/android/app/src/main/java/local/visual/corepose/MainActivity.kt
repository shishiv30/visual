package local.visual.corepose

import android.os.Bundle
import android.util.Log
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private val executor = Executors.newSingleThreadExecutor()
    private var landmarker: PoseLandmarker? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val preview = PreviewView(this)
        val label = TextView(this)
        setContentView(preview)
        // Copy pose_landmarker_full.task into assets/ before running.
        val opts = PoseLandmarker.PoseLandmarkerOptions.builder()
            .setBaseOptions(
                BaseOptions.builder().setModelAssetPath("pose_landmarker_full.task").build(),
            )
            .setRunningMode(RunningMode.LIVE_STREAM)
            .setResultListener { result, _ ->
                val poses = result.landmarks()
                val n = poses.size
                val w = preview.width.coerceAtLeast(1).toFloat()
                val h = preview.height.coerceAtLeast(1).toFloat()
                val flat = FloatArray(n * 33 * 4)
                var o = 0
                for (person in poses) {
                    for (i in 0 until 33) {
                        val lm = person[i]
                        flat[o++] = lm.x() * w
                        flat[o++] = lm.y() * h
                        flat[o++] = lm.z() * w
                        flat[o++] = lm.visibility().orElse(1f)
                    }
                }
                val json = CoreMap.fromBlaze33(
                    flat,
                    n,
                    preview.width.coerceAtLeast(1),
                    preview.height.coerceAtLeast(1),
                    0f,
                    "gpu",
                )
                Log.i("CorePose", json.take(240))
            }
            .build()
        landmarker = PoseLandmarker.createFromOptions(this, opts)
        bindCamera(preview)
        label.text = "CorePose MediaPipe offline"
    }

    private fun bindCamera(previewView: PreviewView) {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            val provider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }
            val analysis = ImageAnalysis.Builder().build()
            analysis.setAnalyzer(executor) { image ->
                val bmp = image.toBitmap()
                landmarker?.detectAsync(BitmapImageBuilder(bmp).build(), image.imageInfo.timestamp)
                image.close()
            }
            provider.unbindAll()
            provider.bindToLifecycle(
                this,
                CameraSelector.DEFAULT_BACK_CAMERA,
                preview,
                analysis,
            )
        }, ContextCompat.getMainExecutor(this))
    }
}
