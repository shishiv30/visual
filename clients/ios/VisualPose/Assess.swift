import Foundation

enum Assess {
    static let unknown = "unknown"
    static let sysCategory = "unknown"
    static let confGate = 0.35
    static let qualityGate = 0.2

    static func classify(_ pack: FeaturePack) -> (String, String, Double) {
        if pack.n < 4 || pack.quality < qualityGate {
            return (sysCategory, unknown, 0)
        }
        if pack.kneeFlexAmp > 50.0 && pack.kneeFlexFreq > 0.8 {
            return mogulStage(pack)
        }
        if pack.inwardLean >= 0.18 && pack.stanceWidth < 1.2 {
            let stage: String
            if pack.turnFreq >= 0.45 {
                stage = "carve_short"
            } else if pack.turnFreq >= 0.32 {
                stage = "carve_medium"
            } else {
                stage = "carve_long"
            }
            return ("alpine_piste", stage, 0.5)
        }
        if pack.kneeFlexAmp > 35.0 && pack.kneeFlexFreq > 0.6 && pack.stanceWidth >= 1.2 {
            return mogulStage(pack)
        }
        if pack.stanceWidth >= 1.2 && pack.kneeFlexFreq <= 0.6 {
            let conf = min(1.0, 0.4 + (pack.stanceWidth - 1.2))
            let stage = pack.turnFreq < 0.18 ? "pizza_glide" : "pizza"
            return ("alpine_piste", stage, conf)
        }
        if pack.stanceWidthStd >= 0.22 && pack.stanceWidth >= 0.95 && pack.inwardLean < 0.18 {
            return ("alpine_piste", "wedge_christie", 0.55)
        }
        if pack.stanceWidth < 1.1 && pack.turnFreq >= 0.45 {
            return ("alpine_piste", "skid_short", 0.5)
        }
        if pack.stanceWidth < 1.1 {
            return ("alpine_piste", "parallel", 0.55)
        }
        return (sysCategory, unknown, 0.25)
    }

    static func assessClip(
        clipId: String,
        frames: [AssessFrame],
        fps: Double,
        curriculum: Curriculum,
        lang: String
    ) -> StageReport {
        let pack = SportsSignals.extractFeatures(frames, fpsIn: fps)
        let (categoryId, stageId, confidence) = classify(pack)
        let stage = curriculum.levels[stageId]
        if stage == nil || !(stage?.inScope ?? false) || confidence < confGate || stageId == unknown {
            return unknownReport(clipId, curriculum, lang, pack)
        }
        let stageSpec = stage!
        var results: [KeypointResult] = []
        var heuristic = stageSpec.heuristicNotFisCarve
        for cid in stageSpec.checkpoints {
            guard let spec = curriculum.checkpoints[cid] else { continue }
            results.append(evalCheckpoint(spec, pack, curriculum, lang))
            heuristic = heuristic || spec.heuristicNotFisCarve
        }
        let score = stageScore(results, confidence, curriculum)
        let required = requiredOk(results, stageSpec, curriculum)
        let ready = confidence >= confGate && score >= curriculum.passScore && required
        var nextIds: [String] = []
        var nextNames: [String] = []
        var nextPlans: [LevelPlan] = []
        if ready {
            for nid in stageSpec.nextLevels {
                guard let nxt = curriculum.levels[nid], nxt.inScope else { continue }
                nextIds.append(nid)
                nextNames.append(text(nxt.name, lang))
                nextPlans.append(levelPlan(nxt, curriculum, lang))
            }
        }
        let weakest = ready ? "" : weakestId(results)
        let catName: String
        if let catLoc = curriculum.categories[stageSpec.categoryId] {
            catName = text(catLoc, lang)
        } else {
            catName = categoryId
        }
        let terrain = curriculum.terrains[stageSpec.terrain]
        let sysDrill = curriculum.drills[curriculum.sysDrill]
        return StageReport(
            clipId: clipId,
            categoryId: stageSpec.categoryId,
            stageId: stageId,
            categoryName: catName,
            stageName: text(stageSpec.name, lang),
            confidence: confidence,
            readyForNextStage: ready,
            disclaimer: text(curriculum.disclaimer, lang),
            stageFocus: text(stageSpec.desc, lang),
            score0100: score,
            terrainId: stageSpec.terrain,
            terrainName: terrain.map { text($0.name, lang) } ?? "",
            terrainDesc: terrain.map { text($0.desc, lang) } ?? "",
            weakestCheckpointId: weakest,
            nextLevelIds: nextIds,
            nextLevelNames: nextNames,
            nextPlans: nextPlans,
            sessionPlan: stageSpec.sessionDrills.compactMap { did in
                curriculum.drills[did].map { drillPayload($0, curriculum, lang) }
            },
            treePath: treePath(curriculum, stageId, lang),
            filmSteps: sysDrill?.training.map { text($0, lang) } ?? [],
            keypoints: results,
            scoreSeries: scoreSeries(stageSpec, pack, curriculum),
            heuristicNotFisCarve: heuristic,
            posture: Posture.scores(pack, results: results)
        )
    }

