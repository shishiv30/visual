package local.visual.corepose

data class LevelHistory(
    val levelId: String,
    val passed: Boolean = false,
    val scoreBest: Double? = null,
    val gatesPassed: Int = 0,
    val gatesTotal: Int = 0,
    val clips: Int = 0,
    val clipIdBest: String = "",
)

data class StageHistory(
    val levels: Map<String, LevelHistory> = emptyMap(),
    val checkpointsPassed: Set<String> = emptySet(),
) {
    val isEmpty: Boolean get() = levels.isEmpty()

    fun passedLevels(): Set<String> = levels.filterValues { it.passed }.keys

    fun scoreBest(levelId: String): Double? = levels[levelId]?.scoreBest

    fun gatesLabel(levelId: String): String {
        val item = levels[levelId] ?: return ""
        if (item.gatesTotal <= 0) return ""
        return "${item.gatesPassed}/${item.gatesTotal}"
    }

    companion object {
        fun fromReports(reports: Iterable<StageReport>, passScore: Double = 60.0): StageHistory {
            val byLevel = LinkedHashMap<String, LevelHistory>()
            val cps = HashSet<String>()
            for (report in reports) {
                val lid = report.stageId
                if (lid.isBlank() || lid == Assess.UNKNOWN) continue
                val gates = report.metrics.filter { it.isGate }
                val gatesPassed = gates.count {
                    it.rubric == Rubric.PASS || it.rubric == Rubric.STRONG
                }
                val gatesTotal = gates.size
                val passed = report.readyForNextStage || report.score0100 >= passScore
                val prev = byLevel[lid]
                val bestScore = listOfNotNull(prev?.scoreBest, report.score0100).maxOrNull()
                val keepPrevClip = prev != null && (prev.scoreBest ?: -1.0) >= report.score0100
                byLevel[lid] = LevelHistory(
                    levelId = lid,
                    passed = (prev?.passed == true) || passed,
                    scoreBest = bestScore,
                    gatesPassed = maxOf(prev?.gatesPassed ?: 0, gatesPassed),
                    gatesTotal = maxOf(prev?.gatesTotal ?: 0, gatesTotal),
                    clips = (prev?.clips ?: 0) + 1,
                    clipIdBest = if (keepPrevClip) prev!!.clipIdBest else report.clipId,
                )
                for (kp in report.keypoints) {
                    if (kp.status == KeypointStatus.PASS) cps.add(kp.id)
                }
            }
            return StageHistory(levels = byLevel, checkpointsPassed = cps)
        }
    }
}
