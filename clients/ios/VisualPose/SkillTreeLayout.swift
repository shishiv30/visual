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
}