    private static func mogulStage(_ pack: FeaturePack) -> (String, String, Double) {
        let stage = pack.fallLine < 0.85 && pack.kneeFlexFreq > 1.1 ? "mogul_fallline" : "mogul_absorb"
        return ("alpine_moguls", stage, min(1.0, 0.45 + pack.kneeFlexFreq / 4.0))
    }

    private static func text(_ item: LocText, _ lang: String) -> String {
        CurriculumLoader.locText(item, lang: lang)
    }

    private static func requiredOk(
        _ results: [KeypointResult],
        _ stage: LevelSpec,
        _ cur: Curriculum
    ) -> Bool {
        var byId: [String: KeypointResult] = [:]
        for item in results { byId[item.id] = item }
        var scored = 0
        for cid in stage.checkpoints {
            guard let spec = cur.checkpoints[cid], spec.required else { continue }
            guard let item = byId[cid], let score = item.score else { continue }
            scored += 1
            if score < cur.checkpointPass { return false }
        }
        return scored > 0
    }

    private static func weakestId(_ results: [KeypointResult]) -> String {
        let known = results.filter { $0.score != nil }
        if known.isEmpty { return results.first?.id ?? "" }
        return known.min(by: { ($0.score ?? 0) < ($1.score ?? 0) })?.id ?? ""
    }

    private static func stageScore(
        _ results: [KeypointResult],
        _ confidence: Double,
        _ cur: Curriculum
    ) -> Double {
        let pts = results.compactMap { item -> Double? in
            guard let spec = cur.checkpoints[item.id], let score = item.score, spec.required else {
                return nil
            }
            return score
        }
        if pts.isEmpty { return 0 }
        let raw = pts.reduce(0, +) / Double(pts.count)
        return Json.roundEven(raw * (0.8 + 0.2 * confidence) * 10.0) / 10.0
    }

    private static func continuousScore(_ value: Double, _ spec: Threshold) -> Double {
        switch spec.op {
        case "gte":
            let band = max(abs(spec.value) * 0.4, 0.08)
            return piecewise(value, spec.value - band, spec.value, spec.value + band)
        case "lte":
            let band = max(abs(spec.value) * 0.4, 0.08)
            let mirrored = spec.value - (value - spec.value)
            return piecewise(mirrored, spec.value - band, spec.value, spec.value + band)
        case "between":
            let hi = spec.hi ?? spec.value
            let lo = spec.value
            if value >= lo && value <= hi {
                let mid = 0.5 * (lo + hi)
                let span = max((hi - lo) / 2.0, 1e-6)
                let dist = abs(value - mid) / span
                return Json.roundEven((100.0 - 40.0 * dist) * 10.0) / 10.0
            }
            let outside = value < lo ? lo - value : value - hi
            let width = max(hi - lo, 0.08)
            return Json.roundEven(max(0.0, 60.0 * (1.0 - outside / width)) * 10.0) / 10.0
        default:
            return 0
        }
    }

