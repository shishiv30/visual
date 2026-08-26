package local.visual.corepose

object CoreMap {
    init {
        System.loadLibrary("core_map")
    }

    external fun fromBlaze33(
        xyzVis: FloatArray?,
        numPeople: Int,
        width: Int,
        height: Int,
        latencyMs: Float,
        device: String,
    ): String
}
