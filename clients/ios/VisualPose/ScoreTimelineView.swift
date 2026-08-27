import UIKit

final class ScoreTimelineView: UIView {
    var onSeek: ((Int) -> Void)?
    private var points: [FrameScorePoint] = []

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .clear
        isOpaque = false
        isUserInteractionEnabled = true
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        backgroundColor = .clear
        isOpaque = false
        isUserInteractionEnabled = true
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: 140)
    }

    func setPoints(_ next: [FrameScorePoint]) {
        points = next
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        let pad: CGFloat = 8
        let w = bounds.width - pad * 2
        let h = bounds.height - pad * 2
        ctx.setStrokeColor(UIColor(rgb: 0x6F6F6F).cgColor)
        ctx.setLineWidth(1)
        ctx.move(to: CGPoint(x: pad, y: pad))
        ctx.addLine(to: CGPoint(x: pad, y: pad + h))
        ctx.move(to: CGPoint(x: pad, y: pad + h))
        ctx.addLine(to: CGPoint(x: pad + w, y: pad + h))
        ctx.strokePath()
        if points.count < 2 || w <= 1 { return }
        let t0 = points.first!.tMs
        let t1 = max(points.last!.tMs, t0 + 1)
        let fill = UIBezierPath()
        let line = UIBezierPath()
        for (i, pt) in points.enumerated() {
            let x = pad + CGFloat((pt.tMs - t0) / (t1 - t0)) * w
            let y = pad + h - CGFloat(min(100, max(0, pt.score)) / 100) * h
            if i == 0 {
                line.move(to: CGPoint(x: x, y: y))
                fill.move(to: CGPoint(x: x, y: pad + h))
                fill.addLine(to: CGPoint(x: x, y: y))
            } else {
                line.addLine(to: CGPoint(x: x, y: y))
                fill.addLine(to: CGPoint(x: x, y: y))
            }
        }
        fill.addLine(to: CGPoint(x: pad + w, y: pad + h))
        fill.close()
        UIColor(rgb: 0xCE93D8, alpha: 0x55 / 255).setFill()
        fill.fill()
        Theme.lightPurple.setStroke()
        line.lineWidth = 3
        line.stroke()
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        if let touch = touches.first {
            seek(at: touch.location(in: self).x, commit: false)
        }
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        if let touch = touches.first {
            seek(at: touch.location(in: self).x, commit: true)
        }
    }

    private func seek(at x: CGFloat, commit: Bool) {
        let pad: CGFloat = 8
        guard let t0 = points.first?.tMs else { return }
        let t1 = max(points.last?.tMs ?? t0, t0 + 1)
        let frac = min(1, max(0, (x - pad) / max(1, bounds.width - pad * 2)))
        let tMs = t0 + Double(frac) * (t1 - t0)
        if commit {
            onSeek?(Int(tMs))
        }
    }
}