    private static func piecewise(_ value: Double, _ lo: Double, _ mid: Double, _ hi: Double) -> Double {
        if value <= lo { return 0 }
        if value >= hi { return 100 }
        if value < mid {
            let t = (value - lo) / max(mid - lo, 1e-6)
            return Json.roundEven(60.0 * t * 10.0) / 10.0
        }
        let t = (value - mid) / max(hi - mid, 1e-6)
        return Json.roundEven((60.0 + 40.0 * t) * 10.0) / 10.0
    }

    private static func evalCheckpoint(
        _ spec: CheckpointSpec,
        _ pack: FeaturePack,
        _ cur: Curriculum,
        _ lang: String
    ) -> KeypointResult {
        let value = SportsSignals.signalValue(pack, name: spec.signal)
        let score: Double?
        let status: KeypointStatus
        if let value {
            score = continuousScore(value, spec.threshold)
            status = score! >= cur.checkpointPass ? .pass : .fail
        } else {
            status = .unknown
            score = nil
        }
        let drills: [DrillPayload]
        if status == .fail {
            drills = spec.drills.compactMap { did in
                cur.drills[did].map { drillPayload($0, cur, lang) }
            }
        } else {
            drills = []
        }
        let evidence = status != .unknown ? evidenceMs(spec, pack, passing: status == .pass) : nil
        let desc = text(spec.desc, lang)
        return KeypointResult(
            id: spec.id,
            name: text(spec.name, lang),
            status: status,
            score: score,
            value: value,
            evidenceMs: evidence,
            good: desc,
            bad: desc,
            drills: drills
        )
    }

    private static func evidenceMs(_ spec: CheckpointSpec, _ pack: FeaturePack, passing: Bool) -> Double? {
        if pack.series.isEmpty { return nil }
        var instant: [(Double, Double)] = []
        for sample in pack.series {
            guard let value = SportsSignals.sampleSignal(sample, name: spec.signal) else { continue }
            instant.append((sample.tMs, continuousScore(value, spec.threshold)))
        }
        if !instant.isEmpty {
            return passing
                ? instant.max(by: { $0.1 < $1.1 })?.0
                : instant.min(by: { $0.1 < $1.1 })?.0
        }
        if spec.signal == "turn_freq" || spec.signal == "fall_line" {
            let scored = pack.series.compactMap { s -> (Double, Double)? in
                guard let hx = s.hipX else { return nil }
                return (s.tMs, abs(hx - pack.hipXMean))
            }
            if scored.isEmpty { return pack.series.first?.tMs }
            return scored.max(by: { $0.1 < $1.1 })?.0
        }
        if spec.signal == "knee_flex_freq" || spec.signal == "knee_flex_amp" {
            let scored = pack.series.compactMap { s -> (Double, Double)? in
                guard let flex = s.kneeFlex else { return nil }
                return (s.tMs, flex)
            }
            if scored.isEmpty { return pack.series.first?.tMs }
            return scored.max(by: { $0.1 < $1.1 })?.0
        }
        if spec.signal == "stance_width_std" {
            let scored = pack.series.compactMap { s -> (Double, Double)? in
                guard let w = s.stanceWidth else { return nil }
                return (s.tMs, abs(w - pack.stanceWidth))
            }
            if scored.isEmpty { return pack.series.first?.tMs }
            return scored.max(by: { $0.1 < $1.1 })?.0
        }
        return pack.series.first?.tMs
    }

    private static func scoreSeries(
        _ stage: LevelSpec,
        _ pack: FeaturePack,
        _ cur: Curriculum
    ) -> [FrameScorePoint] {
        let specs = stage.checkpoints.compactMap { cid -> CheckpointSpec? in
            guard let spec = cur.checkpoints[cid], spec.required else { return nil }
            return spec
        }
        var points: [FrameScorePoint] = []
        for sample in pack.series {
            var scores: [Double] = []
            for spec in specs {
                var value = SportsSignals.sampleSignal(sample, name: spec.signal)
                if value == nil {
                    value = SportsSignals.signalValue(pack, name: spec.signal)
                }
                guard let value else { continue }
                scores.append(continuousScore(value, spec.threshold))
            }
            if scores.isEmpty { continue }
            points.append(
                FrameScorePoint(
                    tMs: sample.tMs,
                    score: Json.roundEven(scores.reduce(0, +) / Double(scores.count) * 10.0) / 10.0
                )
            )
        }
        return points
    }

