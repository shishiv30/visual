import Foundation

enum SkillTreeLayout {
    static let rowDp = 32
    static let dotRadiusDp: Float = 5
    static let lineXDp: Float = 8
    static let textGapDp: Float = 12
    static let dashDp: Float = 3
    static let gapDp: Float = 3
    static let current: UInt32 = 0xFFE1BEE7
    static let completed: UInt32 = 0xFFCE93D8
    static let pending: UInt32 = 0xFF757575
    static let line: UInt32 = 0xFFF5F5F5

    enum Kind {
        case current
        case completed
        case pending
    }

    static func currentIndex(_ nodes: [TreeNode]) -> Int {
        if let i = nodes.firstIndex(where: { $0.current }) { return i }
        return max(0, nodes.count - 1)
    }

    static func kind(index: Int, currentIndex: Int) -> Kind {
        if index == currentIndex { return .current }
        if index < currentIndex { return .completed }
        return .pending
    }

    static func color(_ kind: Kind) -> UInt32 {
        switch kind {
        case .current: return current
        case .completed: return completed
        case .pending: return pending
        }
    }

    static func heightPx(count: Int, density: Float) -> Int {
        let n = max(1, count)
        return Int((Float(n * rowDp) * density).rounded(.toNearestOrEven))
    }

    static func textX(_ density: Float) -> Float {
        (lineXDp + dotRadiusDp + textGapDp) * density
    }

    /// Contiguous runs of same-branch, non-piste rows (readability follow-up: the skill
    /// tree collapses side branches off the piste spine — app-spec §5 Ch 6). Mirrors
    /// desktop's `SkillTreeView._branch_groups` in clients/windows/ui/report_layout.py.
    /// The piste spine is never grouped — `order_tree_rows` never nests a branch inside
    /// another branch on desktop, and iOS's `treePath` likewise only ever attaches side
    /// branches one level off the spine, so a group's rows are always contiguous.
    static func branchGroups(_ nodes: [TreeNode]) -> [(branch: String, indices: [Int])] {
        var groups: [(String, [Int])] = []
        var branch: String?
        var indices: [Int] = []
        func flush() {
            if !indices.isEmpty { groups.append((branch ?? "piste", indices)) }
        }
        for (i, node) in nodes.enumerated() {
            let b = node.branch.isEmpty ? "piste" : node.branch
            if b == "piste" {
                flush()
                indices = []
                branch = nil
                continue
            }
            if b != branch {
                flush()
                branch = b
                indices = []
            }
            indices.append(i)
        }
        flush()
        return groups
    }

    /// English display key for a branch id — pass through `I18n.t` for the localized label.
    static func branchLabelKey(_ branch: String) -> String {
        switch branch {
        case "piste": return "Piste"
        case "moguls": return "Moguls"
        case "offpiste": return "Off-piste"
        case "park": return "Park"
        case "race": return "Race"
        default: return branch
        }
    }
}
