import Foundation

struct PoseFrame {
    var tMs: Int64
    var poses: [CocoPose]
    var width: Int
    var height: Int
    var blaze33: [BlazeJoint] = []
    var bbox: BBox? = nil
}

enum PoseTimeline {
    static func nearest(_ frames: [PoseFrame], tMs: Int64) -> PoseFrame? {
        if frames.isEmpty { return nil }
        var lo = 0
        var hi = frames.count
        while lo < hi {
            let mid = lo + (hi - lo) / 2
            if frames[mid].tMs < tMs {
                lo = mid + 1
            } else {
                hi = mid
            }
        }
        if lo < frames.count && frames[lo].tMs == tMs {
            return frames[lo]
        }
        let insert = lo
        let loI = max(insert - 1, 0)
        let hiI = min(insert, frames.count - 1)
        if abs(frames[loI].tMs - tMs) <= abs(frames[hiI].tMs - tMs) {
            return frames[loI]
        }
        return frames[hiI]
    }
}
