import Foundation

enum ClipKind: String {
    case video
    case image
}

enum ClipStatus: String {
    case pending
    case processing
    case done
}

struct BBox {
    var x1: Float
    var y1: Float
    var x2: Float
    var y2: Float
}

struct BlazeJoint {
    var x: Float
    var y: Float
    var z: Float = 0
    var confidence: Float
}

struct NormBox {
    var x1: Float
    var y1: Float
    var x2: Float
    var y2: Float

    func toList() -> [Float] { [x1, y1, x2, y2] }

    static func fromArray(_ arr: [Any]) -> NormBox? {
        guard arr.count >= 4,
              let x1 = Json.number(arr[0]),
              let y1 = Json.number(arr[1]),
              let x2 = Json.number(arr[2]),
              let y2 = Json.number(arr[3])
        else { return nil }
        return NormBox(x1: Float(x1), y1: Float(y1), x2: Float(x2), y2: Float(y2))
    }
}

struct SeedMark {
    var tMs: Double
    var box: NormBox
}

struct ClipMeta {
    var clipId: String
    var createdAt: String
    var displayName: String
    var durationMs: Int = 0
    var width: Int = 1
    var height: Int = 1
    var fps: Double = 30
    var kind: ClipKind = .video
    var status: ClipStatus = .pending
    var error: String? = nil
    var seedBox: NormBox? = nil
    var seeds: [SeedMark] = []
    var playStartMs: Int = 0
    var playEndMs: Int? = nil
    var athleteKey: String? = nil
    var athlete: AthleteProfile? = nil
}

enum IsoClock {
    static func now(_ date: Date = Date()) -> String {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone.current
        fmt.dateFormat = "yyyy-MM-dd'T'HH:mm:ssXXX"
        return fmt.string(from: date)
    }

    static func displayName(_ date: Date = Date()) -> String {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone.current
        fmt.dateFormat = "MM/dd/yyyy-HH:mm"
        return fmt.string(from: date)
    }
}
