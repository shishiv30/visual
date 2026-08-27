import Foundation

enum KeypointStatus: String {
    case pass
    case fail
    case unknown
}

struct DrillPayload {
    var id: String = ""
    var title: String = ""
    var name: String = ""
    var desc: String = ""
    var steps: [String] = []
    var training: [String] = []
    var venues: [VenuePayload] = []
}

struct VenuePayload {
    var id: String = ""
    var name: String = ""
    var desc: String = ""
    var tips: String = ""
    var terrain: String = ""
}

struct LevelPlan {
    var levelId: String = ""
    var levelName: String = ""
    var drills: [DrillPayload] = []
    var venues: [VenuePayload] = []
}

struct KeypointResult {
    var id: String
    var name: String = ""
    var status: KeypointStatus
    var score: Double? = nil
    var value: Double? = nil
    var evidenceMs: Double? = nil
    var good: String
    var bad: String
    var drills: [DrillPayload] = []
}

struct TreeNode {
    var id: String
    var name: String
    var current: Bool = false
}

struct FrameScorePoint {
    var tMs: Double
    var score: Double
}

struct PostureScores {
    var stability: Double = 0
    var coordination: Double = 0
    var control: Double = 0
    var balance: Double = 0
}

struct StageReport {
    var schemaVersion: String = "2.1.0"
    var clipId: String
    var categoryId: String
    var stageId: String
    var categoryName: String
    var stageName: String
    var confidence: Double
    var readyForNextStage: Bool
    var disclaimer: String
    var stageFocus: String = ""
    var score0100: Double = 0
    var terrainId: String = ""
    var terrainName: String = ""
    var terrainDesc: String = ""
    var weakestCheckpointId: String = ""
    var nextLevelIds: [String] = []
    var nextLevelNames: [String] = []
    var nextPlans: [LevelPlan] = []
    var sessionPlan: [DrillPayload] = []
    var treePath: [TreeNode] = []
    var filmSteps: [String] = []
    var keypoints: [KeypointResult]
    var scoreSeries: [FrameScorePoint] = []
    var heuristicNotFisCarve: Bool = false
    var posture: PostureScores? = nil
}

enum StageReportJson {
    static func save(_ file: URL, _ report: StageReport) {
        Json.write(file, toJson(report), pretty: true)
    }

    static func load(_ file: URL) -> StageReport? {
        guard Json.isFile(file), let obj = Json.readObject(file) else { return nil }
        return fromJson(obj)
    }

    static func toJson(_ report: StageReport) -> [String: Any] {
        var obj: [String: Any] = [
            "schema_version": report.schemaVersion,
            "clip_id": report.clipId,
            "category_id": report.categoryId,
            "stage_id": report.stageId,
            "category_name": report.categoryName,
            "stage_name": report.stageName,
            "confidence": report.confidence,
            "ready_for_next_stage": report.readyForNextStage,
            "disclaimer": report.disclaimer,
            "stage_focus": report.stageFocus,
            "score_0_100": report.score0100,
            "terrain_id": report.terrainId,
            "terrain_name": report.terrainName,
            "terrain_desc": report.terrainDesc,
            "weakest_checkpoint_id": report.weakestCheckpointId,
            "heuristic_not_fis_carve": report.heuristicNotFisCarve,
            "next_level_ids": report.nextLevelIds,
            "next_level_names": report.nextLevelNames,
            "film_steps": report.filmSteps,
            "keypoints": report.keypoints.map { keypointJson($0) },
            "score_series": report.scoreSeries.map { ["t_ms": $0.tMs, "score": $0.score] },
            "tree_path": report.treePath.map { ["id": $0.id, "name": $0.name, "current": $0.current] },
            "next_plans": report.nextPlans.map { planJson($0) },
            "session_plan": report.sessionPlan.map { drillJson($0) },
        ]
        if let posture = report.posture {
            obj["posture"] = [
                "stability": posture.stability,
                "coordination": posture.coordination,
                "control": posture.control,
                "balance": posture.balance,
            ]
        } else {
            obj["posture"] = NSNull()
        }
        return obj
    }

