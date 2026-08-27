import Foundation

enum ClipRange {
    static let frameStride = 2

    static func collectSeeds(_ seeds: [SeedMark], seedBox: NormBox?) -> [SeedMark] {
        if !seeds.isEmpty { return seeds.sorted { $0.tMs < $1.tMs } }
        if let seedBox { return [SeedMark(tMs: 0, box: seedBox)] }
        return []
    }

    static func seedAt(tMs: Double, seeds: [SeedMark], halfMs: Double) -> SeedMark? {
        var hit: SeedMark?
        var best = halfMs
        for item in seeds {
            let delta = abs(item.tMs - tMs)
            if delta <= best {
                best = delta
                hit = item
            }
        }
        return hit
    }

    static func inPlayRange(tMs: Double, startMs: Double, endMs: Double) -> Bool {
        tMs >= startMs && tMs <= endMs
    }

    static func clampPlayheadMs(_ tMs: Int64, startMs: Int64, endMs: Int64) -> Int64 {
        let hi = max(startMs, endMs - 1)
        return min(max(tMs, startMs), hi)
    }

    static func pastPlayEnd(posMs: Int64, endMs: Int64) -> Bool {
        posMs >= endMs
    }

    static func shouldReseekToStart(posMs: Int64, startMs: Int64, seekPending: Bool) -> Bool {
        !seekPending && posMs < startMs
    }

    static func strideMs(fps: Double) -> Int64 {
        let step = (1000.0 / max(fps, 1)) * Double(frameStride)
        let truncated = Int64(step)
        let rounded = (step - Double(truncated) >= 0.5) ? truncated + 1 : truncated
        return max(1, rounded)
    }

    static func halfMs(fps: Double) -> Double {
        (1000.0 / max(fps, 1)) * Double(frameStride) / 2
    }
}
