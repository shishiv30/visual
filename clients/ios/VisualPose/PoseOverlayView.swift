import UIKit

final class PoseOverlayView: UIView {
    private var poses: [CocoPose] = []
    private var bbox: BBox?
    private var srcW = 1
    private var srcH = 1
    private var letterbox = true

    override init(frame: CGRect) {
        super.init(frame: frame)
        isOpaque = false
        backgroundColor = .clear
        isUserInteractionEnabled = false
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        isOpaque = false
        backgroundColor = .clear
        isUserInteractionEnabled = false
    }

    func setPoses(_ next: [CocoPose], frameWidth: Int, frameHeight: Int, box: BBox? = nil) {
        poses = next
        bbox = box ?? next.first.flatMap { OverlayMath.bboxFromPose($0) }
        srcW = max(1, frameWidth)
        srcH = max(1, frameHeight)
        setNeedsDisplay()
    }

    func setLetterbox(_ enabled: Bool) {
        letterbox = enabled
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        let vw = Int(bounds.width)
        let vh = Int(bounds.height)
        if let box = bbox {
            let (l, t) = OverlayMath.mapPoint(x: box.x1, y: box.y1, srcW: srcW, srcH: srcH, viewW: vw, viewH: vh, letterbox: letterbox)
            let (r, b) = OverlayMath.mapPoint(x: box.x2, y: box.y2, srcW: srcW, srcH: srcH, viewW: vw, viewH: vh, letterbox: letterbox)
            ctx.setStrokeColor(Theme.bbox.cgColor)
            ctx.setLineWidth(3)
            ctx.stroke(CGRect(x: CGFloat(l), y: CGFloat(t), width: CGFloat(r - l), height: CGFloat(b - t)))
        }
        let compact = bounds.width < 640
        let lineW: CGFloat = compact ? 1 : 6
        let dotR: CGFloat  = compact ? 1 : 8
        ctx.setStrokeColor(Theme.bone.cgColor)
        ctx.setLineWidth(lineW)
        ctx.setLineCap(.round)
        for pose in poses {
            for seg in OverlayMath.visibleSegments(pose: pose, srcW: srcW, srcH: srcH, viewW: vw, viewH: vh, letterbox: letterbox) {
                ctx.move(to: CGPoint(x: CGFloat(seg.x1), y: CGFloat(seg.y1)))
                ctx.addLine(to: CGPoint(x: CGFloat(seg.x2), y: CGFloat(seg.y2)))
            }
        }
        ctx.strokePath()
        ctx.setFillColor(Theme.joint.cgColor)
        for pose in poses {
            for joint in OverlayMath.visibleJoints(pose: pose, srcW: srcW, srcH: srcH, viewW: vw, viewH: vh, letterbox: letterbox) {
                ctx.fillEllipse(in: CGRect(x: CGFloat(joint.x) - dotR, y: CGFloat(joint.y) - dotR, width: dotR * 2, height: dotR * 2))
            }
        }
    }
}

enum OverlayStamp {
    static func stamp(src: UIImage, frame: PoseFrame?) -> UIImage {
        guard let frame else { return src }
        let size = src.size
        let renderer = UIGraphicsImageRenderer(size: size)
        return renderer.image { ctx in
            src.draw(in: CGRect(origin: .zero, size: size))
            let vw = Int(size.width)
            let vh = Int(size.height)
            let box = frame.bbox ?? frame.poses.first.flatMap { OverlayMath.bboxFromPose($0) }
            if let box {
                let (l, t) = OverlayMath.mapContain(x: box.x1, y: box.y1, srcW: frame.width, srcH: frame.height, viewW: vw, viewH: vh)
                let (r, b) = OverlayMath.mapContain(x: box.x2, y: box.y2, srcW: frame.width, srcH: frame.height, viewW: vw, viewH: vh)
                ctx.cgContext.setStrokeColor(Theme.bbox.cgColor)
                ctx.cgContext.setLineWidth(4)
                ctx.cgContext.stroke(CGRect(x: CGFloat(l), y: CGFloat(t), width: CGFloat(r - l), height: CGFloat(b - t)))
            }
            let stampCompact = size.width < 640
            let sLineW: CGFloat = stampCompact ? 1 : 6
            let sDotR: CGFloat  = stampCompact ? 1 : 8
            ctx.cgContext.setStrokeColor(Theme.bone.cgColor)
            ctx.cgContext.setLineWidth(sLineW)
            ctx.cgContext.setLineCap(.round)
            for pose in frame.poses {
                for seg in OverlayMath.visibleSegments(
                    pose: pose, srcW: frame.width, srcH: frame.height, viewW: vw, viewH: vh, letterbox: true
                ) {
                    ctx.cgContext.move(to: CGPoint(x: CGFloat(seg.x1), y: CGFloat(seg.y1)))
                    ctx.cgContext.addLine(to: CGPoint(x: CGFloat(seg.x2), y: CGFloat(seg.y2)))
                }
            }
            ctx.cgContext.strokePath()
            ctx.cgContext.setFillColor(Theme.joint.cgColor)
            for pose in frame.poses {
                for joint in OverlayMath.visibleJoints(
                    pose: pose, srcW: frame.width, srcH: frame.height, viewW: vw, viewH: vh, letterbox: true
                ) {
                    ctx.cgContext.fillEllipse(
                        in: CGRect(x: CGFloat(joint.x) - sDotR, y: CGFloat(joint.y) - sDotR, width: sDotR * 2, height: sDotR * 2)
                    )
                }
            }
        }
    }
}
