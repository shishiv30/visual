package local.visual.corepose

import android.app.Dialog
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import com.google.android.material.slider.RangeSlider
import kotlin.math.min

/**
 * Shown when an imported video exceeds MAX_MS (120 s). The user selects a trim window
 * (in_ms … out_ms) of at most MAX_MS. On confirm, [onConfirm] is called with the selected
 * start and end in milliseconds.
 */
class TrimDialogFragment : DialogFragment() {

    var onConfirm: ((startMs: Long, endMs: Long) -> Unit)? = null
    var onCancel: (() -> Unit)? = null

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val durationMs = arguments?.getLong(ARG_DURATION_MS) ?: Library.MAX_MS
        val maxMs = Library.MAX_MS

        val ctx = requireContext()

        val layout = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (20 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, 0)
        }

        val label = TextView(ctx).apply {
            setTextColor(0xFF9E9E9E.toInt())
            textSize = 13f
        }
        layout.addView(label)

        val slider = RangeSlider(ctx).apply {
            valueFrom = 0f
            valueTo = durationMs.toFloat()
            stepSize = 1000f
            setValues(0f, min(maxMs.toFloat(), durationMs.toFloat()))
        }
        layout.addView(slider)

        fun formatMs(ms: Float): String {
            val secs = (ms / 1000).toInt()
            return "%d:%02d".format(secs / 60, secs % 60)
        }

        fun updateLabel() {
            val lo = slider.values[0]
            val hi = slider.values[1]
            val windowS = ((hi - lo) / 1000).toInt()
            // Format: "0:15 – 2:15 (120s)" — no i18n key needed for a time range
            label.text = "${formatMs(lo)} – ${formatMs(hi)}  (${windowS}s)"
        }

        updateLabel()

        slider.addOnChangeListener { s, _, _ ->
            val lo = s.values[0]
            val hi = s.values[1]
            // Enforce max window length
            if (hi - lo > maxMs) {
                s.setValues(lo, lo + maxMs)
            }
            updateLabel()
        }

        return AlertDialog.Builder(ctx)
            .setTitle(I18n.t("Trim video (max 2 minutes)"))
            .setView(layout)
            .setPositiveButton(I18n.t("OK")) { _, _ ->
                val lo = slider.values[0].toLong()
                val hi = slider.values[1].toLong()
                onConfirm?.invoke(lo, hi)
            }
            .setNegativeButton(I18n.t("Cancel")) { _, _ ->
                onCancel?.invoke()
            }
            .create()
    }

    companion object {
        const val TAG = "TrimDialog"
        private const val ARG_DURATION_MS = "duration_ms"

        fun newInstance(durationMs: Long): TrimDialogFragment {
            return TrimDialogFragment().apply {
                arguments = Bundle().apply { putLong(ARG_DURATION_MS, durationMs) }
            }
        }
    }
}
