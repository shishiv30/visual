import Foundation

enum PoseFilter {
    static let maxBboxAspect = 3.2
    static let maxHeightOverShoulder = 4.5
    static let maxFullHeightFrac = 0.90
    static let minFullWidthFrac = 0.35
    static let minShoulderVis: Float = 0.30
    static let minHeadVis: Float = 0.20
    static let emaAlpha: Float = 0.45
    static let cropPad = 0.28
    static let tallCropKeepBottom = 0.55

    static let nose = 0
    static let leftEye = 1
    static let rightEye = 2
    static let leftEar = 3
    static let rightEar = 4
    static let leftShoulder = 5
    static let rightShoulder = 6
    static let leftHip = 11
    static let rightHip = 12

    static func bboxIou(_ a: BBox, _ b: BBox) -> Double {
        let ix1 = max(a.x1, b.x1)
        let iy1 = max(a.y1, b.y1)
        let ix2 = min(a.x2, b.x2)
        let iy2 = min(a.y2, b.y2)
        let inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        let areaA = max(0, a.x2 - a.x1) * max(0, a.y2 - a.y1)
        let areaB = max(0, b.x2 - b.x1) * max(0, b.y2 - b.y1)
        let union = areaA + areaB - inter
        if union <= 0 { return 0 }
        return Double(inter / union)
    }

    static func pickPrimary(_ mapped: MappedPeople, prev: BBox?) -> MappedPeople {
        if mapped.poses.count <= 1 { return mapped }
        var bestI = 0
        var best = -1.0
        for i in mapped.poses.indices {
            let kps = mapped.poses[i].keypoints
            var score = kps.isEmpty
                ? Double.nan
                : kps.map { Double($0.confidence) }.reduce(0, +) / Double(kps.count)
            if i < mapped.bboxes.count, let prev {
                score += bboxIou(mapped.bboxes[i], prev)
            }
            if score > best {
                best = score
                bestI = i
            }
        }
        let blaze = bestI < mapped.blazePeople.count ? mapped.blazePeople[bestI] : []
        let box: [BBox] = bestI < mapped.bboxes.count ? [mapped.bboxes[bestI]] : []
        return MappedPeople(
            poses: [mapped.poses[bestI]],
            blazePeople: [blaze],
            bboxes: box
        )
    }

    static func isPlausible(pose: CocoPose, box: BBox, frameW: Int, frameH: Int) -> Bool {
        let width = max(1.0, Double(box.x2 - box.x1))
        let height = max(0.0, Double(box.y2 - box.y1))
        if height / width > maxBboxAspect { return false }
        if height > maxFullHeightFrac * Double(frameH) && width < minFullWidthFrac * Double(frameW) {
            return false
        }
        let leftS = pose.keypoints.indices.contains(leftShoulder) ? pose.keypoints[leftShoulder] : nil
        let rightS = pose.keypoints.indices.contains(rightShoulder) ? pose.keypoints[rightShoulder] : nil
        if let leftS, let rightS,
           leftS.confidence >= minShoulderVis,
           rightS.confidence >= minShoulderVis
        {
            let shoulder = abs(leftS.x - rightS.x)
            if shoulder > 1 && height / Double(shoulder) > maxHeightOverShoulder {
                return false
            }
        }
        let headIds = [nose, leftEye, rightEye, leftEar, rightEar]
        var headVis = 0.0
        var nHead = 0
        for id in headIds {
            guard pose.keypoints.indices.contains(id) else { continue }
            headVis += Double(pose.keypoints[id].confidence)
            nHead += 1
        }
        if nHead > 0 && (headVis / Double(nHead)) < Double(minHeadVis) {
            return false
        }
        return true
    }

    static func isPlausible(_ mapped: MappedPeople, frameW: Int, frameH: Int) -> Bool {
        guard let pose = mapped.poses.first, let box = mapped.bboxes.first else { return false }
        return isPlausible(pose: pose, box: box, frameW: frameW, frameH: frameH)
    }

    static func cropDisagreesWithPrev(_ prev: MappedPeople?, _ curr: MappedPeople) -> Bool {
        guard let prev, !prev.poses.isEmpty, !curr.poses.isEmpty else { return false }
        let tPrev = torsoLength(prev.poses[0])
        let tCurr = torsoLength(curr.poses[0])
        if tPrev > 1.0 && tCurr / tPrev < 0.75 { return true }
        return relativeJump(prev.poses[0], curr.poses[0]) > 0.35
    }

