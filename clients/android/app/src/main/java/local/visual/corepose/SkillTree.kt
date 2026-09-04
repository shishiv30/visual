package local.visual.corepose

/** Port of core/sports/tree.py build_tree + tree_path_projection. */
object SkillTree {
    private val BRANCH_BY_CATEGORY = mapOf(
        "alpine_piste" to "piste",
        "alpine_moguls" to "moguls",
        "alpine_offpiste" to "offpiste",
        "park" to "park",
        "alpine_race" to "race",
        "alpine_switch" to "park",
    )

    fun buildTree(
        curriculum: Curriculum,
        currentId: String,
        history: StageHistory? = null,
        ageBand: String? = null,
        lang: String = "en",
        nameFor: (String) -> String = { it },
    ): List<TreeNodeV3> {
        val hist = history ?: StageHistory()
        val layer = depths(curriculum)
        val parents = parentsMap(curriculum)
        val passed = hist.passedLevels()
        val inferredIds = prerequisiteAncestors(currentId, curriculum) - passed
        val currentName = nameFor(currentId)
        val order = ArrayList<String>()
        order.addAll(curriculum.levelIds)
        for (lid in curriculum.catalogLevelIds) {
            if (lid in curriculum.levels && lid !in order) order.add(lid)
        }
        for (lid in curriculum.levels.keys) {
            if (lid !in order) order.add(lid)
        }
        val nodes = ArrayList<TreeNodeV3>()
        for (lid in order) {
            val level = curriculum.levels[lid] ?: continue
            var lockedReason = ""
            var inferredReason = ""
            val state: NodeState
            when {
                ageExcluded(level, ageBand) -> {
                    state = NodeState.NOT_APPLICABLE
                    lockedReason = I18n.t(
                        "Carving needs body mass to bend the ski; not applicable below age 13.",
                        lang = lang,
                    )
                }
                lid == currentId -> state = NodeState.CURRENT
                lid in passed -> state = NodeState.COMPLETED
                lid in inferredIds -> {
                    state = NodeState.INFERRED
                    inferredReason = I18n.t(
                        "Predicted passed based on {current} result",
                        mapOf("current" to currentName),
                        lang = lang,
                    )
                }
                else -> {
                    lockedReason = lockedReason(level, curriculum, hist, lang, nameFor)
                    state = if (lockedReason.isNotEmpty()) NodeState.LOCKED else NodeState.AVAILABLE
                }
            }
            nodes.add(
                TreeNodeV3(
                    id = lid,
                    name = nameFor(lid),
                    kbStage = level.kbStage,
                    tier = level.tier ?: "full",
                    branch = BRANCH_BY_CATEGORY[level.categoryId] ?: "piste",
                    state = state,
                    scoreBest = hist.scoreBest(lid),
                    gatesPassed = hist.gatesLabel(lid),
                    lockedReason = lockedReason,
                    inferredReason = inferredReason,
                    depth = layer[lid] ?: 0,
                    parents = parents[lid].orEmpty(),
                    children = level.nextLevels,
                ),
            )
        }
        return nodes
    }

    fun treePathProjection(
        curriculum: Curriculum,
        stageId: String,
        nameFor: (String) -> String = { it },
    ): List<TreeNode> {
        val parent = HashMap<String, String>()
        for ((lid, spec) in curriculum.levels) {
            for (nid in spec.nextLevels) {
                parent.putIfAbsent(nid, lid)
            }
        }
        val chain = ArrayList<String>()
        var cursor = stageId
        val seen = HashSet<String>()
        while (cursor.isNotEmpty() && cursor !in seen) {
            seen.add(cursor)
            chain.add(cursor)
            cursor = parent[cursor].orEmpty()
        }
        chain.reverse()
        val nodes = ArrayList<TreeNode>()
        for (lid in chain) {
            if (curriculum.levels[lid] == null) continue
            nodes.add(TreeNode(id = lid, name = nameFor(lid), current = lid == stageId))
        }
        cursor = stageId
        val seenFuture = nodes.map { it.id }.toMutableSet()
        while (true) {
            val spec = curriculum.levels[cursor] ?: break
            if (spec.nextLevels.isEmpty()) break
            val nxt = spec.nextLevels[0]
            if (nxt in seenFuture) break
            if (curriculum.levels[nxt] == null) break
            nodes.add(TreeNode(id = nxt, name = nameFor(nxt), current = false))
            seenFuture.add(nxt)
            cursor = nxt
        }
        return nodes
    }

    private fun parentsMap(curriculum: Curriculum): Map<String, List<String>> {
        val out = curriculum.levels.keys.associateWith { ArrayList<String>() }.toMutableMap()
        for ((lid, spec) in curriculum.levels) {
            for (nid in spec.nextLevels) {
                val list = out[nid] ?: continue
                if (lid !in list) list.add(lid)
            }
        }
        return out
    }

    private fun depths(curriculum: Curriculum): Map<String, Int> {
        val parents = parentsMap(curriculum)
        val depth = curriculum.levels.keys.associateWith { 0 }.toMutableMap()
        repeat(depth.size + 1) {
            var changed = false
            for ((lid, ups) in parents) {
                if (ups.isEmpty()) continue
                val best = ups.mapNotNull { depth[it]?.plus(1) }.maxOrNull() ?: continue
                if (best > (depth[lid] ?: 0)) {
                    depth[lid] = best
                    changed = true
                }
            }
            if (!changed) return@repeat
        }
        return depth
    }

    private fun prerequisiteAncestors(currentId: String, curriculum: Curriculum): Set<String> {
        val seen = HashSet<String>()
        val queue = ArrayList(curriculum.levels[currentId]?.prerequisites?.levels.orEmpty())
        while (queue.isNotEmpty()) {
            val lid = queue.removeAt(queue.lastIndex)
            if (lid in seen) continue
            seen.add(lid)
            curriculum.levels[lid]?.prerequisites?.levels?.let { queue.addAll(it) }
        }
        return seen
    }

    private fun ageExcluded(level: LevelSpec, ageBand: String?): Boolean {
        if (ageBand.isNullOrBlank()) return false
        return level.profileNotes.any { it.id == ageBand && it.status == "not_applicable" }
    }

    private fun lockedReason(
        level: LevelSpec,
        curriculum: Curriculum,
        history: StageHistory,
        lang: String,
        nameFor: (String) -> String,
    ): String {
        val passed = history.passedLevels()
        for (lid in level.prerequisites.levels) {
            if (lid !in passed) {
                return I18n.t(
                    "Needs {name} first",
                    mapOf("name" to nameFor(lid)),
                    lang = lang,
                )
            }
        }
        for (cid in level.prerequisites.checkpoints) {
            if (cid in history.checkpointsPassed) continue
            val spec = curriculum.checkpoints[cid]
            val label = if (spec != null) CurriculumLoader.locText(spec.name, lang) else cid
            return I18n.t(
                "Needs the {name} checkpoint",
                mapOf("name" to label),
                lang = lang,
            )
        }
        return ""
    }
}
