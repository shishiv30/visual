import Foundation

struct LocText {
    var en: String
    var zh: String = ""
}

struct Threshold {
    var op: String
    var value: Double
    var hi: Double? = nil
}

struct DrillSpec {
    var id: String
    var name: LocText
    var desc: LocText
    var training: [LocText]
    var venueIds: [String]
}

struct CheckpointSpec {
    var id: String
    var name: LocText
    var desc: LocText
    var required: Bool
    var signal: String
    var threshold: Threshold
    var heuristicNotFisCarve: Bool
    var drills: [String]
}

struct LevelSpec {
    var id: String
    var categoryId: String
    var inScope: Bool
    var heuristicNotFisCarve: Bool
    var name: LocText
    var desc: LocText
    var checkpoints: [String]
    var nextLevels: [String]
    var sessionDrills: [String]
    var terrain: String
    var venueIds: [String]
}

struct TerrainSpec {
    var id: String
    var name: LocText
    var desc: LocText
}

struct VenueSpec {
    var id: String
    var terrain: String
    var name: LocText
    var desc: LocText
    var tips: LocText
}

struct Curriculum {
    var schemaVersion: String
    var disclaimer: LocText
    var passScore: Double
    var checkpointPass: Double
    var sysDrill: String
    var categories: [String: LocText]
    var terrains: [String: TerrainSpec]
    var venues: [String: VenueSpec]
    var drills: [String: DrillSpec]
    var checkpoints: [String: CheckpointSpec]
    var levels: [String: LevelSpec]
}

enum CurriculumLoader {
    static func load(_ json: String) -> Curriculum {
        guard let root = Json.object(from: json) else {
            preconditionFailure("invalid curriculum json")
        }
        var categories: [String: LocText] = [:]
        for (key, value) in Json.getObject(root, "categories") {
            guard let item = value as? [String: Any] else { continue }
            categories[key] = loc(item)
        }
        var terrains: [String: TerrainSpec] = [:]
        for (key, value) in Json.getObject(root, "terrains") {
            guard let item = value as? [String: Any] else { continue }
            terrains[key] = TerrainSpec(
                id: Json.optString(item, "id", key),
                name: loc(Json.getObject(item, "name")),
                desc: loc(Json.getObject(item, "desc"))
            )
        }
        var venues: [String: VenueSpec] = [:]
        for (key, value) in Json.getObject(root, "venues") {
            guard let item = value as? [String: Any] else { continue }
            venues[key] = VenueSpec(
                id: Json.optString(item, "id", key),
                terrain: Json.optString(item, "terrain"),
                name: loc(Json.getObject(item, "name")),
                desc: loc(Json.getObject(item, "desc")),
                tips: loc(Json.getObject(item, "tips"))
            )
        }
        var drills: [String: DrillSpec] = [:]
        for (key, value) in Json.getObject(root, "drills") {
            guard let item = value as? [String: Any] else { continue }
            drills[key] = DrillSpec(
                id: Json.optString(item, "id", key),
                name: loc(Json.getObject(item, "name")),
                desc: loc(Json.getObject(item, "desc")),
                training: locList(Json.optArray(item, "training")),
                venueIds: Json.strList(Json.optArray(item, "venue_ids"))
            )
        }
        var checkpoints: [String: CheckpointSpec] = [:]
        for (key, value) in Json.getObject(root, "checkpoints") {
            guard let item = value as? [String: Any] else { continue }
            let thr = Json.getObject(item, "threshold")
            let hi: Double?
            if thr["hi"] != nil && !Json.isNull(thr, "hi") {
                hi = Json.getDouble(thr, "hi")
            } else {
                hi = nil
            }
            checkpoints[key] = CheckpointSpec(
                id: Json.optString(item, "id", key),
                name: loc(Json.getObject(item, "name")),
                desc: loc(Json.getObject(item, "desc")),
                required: Json.optBool(item, "required", true),
                signal: Json.getString(item, "signal"),
                threshold: Threshold(op: Json.getString(thr, "op"), value: Json.getDouble(thr, "value"), hi: hi),
                heuristicNotFisCarve: Json.optBool(item, "heuristic_not_fis_carve", false),
                drills: Json.strList(Json.optArray(item, "drills"))
            )
        }
        var levels: [String: LevelSpec] = [:]
        for (key, value) in Json.getObject(root, "levels") {
            guard let item = value as? [String: Any] else { continue }
            levels[key] = LevelSpec(
                id: Json.optString(item, "id", key),
                categoryId: Json.getString(item, "category_id"),
                inScope: Json.optBool(item, "in_scope", true),
                heuristicNotFisCarve: Json.optBool(item, "heuristic_not_fis_carve", false),
                name: loc(Json.getObject(item, "name")),
                desc: loc(Json.getObject(item, "desc")),
                checkpoints: Json.strList(Json.optArray(item, "checkpoints")),
                nextLevels: Json.strList(Json.optArray(item, "next_levels")),
                sessionDrills: Json.strList(Json.optArray(item, "session_drills")),
                terrain: Json.optString(item, "terrain", "green"),
                venueIds: Json.strList(Json.optArray(item, "venue_ids"))
            )
        }
        return Curriculum(
            schemaVersion: Json.getString(root, "schema_version"),
            disclaimer: loc(Json.getObject(root, "disclaimer")),
            passScore: Json.optDouble(root, "pass_score", 75),
            checkpointPass: Json.optDouble(root, "checkpoint_pass", 60),
            sysDrill: Json.getString(root, "sys_drill"),
            categories: categories,
            terrains: terrains,
            venues: venues,
            drills: drills,
            checkpoints: checkpoints,
            levels: levels
        )
    }

    static func loadFile(_ file: URL) -> Curriculum {
        let text = (try? String(contentsOf: file, encoding: .utf8)) ?? "{}"
        return load(text)
    }

    static func loadFromBundle() -> Curriculum {
        guard let url = Bundle.main.url(forResource: "curriculum.v2", withExtension: "json") else {
            preconditionFailure("curriculum.v2.json missing from bundle")
        }
        return loadFile(url)
    }

    static func locText(_ item: LocText, lang: String) -> String {
        if lang == "zh" && !item.zh.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return item.zh
        }
        return I18n.t(item.en, lang: lang)
    }

    static func locText(_ item: LocText) -> String {
        locText(item, lang: I18n.language())
    }

    private static func loc(_ obj: [String: Any]) -> LocText {
        LocText(en: Json.optString(obj, "en"), zh: Json.optString(obj, "zh"))
    }

    private static func locList(_ arr: [Any]?) -> [LocText] {
        guard let arr else { return [] }
        return arr.compactMap { item in
            guard let obj = item as? [String: Any] else { return nil }
            return loc(obj)
        }
    }
}