    static func fromJson(_ obj: [String: Any]) -> StageReport {
        let kpsArr = Json.optArray(obj, "keypoints") ?? []
        let keypoints = kpsArr.compactMap { item -> KeypointResult? in
            guard let node = item as? [String: Any] else { return nil }
            return keypointFrom(node)
        }
        let seriesArr = Json.optArray(obj, "score_series") ?? []
        let series = seriesArr.compactMap { item -> FrameScorePoint? in
            guard let node = item as? [String: Any] else { return nil }
            return FrameScorePoint(tMs: Json.optDouble(node, "t_ms", 0), score: Json.optDouble(node, "score", 0))
        }
        let treeArr = Json.optArray(obj, "tree_path") ?? []
        let tree = treeArr.compactMap { item -> TreeNode? in
            guard let node = item as? [String: Any] else { return nil }
            return TreeNode(
                id: Json.optString(node, "id"),
                name: Json.optString(node, "name"),
                current: Json.optBool(node, "current")
            )
        }
        let postureObj = Json.optObject(obj, "posture")
        return StageReport(
            schemaVersion: Json.optString(obj, "schema_version", "2.1.0"),
            clipId: Json.optString(obj, "clip_id"),
            categoryId: Json.optString(obj, "category_id"),
            stageId: Json.optString(obj, "stage_id"),
            categoryName: Json.optString(obj, "category_name"),
            stageName: Json.optString(obj, "stage_name"),
            confidence: Json.optDouble(obj, "confidence", 0),
            readyForNextStage: Json.optBool(obj, "ready_for_next_stage"),
            disclaimer: Json.optString(obj, "disclaimer"),
            stageFocus: Json.optString(obj, "stage_focus"),
            score0100: Json.optDouble(obj, "score_0_100", 0),
            terrainId: Json.optString(obj, "terrain_id"),
            terrainName: Json.optString(obj, "terrain_name"),
            terrainDesc: Json.optString(obj, "terrain_desc"),
            weakestCheckpointId: Json.optString(obj, "weakest_checkpoint_id"),
            nextLevelIds: Json.strList(Json.optArray(obj, "next_level_ids")),
            nextLevelNames: Json.strList(Json.optArray(obj, "next_level_names")),
            nextPlans: planList(Json.optArray(obj, "next_plans")),
            sessionPlan: drillList(Json.optArray(obj, "session_plan")),
            treePath: tree,
            filmSteps: Json.strList(Json.optArray(obj, "film_steps")),
            keypoints: keypoints,
            scoreSeries: series,
            heuristicNotFisCarve: Json.optBool(obj, "heuristic_not_fis_carve"),
            posture: postureObj.map {
                PostureScores(
                    stability: Json.optDouble($0, "stability", 0),
                    coordination: Json.optDouble($0, "coordination", 0),
                    control: Json.optDouble($0, "control", 0),
                    balance: Json.optDouble($0, "balance", 0)
                )
            }
        )
    }

    private static func keypointJson(_ item: KeypointResult) -> [String: Any] {
        [
            "id": item.id,
            "name": item.name,
            "status": item.status.rawValue,
            "good": item.good,
            "bad": item.bad,
            "score": item.score ?? NSNull(),
            "value": item.value ?? NSNull(),
            "evidence_ms": item.evidenceMs ?? NSNull(),
            "drills": item.drills.map { drillJson($0) },
        ]
    }

    private static func keypointFrom(_ obj: [String: Any]) -> KeypointResult {
        let status: KeypointStatus
        switch Json.optString(obj, "status") {
        case "pass": status = .pass
        case "fail": status = .fail
        default: status = .unknown
        }
        return KeypointResult(
            id: Json.optString(obj, "id"),
            name: Json.optString(obj, "name"),
            status: status,
            score: Json.isNull(obj, "score") ? nil : Json.optDouble(obj, "score"),
            value: Json.isNull(obj, "value") ? nil : Json.optDouble(obj, "value"),
            evidenceMs: Json.isNull(obj, "evidence_ms") ? nil : Json.optDouble(obj, "evidence_ms"),
            good: Json.optString(obj, "good"),
            bad: Json.optString(obj, "bad"),
            drills: drillList(Json.optArray(obj, "drills"))
        )
    }

    private static func drillJson(_ drill: DrillPayload) -> [String: Any] {
        [
            "id": drill.id,
            "title": drill.title,
            "name": drill.name,
            "desc": drill.desc,
            "steps": drill.steps,
            "training": drill.training,
            "venues": drill.venues.map { venueJson($0) },
        ]
    }

    private static func planJson(_ plan: LevelPlan) -> [String: Any] {
        [
            "level_id": plan.levelId,
            "level_name": plan.levelName,
            "drills": plan.drills.map { drillJson($0) },
            "venues": plan.venues.map { venueJson($0) },
        ]
    }

    private static func venueJson(_ venue: VenuePayload) -> [String: Any] {
        [
            "id": venue.id,
            "name": venue.name,
            "desc": venue.desc,
            "tips": venue.tips,
            "terrain": venue.terrain,
        ]
    }

    private static func drillList(_ arr: [Any]?) -> [DrillPayload] {
        guard let arr else { return [] }
        return arr.compactMap { item in
            guard let node = item as? [String: Any] else { return nil }
            return DrillPayload(
                id: Json.optString(node, "id"),
                title: Json.optString(node, "title"),
                name: Json.optString(node, "name"),
                desc: Json.optString(node, "desc"),
                steps: Json.strList(Json.optArray(node, "steps")),
                training: Json.strList(Json.optArray(node, "training")),
                venues: venueList(Json.optArray(node, "venues"))
            )
        }
    }

    private static func planList(_ arr: [Any]?) -> [LevelPlan] {
        guard let arr else { return [] }
        return arr.compactMap { item in
            guard let node = item as? [String: Any] else { return nil }
            return LevelPlan(
                levelId: Json.optString(node, "level_id"),
                levelName: Json.optString(node, "level_name"),
                drills: drillList(Json.optArray(node, "drills")),
                venues: venueList(Json.optArray(node, "venues"))
            )
        }
    }

    private static func venueList(_ arr: [Any]?) -> [VenuePayload] {
        guard let arr else { return [] }
        return arr.compactMap { item in
            guard let node = item as? [String: Any] else { return nil }
            return VenuePayload(
                id: Json.optString(node, "id"),
                name: Json.optString(node, "name"),
                desc: Json.optString(node, "desc"),
                tips: Json.optString(node, "tips"),
                terrain: Json.optString(node, "terrain")
            )
        }
    }
}