    private static func venuePayload(_ cur: Curriculum, _ venueId: String, _ lang: String) -> VenuePayload? {
        guard let venue = cur.venues[venueId] else { return nil }
        return VenuePayload(
            id: venue.id,
            name: text(venue.name, lang),
            desc: text(venue.desc, lang),
            tips: text(venue.tips, lang),
            terrain: venue.terrain
        )
    }

    private static func drillPayload(_ drill: DrillSpec, _ cur: Curriculum, _ lang: String) -> DrillPayload {
        let venues = drill.venueIds.compactMap { venuePayload(cur, $0, lang) }
        let training = drill.training.map { text($0, lang) }
        return DrillPayload(
            id: drill.id,
            title: text(drill.name, lang),
            name: text(drill.name, lang),
            desc: text(drill.desc, lang),
            steps: training,
            training: training,
            venues: venues
        )
    }

    private static func levelPlan(_ stage: LevelSpec, _ cur: Curriculum, _ lang: String) -> LevelPlan {
        let drills = stage.sessionDrills.compactMap { did in
            cur.drills[did].map { drillPayload($0, cur, lang) }
        }
        let venues = stage.venueIds.compactMap { venuePayload(cur, $0, lang) }
        return LevelPlan(
            levelId: stage.id,
            levelName: text(stage.name, lang),
            drills: drills,
            venues: venues
        )
    }

    private static func treePath(_ cur: Curriculum, _ stageId: String, _ lang: String) -> [TreeNode] {
        var parent: [String: String] = [:]
        for (lid, spec) in cur.levels {
            for nid in spec.nextLevels {
                if parent[nid] == nil {
                    parent[nid] = lid
                }
            }
        }
        var chain: [String] = []
        var cursor = stageId
        var seen: Set<String> = []
        while !cursor.isEmpty && !seen.contains(cursor) {
            seen.insert(cursor)
            chain.append(cursor)
            cursor = parent[cursor] ?? ""
        }
        chain.reverse()
        var nodes: [TreeNode] = []
        for lid in chain {
            guard let spec = cur.levels[lid] else { continue }
            nodes.append(TreeNode(id: lid, name: text(spec.name, lang), current: lid == stageId))
        }
        cursor = stageId
        var seenFuture = Set(nodes.map(\.id))
        while true {
            guard let spec = cur.levels[cursor], !spec.nextLevels.isEmpty else { break }
            let nxt = spec.nextLevels[0]
            if seenFuture.contains(nxt) { break }
            guard let nextSpec = cur.levels[nxt] else { break }
            nodes.append(TreeNode(id: nxt, name: text(nextSpec.name, lang), current: false))
            seenFuture.insert(nxt)
            cursor = nxt
        }
        return nodes
    }

    private static func unknownReport(
        _ clipId: String,
        _ cur: Curriculum,
        _ lang: String,
        _ pack: FeaturePack
    ) -> StageReport {
        let drill = cur.drills[cur.sysDrill]
        let payload = drill.map { drillPayload($0, cur, lang) } ?? DrillPayload()
        return StageReport(
            clipId: clipId,
            categoryId: sysCategory,
            stageId: unknown,
            categoryName: I18n.t("Unknown", lang: lang),
            stageName: I18n.t("Re-film", lang: lang),
            confidence: min(pack.quality, 0.34),
            readyForNextStage: false,
            disclaimer: text(cur.disclaimer, lang),
            weakestCheckpointId: "KP-SYS-01",
            filmSteps: drill?.training.map { text($0, lang) } ?? [],
            keypoints: [
                KeypointResult(
                    id: "KP-SYS-01",
                    name: drill.map { text($0.name, lang) } ?? "",
                    status: .unknown,
                    good: drill.map { text($0.name, lang) } ?? "",
                    bad: I18n.t(
                        "Stage cannot be judged when the shot is unstable, occluded, or out of curriculum scope.",
                        lang: lang
                    ),
                    drills: [payload]
                ),
            ],
            posture: Posture.scores(pack, results: [])
        )
    }
}
