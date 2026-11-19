import Foundation

struct PoseFrame {
    var tMs: Int64
    var poses: [CocoPose]
    var width: Int
    var height: Int
    var blaze33: [BlazeJoint] = []
    var bbox: BBox? = nil

    func remapToSize(_ origW: Int, _ origH: Int) -> PoseFrame {
        if width == origW && height == origH { return self }
        let sx = Float(origW) / Float(width)
        let sy = Float(origH) / Float(height)
        let scaledPoses = poses.map { pose in
            CocoPose(keypoints: pose.keypoints.map { kp in
                CocoKeypoint(x: kp.x * sx, y: kp.y * sy, confidence: kp.confidence)
            })
        }
        let scaledBlaze = blaze33.map { j in
            BlazeJoint(x: j.x * sx, y: j.y * sy, z: j.z, confidence: j.confidence)
        }
        let scaledBox = bbox.map { b in
            BBox(x1: b.x1 * sx, y1: b.y1 * sy, x2: b.x2 * sx, y2: b.y2 * sy)
        }
        return PoseFrame(tMs: tMs, poses: scaledPoses, width: origW, height: origH,
                         blaze33: scaledBlaze, bbox: scaledBox)
    }
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
