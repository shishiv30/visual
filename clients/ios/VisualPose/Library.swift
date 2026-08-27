import Foundation

final class Library {
    static let maxMs: Int64 = 120_000

    let root: URL

    init(_ root: URL) {
        self.root = root
    }

    func clipDir(_ clipId: String) -> URL {
        root.appendingPathComponent(clipId, isDirectory: true)
    }

    func mediaFile(_ meta: ClipMeta) -> URL {
        let folder = clipDir(meta.clipId)
        return meta.kind == .image
            ? folder.appendingPathComponent("clip.jpg")
            : folder.appendingPathComponent("clip.mp4")
    }

    func thumbFile(_ clipId: String) -> URL {
        clipDir(clipId).appendingPathComponent("thumb.jpg")
    }

    func metaFile(_ clipId: String) -> URL {
        clipDir(clipId).appendingPathComponent("meta.json")
    }

    func analysisFile(_ clipId: String) -> URL {
        clipDir(clipId).appendingPathComponent("analysis.json")
    }

    func stageReportFile(_ clipId: String) -> URL {
        clipDir(clipId).appendingPathComponent("stage_report.json")
    }

    func frameFeedbackFile(_ clipId: String) -> URL {
        clipDir(clipId).appendingPathComponent("frame_feedback.json")
    }

    func saveMeta(_ meta: ClipMeta) {
        Json.write(metaFile(meta.clipId), Library.toJson(meta), pretty: true)
    }

    func loadMeta(_ clipId: String) -> ClipMeta {
        let text = (try? String(contentsOf: metaFile(clipId), encoding: .utf8)) ?? "{}"
        return Library.fromJson(Json.object(from: text) ?? [:])
    }

    func listClips() -> [ClipMeta] {
        guard Json.isDirectory(root),
              let folders = try? FileManager.default.contentsOfDirectory(
                  at: root, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles]
              )
        else { return [] }
        return folders.compactMap { folder in
            let path = folder.appendingPathComponent("meta.json")
            guard Json.isFile(path), let obj = Json.readObject(path) else { return nil }
            return Library.fromJson(obj)
        }
        .sorted { $0.createdAt > $1.createdAt }
    }

    func deleteClip(_ clipId: String) {
        try? FileManager.default.removeItem(at: clipDir(clipId))
    }

    @discardableResult
    func prepareReanalyze(_ clipId: String) -> ClipMeta {
        var meta = loadMeta(clipId)
        meta.status = .pending
        meta.error = nil
        meta.seedBox = nil
        meta.seeds = []
        meta.playStartMs = 0
        meta.playEndMs = nil
        saveMeta(meta)
        try? FileManager.default.removeItem(at: analysisFile(clipId))
        try? FileManager.default.removeItem(at: stageReportFile(clipId))
        try? FileManager.default.removeItem(at: frameFeedbackFile(clipId))
        return meta
    }

    func newClipId() -> String {
        UUID().uuidString.lowercased()
    }

    static func displayNameNow(_ now: Date = Date()) -> String {
        IsoClock.displayName(now)
    }

    static func createdAtIso(_ now: Date = Date()) -> String {
        IsoClock.now(now)
    }

    static func formatDurationMs(_ ms: Int, image: Bool = false) -> String {
        if image { return "--" }
        let total = max(ms / 1000, 0)
        let m = total / 60
        let s = total % 60
        return "\(m):\(String(format: "%02d", s))"
    }

    static func playWindowMs(_ meta: ClipMeta) -> (Int64, Int64) {
        let start = max(Int64(meta.playStartMs), 0)
        let end: Int64
        if let playEnd = meta.playEndMs {
            end = Int64(playEnd)
        } else if meta.durationMs > 0 {
            end = Int64(meta.durationMs)
        } else {
            end = Int64.max / 4
        }
        return (start, end <= start ? start + 1 : end)
    }

    static func statusKey(_ status: ClipStatus) -> String {
        switch status {
        case .pending: return "Pending"
        case .processing: return "Processing"
        case .done: return "Done"
        }
    }

    static func toJson(_ meta: ClipMeta) -> [String: Any] {
        [
            "clip_id": meta.clipId,
            "created_at": meta.createdAt,
            "display_name": meta.displayName,
            "duration_ms": meta.durationMs,
            "width": meta.width,
            "height": meta.height,
            "fps": meta.fps,
            "kind": meta.kind.rawValue,
            "status": meta.status.rawValue,
            "error": meta.error ?? NSNull(),
            "seed_box": meta.seedBox.map { $0.toList().map { Double($0) } as Any } ?? NSNull(),
            "seeds": meta.seeds.map { seed -> [String: Any] in
                [
                    "t_ms": seed.tMs,
                    "box": seed.box.toList().map { Double($0) },
                ]
            },
            "play_start_ms": meta.playStartMs,
            "play_end_ms": meta.playEndMs ?? NSNull(),
            "athlete_key": meta.athleteKey ?? NSNull(),
            "athlete": meta.athlete.map { $0.toJson() as Any } ?? NSNull(),
        ]
    }

    static func fromJson(_ obj: [String: Any]) -> ClipMeta {
        let seedArr = Json.optArray(obj, "seed_box")
        var seeds: [SeedMark] = []
        if let seedsArr = Json.optArray(obj, "seeds") {
            for item in seedsArr {
                guard let node = item as? [String: Any],
                      let boxArr = Json.optArray(node, "box"),
                      let box = NormBox.fromArray(boxArr)
                else { continue }
                seeds.append(SeedMark(tMs: Json.optDouble(node, "t_ms", 0), box: box))
            }
        }
        let playEnd: Int?
        if Json.isNull(obj, "play_end_ms") {
            playEnd = nil
        } else {
            playEnd = max(Int(Json.optDouble(obj, "play_end_ms", 0)), 0)
        }
        let athleteKey: String?
        if obj["athlete_key"] != nil && !Json.isNull(obj, "athlete_key") {
            let raw = Json.optString(obj, "athlete_key")
            athleteKey = raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : raw
        } else {
            athleteKey = nil
        }
        let error: String?
        if Json.isNull(obj, "error") {
            error = nil
        } else {
            let raw = Json.optString(obj, "error")
            error = raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : raw
        }
        return ClipMeta(
            clipId: Json.opt(obj, "clip_id") as? String ?? "",
            createdAt: Json.optString(obj, "created_at"),
            displayName: Json.optString(obj, "display_name"),
            durationMs: Json.optInt(obj, "duration_ms"),
            width: max(Json.optInt(obj, "width", 1), 1),
            height: max(Json.optInt(obj, "height", 1), 1),
            fps: Json.optDouble(obj, "fps", 30),
            kind: Json.optString(obj, "kind") == "image" ? .image : .video,
            status: {
                switch Json.optString(obj, "status") {
                case "processing": return .processing
                case "done": return .done
                default: return .pending
                }
            }(),
            error: error,
            seedBox: seedArr.flatMap { NormBox.fromArray($0) },
            seeds: seeds,
            playStartMs: max(Int(Json.optDouble(obj, "play_start_ms", 0)), 0),
            playEndMs: playEnd,
            athleteKey: athleteKey,
            athlete: Json.optObject(obj, "athlete").map { AthleteProfile.fromJson($0) }
        )
    }
}
