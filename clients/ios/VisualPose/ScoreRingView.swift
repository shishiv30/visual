import UIKit

final class ScoreRingView: UIView {
    private var score: Double? = 0
    private var caption = ""
    private var ringColor = Theme.title

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .clear
        isOpaque = false
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        backgroundColor = .clear
        isOpaque = false
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: 148)
    }

    func setScore(_ next: Double?, label: String, ringColor: UIColor) {
        score = next
        caption = label
        self.ringColor = ringColor
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        let stroke: CGFloat = 10
        let pad = stroke + 8
        let ringSize = min(bounds.width - pad * 2, bounds.height - 36)
        let cx = bounds.width / 2
        let top: CGFloat = 8
        let oval = CGRect(x: cx - ringSize / 2, y: top, width: ringSize, height: ringSize)
        let value = score ?? 0
        let frac = CGFloat(min(1, max(0, value / 100)))
        let zeroRing = score == nil || frac <= 0
        ctx.setLineWidth(stroke)
        ctx.setLineCap(.round)
        ctx.setStrokeColor((zeroRing ? Theme.title : Theme.ringTrack).cgColor)
        ctx.strokeEllipse(in: oval)
        if !zeroRing {
            ctx.setStrokeColor(ringColor.cgColor)
            ctx.addArc(
                center: CGPoint(x: oval.midX, y: oval.midY),
                radius: ringSize / 2,
                startAngle: -.pi / 2,
                endAngle: -.pi / 2 + 2 * .pi * frac,
                clockwise: false
            )
            ctx.strokePath()
        }
        let text = score == nil ? "—" : "\(Int(score!))"
        let valueFont = UIFont.systemFont(ofSize: 22, weight: .regular)
        let valueAttrs: [NSAttributedString.Key: Any] = [
            .font: valueFont,
            .foregroundColor: Theme.paper,
        ]
        let textSize = (text as NSString).size(withAttributes: valueAttrs)
        (text as NSString).draw(
            at: CGPoint(x: cx - textSize.width / 2, y: oval.midY - textSize.height / 2),
            withAttributes: valueAttrs
        )
        let labelFont = UIFont.systemFont(ofSize: 12)
        let labelAttrs: [NSAttributedString.Key: Any] = [
            .font: labelFont,
            .foregroundColor: Theme.title,
        ]
        let lines = wrap(caption, maxWidth: bounds.width - 16, font: labelFont)
        var y = oval.maxY + 16
        for line in lines.prefix(2) {
            let w = (line as NSString).size(withAttributes: labelAttrs).width
            (line as NSString).draw(at: CGPoint(x: cx - w / 2, y: y), withAttributes: labelAttrs)
            y += 14
        }
    }

    private func wrap(_ text: String, maxWidth: CGFloat, font: UIFont) -> [String] {
        if text.isEmpty { return [] }
        let words = text.split(separator: " ").map(String.init)
        var lines: [String] = []
        var cur = ""
        for word in words {
            let next = cur.isEmpty ? word : "\(cur) \(word)"
            let width = (next as NSString).size(withAttributes: [.font: font]).width
            if width > maxWidth, !cur.isEmpty {
                lines.append(cur)
                cur = word
            } else {
                cur = next
            }
        }
        if !cur.isEmpty { lines.append(cur) }
        return lines
    }
}
