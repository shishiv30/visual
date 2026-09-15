import UIKit

/// Vertical skill-tree list with a white dashed spine (see clients/ios/README.md).
///
/// Rows are real subviews (not one painted canvas) so side branches can be collapsed
/// behind a tappable disclosure row — readability follow-up, app-spec §5 Ch 6 / design
/// doc §8. The piste spine (`TreeNode.branch == "piste"`) is always fully shown; only
/// contiguous runs of a single non-piste branch collapse, defaulting to collapsed except
/// the branch holding the `current` node.
final class SkillTreeView: UIView {
    private var nodes: [TreeNode] = []
    private var expandedGroups: Set<Int> = []
    private var hasDefaultExpansion = false
    private var groups: [(branch: String, indices: [Int])] = []
    private var groupRows: [Int: [UIView]] = [:]
    private var disclosureButtons: [Int: UIButton] = [:]

    private let spine = SkillTreeSpineView()
    private let stack = UIStackView()

    override init(frame: CGRect) {
        super.init(frame: frame)
        setup()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setup()
    }

    private func setup() {
        backgroundColor = .clear
        isOpaque = false
        spine.translatesAutoresizingMaskIntoConstraints = false
        addSubview(spine)
        stack.axis = .vertical
        stack.spacing = 0
        stack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(stack)
        NSLayoutConstraint.activate([
            spine.topAnchor.constraint(equalTo: topAnchor),
            spine.leadingAnchor.constraint(equalTo: leadingAnchor),
            spine.trailingAnchor.constraint(equalTo: trailingAnchor),
            spine.bottomAnchor.constraint(equalTo: bottomAnchor),
            stack.topAnchor.constraint(equalTo: topAnchor),
            stack.leadingAnchor.constraint(equalTo: leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: trailingAnchor),
            stack.bottomAnchor.constraint(equalTo: bottomAnchor),
        ])
    }

    func setRoute(_ next: [TreeNode]) {
        nodes = next
        hasDefaultExpansion = false
        expandedGroups = []
        rebuild()
    }

    private func rebuild() {
        stack.arrangedSubviews.forEach {
            stack.removeArrangedSubview($0)
            $0.removeFromSuperview()
        }
        groupRows = [:]
        disclosureButtons = [:]
        groups = []
        guard !nodes.isEmpty else {
            spine.rowCount = 0
            let label = UILabel()
            label.text = I18n.t("—")
            label.textColor = argb(SkillTreeLayout.pending)
            label.font = .systemFont(ofSize: 16)
            stack.addArrangedSubview(label)
            return
        }

        let currentI = SkillTreeLayout.currentIndex(nodes)
        groups = SkillTreeLayout.branchGroups(nodes)
        if !hasDefaultExpansion {
            hasDefaultExpansion = true
            // Default: only the branch containing the `current` node starts expanded.
            expandedGroups = Set(groups.enumerated().compactMap { gi, g in
                g.indices.contains(currentI) ? gi : nil
            })
        }

        var groupHeaderAt: [Int: Int] = [:] // node index -> group index, first row only
        var groupOfIndex: [Int: Int] = [:] // node index -> group index, every row
        for (gi, g) in groups.enumerated() {
            if let first = g.indices.first { groupHeaderAt[first] = gi }
            for idx in g.indices { groupOfIndex[idx] = gi }
        }

        // Every row is built once and kept as an arranged subview; toggling a
        // branch flips `isHidden` on its rows instead of tearing down and
        // rebuilding the whole tree on every tap (a stack view collapses
        // hidden arranged subviews out of layout automatically).
        for (i, node) in nodes.enumerated() {
            if let gi = groupHeaderAt[i] {
                let (branch, indices) = groups[gi]
                let button = disclosureRow(branch: branch, count: indices.count, groupIndex: gi)
                disclosureButtons[gi] = button
                stack.addArrangedSubview(button)
            }
            let gi = groupOfIndex[i]
            let kind = SkillTreeLayout.kind(index: i, currentIndex: currentI)
            let indent = gi != nil ? 1 : 0
            let row = nodeRow(node, kind: kind, indent: indent)
            if let gi {
                row.isHidden = !expandedGroups.contains(gi)
                groupRows[gi, default: []].append(row)
            }
            stack.addArrangedSubview(row)
        }
        updateSpineRowCount()
    }

    private func updateSpineRowCount() {
        spine.rowCount = stack.arrangedSubviews.filter { !$0.isHidden }.count
    }

