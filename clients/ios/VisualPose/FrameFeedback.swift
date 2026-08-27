import Foundation

struct FrameFeedbackEntry {
    var tMs: Double = 0
    var poseIndex: Int? = nil
    var stageVote: String? = nil
    var skeletonOk: Bool = true
    var updatedAt: String = ""
}

struct FrameFeedbackFile {
    var clipId: String
    var stageIdAtVote: String = ""
    var frames: [String: FrameFeedbackEntry] = [:]
}

enum FrameFeedback {
    static func empty(_ clipId: String) -> FrameFeedbackFile {
        FrameFeedbackFile(clipId: clipId)
    }

    static func load(_ file: URL, clipId: String) -> FrameFeedbackFile {
        let emptyDoc = empty(clipId)
        guard Json.isFile(file),
              let text = try? String(contentsOf: file, encoding: .utf8),
              let obj = Json.object(from: text)
        else { return emptyDoc }
        var doc = FrameFeedbackFile(
            clipId: Json.optString(obj, "clip_id", clipId),
            stageIdAtVote: Json.optString(obj, "stage_id_at_vote")
        )
        let frames = Json.optObject(obj, "frames") ?? [:]
        for (key, raw) in frames {
            guard let item = raw as? [String: Any] else { continue }
            let poseIndex: Int? = Json.isNull(item, "pose_index") ? nil : Json.optInt(item, "pose_index")
            let stageVote: String?
            if Json.isNull(item, "stage_vote") {
                stageVote = nil
            } else {
                let rawVote = Json.optString(item, "stage_vote")
                stageVote = rawVote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : rawVote
            }
            doc.frames[key] = FrameFeedbackEntry(
                tMs: Json.optDouble(item, "t_ms", 0),
                poseIndex: poseIndex,
                stageVote: stageVote,
                skeletonOk: Json.optBool(item, "skeleton_ok", true),
                updatedAt: Json.optString(item, "updated_at")
            )
        }
        return doc
    }

    static func save(_ file: URL, _ doc: FrameFeedbackFile) {
        var frames: [String: Any] = [:]
        for (key, entry) in doc.frames {
            var item: [String: Any] = [
                "t_ms": entry.tMs,
                "skeleton_ok": entry.skeletonOk,
                "updated_at": entry.updatedAt,
                "pose_index": entry.poseIndex ?? NSNull(),
                "stage_vote": entry.stageVote ?? NSNull(),
            ]
            _ = item
            frames[key] = item
        }
        Json.write(
            file,
            [
                "clip_id": doc.clipId,
                "stage_id_at_vote": doc.stageIdAtVote,
                "frames": frames,
            ],
            pretty: true
        )
    }

    @discardableResult
    static func toggleVote(
        file: URL,
        clipId: String,
        videoFrame: Int,
        vote: String,
        tMs: Double,
        poseIndex: Int?,
        stageId: String
    ) -> FrameFeedbackFile {
        var doc = load(file, clipId: clipId)
        doc.clipId = clipId
        var entry = touch(&doc, videoFrame: videoFrame, tMs: tMs, poseIndex: poseIndex, stageId: stageId)
        entry.stageVote = entry.stageVote == vote ? nil : vote
        doc.frames[String(videoFrame)] = entry
        save(file, doc)
        return doc
    }

    @discardableResult
    static func toggleSkeleton(
        file: URL,
        clipId: String,
        videoFrame: Int,
        tMs: Double,
        poseIndex: Int?,
        stageId: String
    ) -> FrameFeedbackFile {
        var doc = load(file, clipId: clipId)
        doc.clipId = clipId
        var entry = touch(&doc, videoFrame: videoFrame, tMs: tMs, poseIndex: poseIndex, stageId: stageId)
        entry.skeletonOk.toggle()
        doc.frames[String(videoFrame)] = entry
        save(file, doc)
        return doc
    }

    private static func touch(
        _ doc: inout FrameFeedbackFile,
        videoFrame: Int,
        tMs: Double,
        poseIndex: Int?,
        stageId: String
    ) -> FrameFeedbackEntry {
        let key = String(videoFrame)
        var entry = doc.frames[key] ?? FrameFeedbackEntry()
        entry.tMs = tMs
        entry.poseIndex = poseIndex
        entry.updatedAt = IsoClock.now()
        if !stageId.isEmpty {
            doc.stageIdAtVote = stageId
        }
        doc.frames[key] = entry
        return entry
    }
}
