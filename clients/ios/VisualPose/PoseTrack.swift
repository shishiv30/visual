import Foundation

enum PoseTrack {
    static let highScore = 55.0
    static let lowScore = 40.0
    static let maxGapMs = 400.0
    static let holdMs = 200.0
    static let interpConf: Float = 0.85
    static let blazeN = 33
    /// Below this, one landmark (not necessarily the whole pose) is weak enough
    /// that `stabilizeWeakJoints` will try to bridge it from neighbors before
    /// any per-metric consumer has to gate it out. Above it, the joint is left
    /// alone even though a metric's own, usually stricter, confidence gate may
    /// still discount or drop it later.
    static let jointConfMin: Float = 0.35

    /// Bridge one landmark's short confidence dip from its own neighbors.
    ///
    /// `fillLowScore` already does this at the whole-pose level, keyed off the
    /// frame's overall score. That leaves the common ski case unaddressed: the
    /// torso tracks perfectly all the way through a turn but one ankle or foot
    /// drops out for a few frames -- occluded by snow spray, motion blur, or a
    /// self-occlusion at full flex -- while the rest of the skeleton stays
    /// confident. A frame like that never triggers the whole-frame path (its
    /// overall score is fine), so the weak joint used to sit at its raw, noisy
    /// coordinates until a metric's own confidence gate dropped it or (the bug
    /// this fixes) it became the "most extreme" sample and got shown to the
    /// coach as evidence.
    ///
    /// This runs per landmark index, independently of every other joint, with
    /// the exact same `maxGapMs`/`holdMs` policy as the whole-frame version: a
    /// short gap flanked by two well-tracked samples is linearly interpolated
    /// between them; a gap open on only one side is held from that side,
    /// decaying via `interpConf` so it is never mistaken for a fresh
    /// measurement; a gap with no well-tracked anchor on either side (or
    /// longer than `maxGapMs`) is left alone, since there is nothing real to
    /// interpolate from. Run this BEFORE `fillLowScore` -- it operates on a
    /// finer granularity (per blaze33 landmark) than that whole-frame pass.
    static func stabilizeWeakJoints(_ frames: [PoseFrame], confMin: Float = jointConfMin) -> [PoseFrame] {
        let n = frames.count
        if n < 2 { return frames }
        var out = frames
        for j in 0..<blazeN {
            let conf: [Float] = out.map { frame in
                frame.blaze33.count > j ? frame.blaze33[j].confidence : 0.0
            }
            var i = 0
            while i < n {
                if conf[i] >= confMin {
                    i += 1
                    continue
                }
                var k = i
                while k < n && conf[k] < confMin {
                    k += 1
                }
                let leftI = i > 0 && conf[i - 1] >= confMin ? i - 1 : nil
                let rightI = k < n && conf[k] >= confMin ? k : nil
                if let leftI, let rightI {
                    let tLeft = Double(out[leftI].tMs)
                    let tRight = Double(out[rightI].tMs)
                    let span = tRight - tLeft
                    if span > 0 && span <= maxGapMs {
                        let leftJoint = out[leftI].blaze33[j]
                        let rightJoint = out[rightI].blaze33[j]
                        for m in i..<k {
                            guard out[m].blaze33.count > j else { continue }
                            let w = Float((Double(out[m].tMs) - tLeft) / span)
                            out[m].blaze33[j] = lerpJoint(left: leftJoint, right: rightJoint, w: w)
                        }
                    }
                } else if let leftI {
                    let tLeft = Double(out[leftI].tMs)
                    let leftJoint = out[leftI].blaze33[j]
                    for m in i..<k {
                        guard out[m].blaze33.count > j else { continue }
                        if Double(out[m].tMs) - tLeft <= holdMs {
                            out[m].blaze33[j] = holdJoint(leftJoint)
                        }
                    }
                } else if let rightI {
                    let tRight = Double(out[rightI].tMs)
                    let rightJoint = out[rightI].blaze33[j]
                    for m in i..<k {
                        guard out[m].blaze33.count > j else { continue }
                        if tRight - Double(out[m].tMs) <= holdMs {
                            out[m].blaze33[j] = holdJoint(rightJoint)
                        }
                    }
                }
                i = k
            }
        }
        return out
    }

    private static func lerpJoint(left: BlazeJoint, right: BlazeJoint, w: Float) -> BlazeJoint {
        BlazeJoint(
            x: lerp(left.x, right.x, w),
            y: lerp(left.y, right.y, w),
            z: lerp(left.z, right.z, w),
            confidence: min(1.0, min(left.confidence, right.confidence) * interpConf)
        )
    }

    private static func holdJoint(_ anchor: BlazeJoint) -> BlazeJoint {
        BlazeJoint(
            x: anchor.x,
            y: anchor.y,
            z: anchor.z,
            confidence: min(1.0, anchor.confidence * interpConf)
        )
    }

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
