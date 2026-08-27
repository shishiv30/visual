import Foundation

enum PoseTrack {
    static let highScore = 55.0
    static let lowScore = 40.0
    static let maxGapMs = 400.0
    static let holdMs = 200.0
    static let interpConf: Float = 0.85

    static func fillLowScore(_ frames: [PoseFrame]) -> [PoseFrame] {
        if frames.count <= 1 { return frames }
        let scores = frames.map { frameScore($0) }
        var out = frames
        var i = 0
        let n = out.count
        while i < n {
            if scores[i] >= lowScore {
                i += 1
                continue
            }
            var j = i
            while j < n && scores[j] < lowScore {
                j += 1
            }
            let leftI = nearestHigh(scores, start: i - 1, step: -1)
            let rightI = nearestHigh(scores, start: j, step: 1)
            if let leftI, let rightI {
                let tLeft = Double(out[leftI].tMs)
                let tRight = Double(out[rightI].tMs)
                let gap = tRight - tLeft
                if gap >= 0 && gap <= maxGapMs {
                    let span = tRight - tLeft
                    for k in i..<j {
                        let w = Float((Double(out[k].tMs) - tLeft) / span)
                        out[k] = lerpFrame(left: out[leftI], right: out[rightI], curr: out[k], w: w)
                    }
                }
            } else if let leftI {
                for k in i..<j {
                    if Double(out[k].tMs - out[leftI].tMs) <= holdMs {
                        out[k] = holdFrame(out[leftI], out[k])
                    }
                }
            } else if let rightI {
                for k in i..<j {
                    if Double(out[rightI].tMs - out[k].tMs) <= holdMs {
                        out[k] = holdFrame(out[rightI], out[k])
                    }
                }
            }
            i = j
        }
        return out
    }

    static func frameScore(_ frame: PoseFrame) -> Double {
        guard let pose = frame.poses.first else { return 0 }
        let vis = pose.keypoints.map { Double($0.confidence) }
        if vis.isEmpty { return 0 }
        let avg = vis.reduce(0, +) / Double(vis.count) * 100.0
        return min(max(avg, 0), 100)
    }

    private static func nearestHigh(_ scores: [Double], start: Int, step: Int) -> Int? {
        var i = start
        while scores.indices.contains(i) {
            if scores[i] >= highScore { return i }
            i += step
        }
        return nil
    }

    private static func lerpFrame(left: PoseFrame, right: PoseFrame, curr: PoseFrame, w: Float) -> PoseFrame {
        guard let lp = left.poses.first, let rp = right.poses.first else { return curr }
        let pose = CocoPose(
            keypoints: lp.keypoints.enumerated().map { i, a in
                let b = rp.keypoints.indices.contains(i) ? rp.keypoints[i] : a
                return CocoKeypoint(
                    x: lerp(a.x, b.x, w),
                    y: lerp(a.y, b.y, w),
                    confidence: min(a.confidence, b.confidence) * interpConf
                )
            }
        )
        let blaze: [BlazeJoint]
        if left.blaze33.count == right.blaze33.count && !left.blaze33.isEmpty {
            blaze = left.blaze33.enumerated().map { i, a in
                let b = right.blaze33[i]
                return BlazeJoint(
                    x: lerp(a.x, b.x, w),
                    y: lerp(a.y, b.y, w),
                    z: lerp(a.z, b.z, w),
                    confidence: min(a.confidence, b.confidence) * interpConf
                )
            }
        } else {
            blaze = left.blaze33
        }
        let box: BBox?
        if let lb = left.bbox, let rb = right.bbox {
            box = BBox(
                x1: lerp(lb.x1, rb.x1, w),
                y1: lerp(lb.y1, rb.y1, w),
                x2: lerp(lb.x2, rb.x2, w),
                y2: lerp(lb.y2, rb.y2, w)
            )
        } else {
            box = left.bbox ?? right.bbox
        }
        var next = curr
        next.poses = [pose]
        next.blaze33 = blaze
        next.bbox = box
        return next
    }

    private static func holdFrame(_ anchor: PoseFrame, _ curr: PoseFrame) -> PoseFrame {
        guard let pose = anchor.poses.first else { return curr }
        var next = curr
        next.poses = [
            CocoPose(
                keypoints: pose.keypoints.map { kp in
                    CocoKeypoint(x: kp.x, y: kp.y, confidence: kp.confidence * interpConf)
                }
            ),
        ]
        next.blaze33 = anchor.blaze33.map { j in
            BlazeJoint(x: j.x, y: j.y, z: j.z, confidence: j.confidence * interpConf)
        }
        next.bbox = anchor.bbox
        return next
    }

    private static func lerp(_ a: Float, _ b: Float, _ w: Float) -> Float {
        (1 - w) * a + w * b
    }
}
