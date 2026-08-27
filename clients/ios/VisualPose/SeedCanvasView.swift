import UIKit

final class SeedCanvasView: UIView {
    var boxCommitted: (() -> Void)?

    private var frameImage: UIImage?
    private var origin = CGPoint.zero
    private var dragging = false
    private var rect = CGRect.zero

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
        origin = touch.location(in: self)
        dragging = true
        rect = CGRect(origin: origin, size: .zero)
        setNeedsDisplay()
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard dragging, let touch = touches.first else { return }
        let p = touch.location(in: self)
        rect = CGRect(x: origin.x, y: origin.y, width: p.x - origin.x, height: p.y - origin.y)
        setNeedsDisplay()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard dragging, let touch = touches.first else { return }
        dragging = false
        let p = touch.location(in: self)
        rect = CGRect(x: origin.x, y: origin.y, width: p.x - origin.x, height: p.y - origin.y)
        setNeedsDisplay()
        if boxNorm() != nil {
            boxCommitted?()
        }
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        dragging = false
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
