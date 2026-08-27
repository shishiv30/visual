import Foundation

enum AthleteGender: String {
    case unspecified
    case female
    case male
    case other

    static func fromValue(_ raw: String?) -> AthleteGender {
        AthleteGender(rawValue: raw ?? "") ?? .unspecified
    }
}

struct AthleteProfile {
    var key: String
    var name: String
    var birthday: String = ""
    var heightCm: Float
    var gender: AthleteGender = .unspecified
    var weightKg: Float
    var skiCm: Float
    var updatedAt: String = ""

    func toJson() -> [String: Any] {
        [
            "key": key,
            "name": name,
            "birthday": birthday,
            "height_cm": Double(heightCm),
            "gender": gender.rawValue,
            "weight_kg": Double(weightKg),
            "ski_cm": Double(skiCm),
            "updated_at": updatedAt,
        ]
    }

    static func fromJson(_ obj: [String: Any]) -> AthleteProfile {
        AthleteProfile(
            key: Json.optString(obj, "key"),
            name: Json.optString(obj, "name"),
            birthday: Json.optString(obj, "birthday"),
            heightCm: Float(Json.optDouble(obj, "height_cm", 0)),
            gender: AthleteGender.fromValue(Json.optString(obj, "gender")),
            weightKg: Float(Json.optDouble(obj, "weight_kg", 0)),
            skiCm: Float(Json.optDouble(obj, "ski_cm", 0)),
            updatedAt: Json.optString(obj, "updated_at")
        )
    }
}

enum AthletesError: LocalizedError {
    case nameRequired
    case measuresMustBePositive

    var errorDescription: String? {
        switch self {
        case .nameRequired: return "name required"
        case .measuresMustBePositive: return "measures must be positive"
        }
    }
}

final class Athletes {
    private let file: URL

    init(_ file: URL) {
        self.file = file
    }

    func list() -> [AthleteProfile] {
        load().sorted {
            $0.key.lowercased(with: Locale(identifier: "en_US"))
                < $1.key.lowercased(with: Locale(identifier: "en_US"))
        }
    }

    func getByKey(_ key: String) -> AthleteProfile? {
        let want = key.trimmingCharacters(in: .whitespacesAndNewlines)
        return load().first { $0.key == want }
    }

    @discardableResult
    func upsert(
        name: String,
        weightKg: Float,
        heightCm: Float,
        skiCm: Float,
        birthday: String = "",
        gender: AthleteGender = .unspecified
    ) throws -> AthleteProfile {
        let cleaned = Athletes.collapseSpaces(name)
        if cleaned.isEmpty { throw AthletesError.nameRequired }
        if weightKg <= 0 || heightCm <= 0 || skiCm <= 0 { throw AthletesError.measuresMustBePositive }
        let profile = AthleteProfile(
            key: Athletes.athleteKey(cleaned, weightKg, heightCm, skiCm),
            name: cleaned,
            birthday: birthday.trimmingCharacters(in: .whitespacesAndNewlines),
            heightCm: Athletes.round1(heightCm),
            gender: gender,
            weightKg: Athletes.round1(weightKg),
            skiCm: Athletes.round1(skiCm),
            updatedAt: Athletes.nowIso()
        )
        var next: [AthleteProfile] = []
        var replaced = false
        for item in load() {
            if item.key == profile.key {
                next.append(profile)
                replaced = true
            } else {
                next.append(item)
            }
        }
        if !replaced { next.append(profile) }
        save(next)
        return profile
    }

    private func load() -> [AthleteProfile] {
        guard Json.isFile(file),
              let text = try? String(contentsOf: file, encoding: .utf8),
              let root = Json.object(from: text)
        else { return [] }
        let arr = Json.optArray(root, "athletes") ?? []
        return arr.compactMap { item in
            guard let obj = item as? [String: Any] else { return nil }
            return AthleteProfile.fromJson(obj)
        }
    }

    private func save(_ athletes: [AthleteProfile]) {
        Json.write(
            file,
            [
                "schema_version": "1.0.0",
                "athletes": athletes.map { $0.toJson() },
            ],
            pretty: true
        )
    }

    static func formatMeasure(_ value: Float) -> String {
        let rounded = round1(value)
        if rounded == Float(Int(rounded)) {
            return String(Int(rounded))
        }
        return String(format: "%.1f", locale: Locale(identifier: "en_US"), Double(rounded))
    }

    static func athleteKey(_ name: String, _ weightKg: Float, _ heightCm: Float, _ skiCm: Float) -> String {
        let cleaned = collapseSpaces(name)
        return "\(cleaned)-\(formatMeasure(weightKg))-\(formatMeasure(heightCm))-\(formatMeasure(skiCm))"
    }

    static func round1(_ value: Float) -> Float { Json.round1(value) }

    static func nowIso() -> String { IsoClock.now() }

    static func collapseSpaces(_ name: String) -> String {
        name.trimmingCharacters(in: .whitespacesAndNewlines)
            .split { $0.isWhitespace }
            .filter { !$0.isEmpty }
            .joined(separator: " ")
    }
}
