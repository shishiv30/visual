import Foundation

struct CocoKeypoint {
    var x: Float
    var y: Float
    var confidence: Float
}

struct CocoPose {
    var keypoints: [CocoKeypoint]
}

struct OverlayCover {
    var scale: Float
    var dx: Float
    var dy: Float
}

struct OverlaySegment {
    var x1: Float
    var y1: Float
    var x2: Float
    var y2: Float
}

struct OverlayJoint {
    var x: Float
    var y: Float
}

enum OverlayMath {
    static let minVis: Float = 0.3
    static let coco17Edges: [(Int, Int)] = [
        (0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    ]

    static func cover(srcW: Int, srcH: Int, viewW: Int, viewH: Int) -> OverlayCover {
        guard srcW > 0, srcH > 0, viewW > 0, viewH > 0 else {
            return OverlayCover(scale: 1, dx: 0, dy: 0)
        }
        let scale = max(Float(viewW) / Float(srcW), Float(viewH) / Float(srcH))
        return OverlayCover(
            scale: scale,
            dx: (Float(viewW) - Float(srcW) * scale) / 2,
            dy: (Float(viewH) - Float(srcH) * scale) / 2
        )
    }

    static func contain(srcW: Int, srcH: Int, viewW: Int, viewH: Int) -> OverlayCover {
        guard srcW > 0, srcH > 0, viewW > 0, viewH > 0 else {
            return OverlayCover(scale: 1, dx: 0, dy: 0)
        }
        let scale = min(Float(viewW) / Float(srcW), Float(viewH) / Float(srcH))
        return OverlayCover(
            scale: scale,
            dx: (Float(viewW) - Float(srcW) * scale) / 2,
            dy: (Float(viewH) - Float(srcH) * scale) / 2
        )
    }

    static func mapContain(x: Float, y: Float, srcW: Int, srcH: Int, viewW: Int, viewH: Int) -> (Float, Float) {
        let box = contain(srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH)
        return (x * box.scale + box.dx, y * box.scale + box.dy)
    }

    static func unmapContain(x: Float, y: Float, srcW: Int, srcH: Int, viewW: Int, viewH: Int) -> (Float, Float) {
        let box = contain(srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH)
        return ((x - box.dx) / box.scale, (y - box.dy) / box.scale)
    }

    static func mapFillCenter(x: Float, y: Float, srcW: Int, srcH: Int, viewW: Int, viewH: Int) -> (Float, Float) {
        let box = cover(srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH)
        return (x * box.scale + box.dx, y * box.scale + box.dy)
    }

    static func mapPoint(
        x: Float, y: Float, srcW: Int, srcH: Int, viewW: Int, viewH: Int, letterbox: Bool
    ) -> (Float, Float) {
        if letterbox {
            return mapContain(x: x, y: y, srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH)
        }
        return mapFillCenter(x: x, y: y, srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH)
    }

    static func visibleJoints(
        pose: CocoPose, srcW: Int, srcH: Int, viewW: Int, viewH: Int, letterbox: Bool = true
    ) -> [OverlayJoint] {
        pose.keypoints.compactMap { kp in
            guard kp.confidence >= minVis else { return nil }
            let (x, y) = mapPoint(
                x: kp.x, y: kp.y, srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH, letterbox: letterbox
            )
            return OverlayJoint(x: x, y: y)
        }
    }

    static func visibleSegments(
        pose: CocoPose, srcW: Int, srcH: Int, viewW: Int, viewH: Int, letterbox: Bool = true
    ) -> [OverlaySegment] {
        guard pose.keypoints.count >= 17 else { return [] }
        return coco17Edges.compactMap { a, b in
            let pa = pose.keypoints[a]
            let pb = pose.keypoints[b]
            guard pa.confidence >= minVis, pb.confidence >= minVis else { return nil }
            let (x1, y1) = mapPoint(
                x: pa.x, y: pa.y, srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH, letterbox: letterbox
            )
            let (x2, y2) = mapPoint(
                x: pb.x, y: pb.y, srcW: srcW, srcH: srcH, viewW: viewW, viewH: viewH, letterbox: letterbox
            )
            return OverlaySegment(x1: x1, y1: y1, x2: x2, y2: y2)
        }
    }

    static func bboxFromPose(_ pose: CocoPose) -> BBox? {
        let pts = pose.keypoints.filter { $0.confidence >= minVis }
        guard !pts.isEmpty else { return nil }
        return BBox(
            x1: pts.map(\.x).min()!,
            y1: pts.map(\.y).min()!,
            x2: pts.map(\.x).max()!,
            y2: pts.map(\.y).max()!
        )
    }
}
