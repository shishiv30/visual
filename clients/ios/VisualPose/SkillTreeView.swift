import UIKit

final class SkillTreeView: UIView {
    private var nodes: [TreeNode] = []

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

    func setRoute(_ next: [TreeNode]) {
        nodes = next
        invalidateIntrinsicContentSize()
        setNeedsDisplay()
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: SkillTreeLayout.heightPx(count: nodes.count, density: 1))
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        let density: CGFloat = 1
        let textFont = UIFont.systemFont(ofSize: 16)
        let n = nodes.count
        if n == 0 {
            let attrs: [NSAttributedString.Key: Any] = [
                .font: textFont,
                .foregroundColor: SkillTreeLayout.pending,
            ]
            let y = SkillTreeLayout.rowDp * density / 2
            (I18n.t("—") as NSString).draw(at: CGPoint(x: SkillTreeLayout.textX(density: density), y: y - 10), withAttributes: attrs)
            return
        }
        let currentI = SkillTreeLayout.currentIndex(nodes)
        let cx = SkillTreeLayout.lineXDp * density
        let row = SkillTreeLayout.rowDp * density
        let r = SkillTreeLayout.dotRadiusDp * density
        if n > 1 {
            ctx.setStrokeColor(SkillTreeLayout.line.cgColor)
            ctx.setLineWidth(max(1, density))
            ctx.setLineDash(phase: 0, lengths: [SkillTreeLayout.dashDp * density, SkillTreeLayout.gapDp * density])
            ctx.move(to: CGPoint(x: cx, y: row / 2))
            ctx.addLine(to: CGPoint(x: cx, y: CGFloat(n - 1) * row + row / 2))
            ctx.strokePath()
            ctx.setLineDash(phase: 0, lengths: [])
        }
        for (i, node) in nodes.enumerated() {
            let kind = SkillTreeLayout.kind(index: i, currentIndex: currentI)
            let color = SkillTreeLayout.color(kind)
            let cy = CGFloat(i) * row + row / 2
            if kind == .pending {
                ctx.setStrokeColor(color.cgColor)
                ctx.setLineWidth(max(1, density))
                ctx.strokeEllipse(in: CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2))
            } else {
                ctx.setFillColor(color.cgColor)
                ctx.fillEllipse(in: CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2))
            }
            let font = kind == .pending ? UIFont.systemFont(ofSize: 16) : UIFont.boldSystemFont(ofSize: 16)
            let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: color]
            let size = (node.name as NSString).size(withAttributes: attrs)
            (node.name as NSString).draw(
                at: CGPoint(x: SkillTreeLayout.textX(density: density), y: cy - size.height / 2),
                withAttributes: attrs
            )
        }
    }
}
