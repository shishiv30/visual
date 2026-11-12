import UIKit

final class SeedCanvasView: UIView {
    var boxCommitted: (() -> Void)?

    /// newPending: finger down outside the box, not yet moved past slop - a plain tap must not
    /// wipe the existing box. corner: resize from the grabbed corner. move: drag the whole box.
    private enum Mode { case none, newPending, new, corner, move }

    private let slop: CGFloat = 8
    private let cornerHit: CGFloat = 32
    private let knobR: CGFloat = 5
    private let haptic = UISelectionFeedbackGenerator()

    private var frameImage: UIImage?
    private var origin = CGPoint.zero
    private var mode = Mode.none
    private var rect = CGRect.zero
    private var startRect = CGRect.zero
    private var anchor = CGPoint.zero
    private var grab = CGPoint.zero

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = UIColor(rgb: 0x111111)
        isUserInteractionEnabled = true
        isMultipleTouchEnabled = false
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        backgroundColor = UIColor(rgb: 0x111111)
    }

    override var intrinsicContentSize: CGSize {
        let width = bounds.width > 0 ? bounds.width : UIScreen.main.bounds.width - Theme.pageInset * 2
        return CGSize(width: UIView.noIntrinsicMetric, height: canvasHeight(for: width))
    }

    /// Whether the current frame already has `size` (a new size means a relayout / box re-place).
    func hasFrameSize(_ size: CGSize) -> Bool {
        frameImage?.size == size
    }

    func setFrame(_ image: UIImage?) {
        let relayout = frameImage?.size != image?.size
        frameImage = image
        if relayout {
            invalidateIntrinsicContentSize()
            superview?.setNeedsLayout()
        }
        setNeedsDisplay()
    }

    func setBoxNorm(_ box: NormBox?) {
        guard let box, let bmp = frameImage, bounds.width >= 2, bounds.height >= 2 else {
            rect = .zero
            setNeedsDisplay()
            return
        }
        let (l, t) = OverlayMath.mapContain(
            x: box.x1 * Float(bmp.size.width),
            y: box.y1 * Float(bmp.size.height),
            srcW: Int(bmp.size.width),
            srcH: Int(bmp.size.height),
            viewW: Int(bounds.width),
            viewH: Int(bounds.height)
        )
        let (r, b) = OverlayMath.mapContain(
            x: box.x2 * Float(bmp.size.width),
            y: box.y2 * Float(bmp.size.height),
            srcW: Int(bmp.size.width),
            srcH: Int(bmp.size.height),
            viewW: Int(bounds.width),
            viewH: Int(bounds.height)
        )
        rect = CGRect(x: CGFloat(l), y: CGFloat(t), width: CGFloat(r - l), height: CGFloat(b - t))
        setNeedsDisplay()
    }

    func boxNorm() -> NormBox? {
        guard let bmp = frameImage, bounds.width >= 2, bounds.height >= 2 else { return nil }
        let n = sorted(rect)
        if n.width < 8 || n.height < 8 {
            return nil
        }
        let (x1, y1) = OverlayMath.unmapContain(
            x: Float(n.minX), y: Float(n.minY),
            srcW: Int(bmp.size.width), srcH: Int(bmp.size.height),
            viewW: Int(bounds.width), viewH: Int(bounds.height)
        )
        let (x2, y2) = OverlayMath.unmapContain(
            x: Float(n.maxX), y: Float(n.maxY),
            srcW: Int(bmp.size.width), srcH: Int(bmp.size.height),
            viewW: Int(bounds.width), viewH: Int(bounds.height)
        )
        let nx1 = min(x1, x2) / Float(bmp.size.width)
        let ny1 = min(y1, y2) / Float(bmp.size.height)
        let nx2 = max(x1, x2) / Float(bmp.size.width)
        let ny2 = max(y1, y2) / Float(bmp.size.height)
        if nx2 - nx1 < 0.02 || ny2 - ny1 < 0.02 {
            return nil
        }
        return NormBox(
            x1: min(max(nx1, 0), 1),
            y1: min(max(ny1, 0), 1),
            x2: min(max(nx2, 0), 1),
            y2: min(max(ny2, 0), 1)
        )
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        let p = touch.location(in: self)
        origin = p
        let n = sorted(rect)
        startRect = n
        mode = .newPending
        guard n.width >= 8, n.height >= 8 else { return }
        if let corner = nearestCorner(n, p) {
            // Resize: the opposite corner stays put; keep the finger's offset to the corner so
            // it does not jump under the fingertip.
            mode = .corner
            anchor = CGPoint(x: corner.x == n.minX ? n.maxX : n.minX, y: corner.y == n.minY ? n.maxY : n.minY)
            grab = CGPoint(x: corner.x - p.x, y: corner.y - p.y)
            haptic.selectionChanged()
        } else if n.contains(p) {
            mode = .move
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard mode != .none, let touch = touches.first else { return }
        let p = touch.location(in: self)
        if mode == .newPending {
            if hypot(p.x - origin.x, p.y - origin.y) <= slop { return }
            mode = .new
        }
        applyDrag(p)
        setNeedsDisplay()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        let was = mode
        mode = .none
        // A tap: keep whatever box is there.
        guard was != .none, was != .newPending else { return }
        mode = was
        applyDrag(touch.location(in: self))
        mode = .none
        if boxNorm() != nil {
            rect = sorted(rect)
            boxCommitted?()
        } else {
            // Too small to be a person box: restore instead of leaving a stray sliver.
            rect = startRect
        }
        setNeedsDisplay()
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        if mode != .none, mode != .newPending {
            rect = startRect
            setNeedsDisplay()
        }
        mode = .none
    }

    private func applyDrag(_ p: CGPoint) {
        let img = imageRect()
        func cx(_ v: CGFloat) -> CGFloat { min(max(v, img.minX), img.maxX) }
        func cy(_ v: CGFloat) -> CGFloat { min(max(v, img.minY), img.maxY) }
        switch mode {
        case .new:
            let a = CGPoint(x: cx(origin.x), y: cy(origin.y))
            rect = CGRect(x: a.x, y: a.y, width: cx(p.x) - a.x, height: cy(p.y) - a.y)
        case .corner:
            rect = CGRect(x: anchor.x, y: anchor.y, width: cx(p.x + grab.x) - anchor.x, height: cy(p.y + grab.y) - anchor.y)
        case .move:
            let w = startRect.width
            let h = startRect.height
            let l = min(max(startRect.minX + p.x - origin.x, img.minX), max(img.minX, img.maxX - w))
            let t = min(max(startRect.minY + p.y - origin.y, img.minY), max(img.minY, img.maxY - h))
            rect = CGRect(x: l, y: t, width: w, height: h)
        default:
            break
        }
    }

    /// Corner of `n` within reach of `p`, nearest first.
    private func nearestCorner(_ n: CGRect, _ p: CGPoint) -> CGPoint? {
        let corners = [
            CGPoint(x: n.minX, y: n.minY), CGPoint(x: n.maxX, y: n.minY),
            CGPoint(x: n.maxX, y: n.maxY), CGPoint(x: n.minX, y: n.maxY),
        ]
        // Small boxes: shrink the reach so the inside stays grabbable for moving.
        let reach = min(cornerHit, min(n.width, n.height) / 3 + 12)
        let hits = corners
            .map { (point: $0, dist: hypot($0.x - p.x, $0.y - p.y)) }
            .filter { $0.dist <= reach }
        return hits.min { $0.dist < $1.dist }?.point
    }

    /// On-screen rectangle of the letterboxed frame; the whole view when there is no frame.
    private func imageRect() -> CGRect {
        guard let bmp = frameImage else { return bounds }
        let box = OverlayMath.contain(
            srcW: Int(bmp.size.width), srcH: Int(bmp.size.height),
            viewW: Int(bounds.width), viewH: Int(bounds.height)
        )
        return CGRect(
            x: CGFloat(box.dx),
            y: CGFloat(box.dy),
            width: bmp.size.width * CGFloat(box.scale),
            height: bmp.size.height * CGFloat(box.scale)
        )
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        ctx.setFillColor(UIColor(rgb: 0x111111).cgColor)
        ctx.fill(bounds)
        if let bmp = frameImage, bounds.width > 0, bounds.height > 0 {
            let box = OverlayMath.contain(
                srcW: Int(bmp.size.width), srcH: Int(bmp.size.height),
                viewW: Int(bounds.width), viewH: Int(bounds.height)
            )
            let dest = CGRect(
                x: CGFloat(box.dx),
                y: CGFloat(box.dy),
                width: CGFloat(bmp.size.width) * CGFloat(box.scale),
                height: CGFloat(bmp.size.height) * CGFloat(box.scale)
            )
            bmp.draw(in: dest)
        }
        let n = sorted(self.rect)
        if n.width >= 2, n.height >= 2 {
            ctx.setStrokeColor(Theme.bbox.cgColor)
            ctx.setLineWidth(2)
            ctx.stroke(n)
            if mode != .new {
                // Corner knobs signal that the box can be resized / moved, not only redrawn.
                ctx.setFillColor(Theme.bbox.cgColor)
                for c in [
                    CGPoint(x: n.minX, y: n.minY), CGPoint(x: n.maxX, y: n.minY),
                    CGPoint(x: n.maxX, y: n.maxY), CGPoint(x: n.minX, y: n.maxY),
                ] {
                    ctx.fillEllipse(in: CGRect(x: c.x - knobR, y: c.y - knobR, width: knobR * 2, height: knobR * 2))
                }
            }
        }
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        invalidateIntrinsicContentSize()
    }

    private func canvasHeight(for width: CGFloat) -> CGFloat {
        let maxH: CGFloat = 360
        let minH: CGFloat = 160
        let aspect: CGFloat
        if let bmp = frameImage, bmp.size.width > 0 {
            aspect = bmp.size.height / bmp.size.width
        } else {
            aspect = 9 / 16
        }
        return min(maxH, max(minH, width * aspect))
    }

    private func sorted(_ src: CGRect) -> CGRect {
        CGRect(
            x: min(src.minX, src.maxX),
            y: min(src.minY, src.maxY),
            width: abs(src.width),
            height: abs(src.height)
        )
    }
}