    private func disclosureRow(branch: String, count: Int, groupIndex: Int) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitleColor(Theme.title, for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 15)
        button.titleLabel?.numberOfLines = 1
        button.contentHorizontalAlignment = .left
        button.contentEdgeInsets = UIEdgeInsets(
            top: 0, left: CGFloat(SkillTreeLayout.textX(1)), bottom: 0, right: 0
        )
        button.heightAnchor.constraint(equalToConstant: CGFloat(SkillTreeLayout.rowDp)).isActive = true
        button.addAction(UIAction { [weak self] _ in self?.toggleGroup(groupIndex) }, for: .touchUpInside)
        updateDisclosureTitle(button, branch: branch, count: count, expanded: expandedGroups.contains(groupIndex))
        return button
    }

    private func updateDisclosureTitle(_ button: UIButton, branch: String, count: Int, expanded: Bool) {
        let label = I18n.t(SkillTreeLayout.branchLabelKey(branch))
        let title = "\(expanded ? "▾" : "▸") \(label) · \(I18n.t("{n} stages", vars: ["n": String(count)]))"
        button.setTitle(title, for: .normal)
    }

    private func toggleGroup(_ groupIndex: Int) {
        let expanded: Bool
        if expandedGroups.contains(groupIndex) {
            expandedGroups.remove(groupIndex)
            expanded = false
        } else {
            expandedGroups.insert(groupIndex)
            expanded = true
        }
        for row in groupRows[groupIndex] ?? [] {
            row.isHidden = !expanded
        }
        if groupIndex < groups.count, let button = disclosureButtons[groupIndex] {
            let (branch, indices) = groups[groupIndex]
            updateDisclosureTitle(button, branch: branch, count: indices.count, expanded: expanded)
        }
        updateSpineRowCount()
    }

    private func nodeRow(_ node: TreeNode, kind: SkillTreeLayout.Kind, indent: Int) -> UIView {
        let row = UIStackView()
        row.axis = .horizontal
        row.alignment = .center
        row.spacing = CGFloat(SkillTreeLayout.textGapDp)
        row.isLayoutMarginsRelativeArrangement = true
        row.layoutMargins = UIEdgeInsets(
            top: 0, left: CGFloat(SkillTreeLayout.lineXDp) + CGFloat(indent) * 20, bottom: 0, right: 0
        )
        row.heightAnchor.constraint(equalToConstant: CGFloat(SkillTreeLayout.rowDp)).isActive = true

        let color = argb(SkillTreeLayout.color(kind))
        let r = CGFloat(SkillTreeLayout.dotRadiusDp)
        let dot = UIView()
        dot.translatesAutoresizingMaskIntoConstraints = false
        dot.widthAnchor.constraint(equalToConstant: r * 2).isActive = true
        dot.heightAnchor.constraint(equalToConstant: r * 2).isActive = true
        dot.layer.cornerRadius = r
        if kind == .pending {
            dot.backgroundColor = .clear
            dot.layer.borderWidth = 1
            dot.layer.borderColor = color.cgColor
        } else {
            dot.backgroundColor = color
        }
        row.addArrangedSubview(dot)

        let text = UILabel()
        text.text = node.name
        text.textColor = color
        text.font = kind == .pending ? .systemFont(ofSize: 16) : .boldSystemFont(ofSize: 16)
        text.numberOfLines = 1
        row.addArrangedSubview(text)
        return row
    }

    private func argb(_ value: UInt32) -> UIColor {
        UIColor(rgb: value & 0x00FFFFFF)
    }
}

/// Paints the continuous white dashed spine behind `SkillTreeView`'s rows. The piste
/// column runs the full height of the tree regardless of which side branches are
/// expanded, since the first and last rendered rows are always piste stages.
private final class SkillTreeSpineView: UIView {
    var rowCount: Int = 0 {
        didSet { setNeedsDisplay() }
    }

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

    override func draw(_ rect: CGRect) {
        guard rowCount > 1, let ctx = UIGraphicsGetCurrentContext() else { return }
        let cx = CGFloat(SkillTreeLayout.lineXDp)
        let row = CGFloat(SkillTreeLayout.rowDp)
        ctx.setStrokeColor(UIColor(rgb: SkillTreeLayout.line & 0x00FFFFFF).cgColor)
        ctx.setLineWidth(1)
        ctx.setLineDash(phase: 0, lengths: [CGFloat(SkillTreeLayout.dashDp), CGFloat(SkillTreeLayout.gapDp)])
        ctx.move(to: CGPoint(x: cx, y: row / 2))
        ctx.addLine(to: CGPoint(x: cx, y: bounds.height - row / 2))
        ctx.strokePath()
    }
}