    static func cropBoxForRetry(_ bbox: BBox, frameW: Int, frameH: Int) -> PixelBox {
        let bw = max(1.0, Double(bbox.x2 - bbox.x1))
        let bh = max(1.0, Double(bbox.y2 - bbox.y1))
        let y1 = Double(bbox.y1) + bh * (1.0 - tallCropKeepBottom)
        let padX = bw * cropPad
        let padY = bh * cropPad * tallCropKeepBottom
        let nx1 = max(0.0, Double(bbox.x1) - padX)
        let ny1 = max(0.0, y1 - padY)
        let nx2 = min(Double(frameW), Double(bbox.x2) + padX)
        let ny2 = min(Double(frameH), Double(bbox.y2) + padY)
        if nx2 <= nx1 || ny2 <= ny1 {
            return PixelBox(x1: 0, y1: 0, x2: Double(frameW), y2: Double(frameH))
        }
        return PixelBox(x1: nx1, y1: ny1, x2: nx2, y2: ny2)
    }

    static func emaSmooth(_ prev: MappedPeople?, _ curr: MappedPeople) -> MappedPeople {
        guard let prev, !prev.poses.isEmpty, !curr.poses.isEmpty else { return curr }
        let prevKps = prev.poses[0].keypoints
        let currKps = curr.poses[0].keypoints
        if prevKps.count != currKps.count { return curr }
        let mixed: [CocoKeypoint] = currKps.enumerated().map { i, b in
            let a = prevKps[i]
            if b.confidence < 0.2 {
                return CocoKeypoint(x: a.x, y: a.y, confidence: b.confidence)
            }
            return CocoKeypoint(
                x: emaAlpha * b.x + (1 - emaAlpha) * a.x,
                y: emaAlpha * b.y + (1 - emaAlpha) * a.y,
                confidence: b.confidence
            )
        }
        let box: BBox?
        if !prev.bboxes.isEmpty && !curr.bboxes.isEmpty {
            let px = prev.bboxes[0]
            let cx = curr.bboxes[0]
            box = BBox(
                x1: emaAlpha * cx.x1 + (1 - emaAlpha) * px.x1,
                y1: emaAlpha * cx.y1 + (1 - emaAlpha) * px.y1,
                x2: emaAlpha * cx.x2 + (1 - emaAlpha) * px.x2,
                y2: emaAlpha * cx.y2 + (1 - emaAlpha) * px.y2
            )
        } else {
            box = curr.bboxes.first
        }
        let blaze: [BlazeJoint]
        if !prev.blazePeople.isEmpty && !curr.blazePeople.isEmpty {
            let pa = prev.blazePeople[0]
            let pb = curr.blazePeople[0]
            if pa.count == pb.count {
                blaze = pb.enumerated().map { i, b in
                    let a = pa[i]
                    if b.confidence < 0.2 {
                        return BlazeJoint(x: a.x, y: a.y, z: a.z, confidence: b.confidence)
                    }
                    return BlazeJoint(
                        x: emaAlpha * b.x + (1 - emaAlpha) * a.x,
                        y: emaAlpha * b.y + (1 - emaAlpha) * a.y,
                        z: emaAlpha * b.z + (1 - emaAlpha) * a.z,
                        confidence: b.confidence
                    )
                }
            } else {
                blaze = pb
            }
        } else {
            blaze = curr.blazePeople.first ?? []
        }
        return MappedPeople(
            poses: [CocoPose(keypoints: mixed)],
            blazePeople: [blaze],
            bboxes: box.map { [$0] } ?? []
        )
    }

    static func torsoLength(_ pose: CocoPose) -> Double {
        guard let sh = pairMid(pose, leftShoulder, rightShoulder),
              let hp = pairMid(pose, leftHip, rightHip)
        else { return 0 }
        let dx = sh.0 - hp.0
        let dy = sh.1 - hp.1
        return sqrt(dx * dx + dy * dy)
    }

    private static func relativeJump(_ a: CocoPose, _ b: CocoPose) -> Double {
        let am = pairMid(a, leftHip, rightHip) ?? pairMid(a, leftShoulder, rightShoulder)
        let bm = pairMid(b, leftHip, rightHip) ?? pairMid(b, leftShoulder, rightShoulder)
        guard let am, let bm else { return 0 }
        let dx = am.0 - bm.0
        let dy = am.1 - bm.1
        let scale = max(torsoLength(a), max(torsoLength(b), 1.0))
        return sqrt(dx * dx + dy * dy) / scale
    }

    private static func pairMid(_ pose: CocoPose, _ left: Int, _ right: Int) -> (Double, Double)? {
        guard pose.keypoints.indices.contains(left), pose.keypoints.indices.contains(right) else {
            return nil
        }
        let a = pose.keypoints[left]
        let b = pose.keypoints[right]
        if a.confidence < minShoulderVis || b.confidence < minShoulderVis { return nil }
        return ((Double(a.x) + Double(b.x)) / 2.0, (Double(a.y) + Double(b.y)) / 2.0)
    }
}
