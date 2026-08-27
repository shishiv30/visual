import UIKit

enum Theme {
    static let surface = UIColor(rgb: 0x121212)
    static let card = UIColor(rgb: 0x1A2433)
    static let title = UIColor(rgb: 0x9E9E9E)
    static let paper = UIColor(rgb: 0xF5F5F5)
    static let ringTrack = UIColor(rgb: 0x2A3544)
    static let link = UIColor(rgb: 0x4FC3F7)
    static let deepPurple = UIColor(rgb: 0x5E35B1)
    static let lightPurple = UIColor(rgb: 0xCE93D8)
    static let currentTree = UIColor(rgb: 0xE1BEE7)
    static let watermelon = UIColor(rgb: 0xE94B6A)
    static let terrainBlack = UIColor(rgb: 0x000000)
    static let medalBeginner = UIColor(rgb: 0x43A047)
    static let medalIntermediate = UIColor(rgb: 0x1E88E5)
    static let medalAdvanced = UIColor(rgb: 0x8E24AA)
    static let medalElite = UIColor(rgb: 0xFFC107)
    static let bone = UIColor(rgb: 0xFFA500)
    static let joint = UIColor(rgb: 0xFF1744)
    static let bbox = UIColor(rgb: 0x00FF00)
    static let spaceChapter: CGFloat = 36
    static let spacePanel: CGFloat = 24
    static let spaceText: CGFloat = 16
    static let pageInset: CGFloat = 12
    static let reportInset: CGFloat = 8
    static let controlHeight: CGFloat = 32
    static let floatingBack: CGFloat = 44
    static let cardRadius: CGFloat = 10
}

extension UIColor {
    convenience init(rgb: UInt32, alpha: CGFloat = 1) {
        self.init(
            red: CGFloat((rgb >> 16) & 0xFF) / 255,
            green: CGFloat((rgb >> 8) & 0xFF) / 255,
            blue: CGFloat(rgb & 0xFF) / 255,
            alpha: alpha
        )
    }

    var argb: UInt32 {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        getRed(&r, green: &g, blue: &b, alpha: &a)
        return (UInt32(a * 255) << 24)
            | (UInt32(r * 255) << 16)
            | (UInt32(g * 255) << 8)
            | UInt32(b * 255)
    }
}

enum ReportTheme {
    static let spaceChapter = 36
    static let spacePanel = 24
    static let spaceText = 16
    static let pageInset = 12
    static let reportInset = 8

    static func scorePurple(_ score: Double?) -> UIColor {
        guard let score, score > 0 else { return Theme.title }
        let frac = min(1, max(0, score / 100))
        let r = 0x5E + Int(Double(0xCE - 0x5E) * frac)
        let g = 0x35 + Int(Double(0x93 - 0x35) * frac)
        let b = 0xB1 + Int(Double(0xD8 - 0xB1) * frac)
        return UIColor(rgb: UInt32(r << 16 | g << 8 | b))
    }

    static func medalColor(stageId: String) -> UIColor {
        switch stageId {
        case "pizza_glide", "pizza", "wedge_christie": return Theme.medalBeginner
        case "parallel", "skid_short", "carve_long", "switch": return Theme.medalIntermediate
        case "carve_medium", "mogul_absorb", "gates": return Theme.medalAdvanced
        case "carve_short", "mogul_fallline", "ollie", "park": return Theme.medalElite
        default: return Theme.medalIntermediate
        }
    }

    static func terrainDiamondColors(_ terrainId: String) -> [UIColor] {
        switch terrainId {
        case "green": return [UIColor(rgb: 0x2E7D32)]
        case "blue": return [UIColor(rgb: 0x1565C0)]
        case "red": return [UIColor(rgb: 0xC62828)]
        case "black", "mogul": return [Theme.terrainBlack]
        case "double_black", "black_double": return [Theme.terrainBlack, Theme.terrainBlack]
        case "park": return [UIColor(rgb: 0x8E24AA)]
        default: return [UIColor(rgb: 0x9E9E9E)]
        }
    }

    static func formatEvidenceMs(_ tMs: Double) -> String {
        let total = max(0, tMs / 1000)
        let minutes = Int(total) / 60
        let seconds = total - Double(minutes * 60)
        return String(format: "%d:%04.1f", minutes, seconds)
    }

    static func sortedKeypoints(_ items: [KeypointResult]) -> [KeypointResult] {
        items.sorted {
            let a = $0.status == .fail ? 0 : 1
            let b = $1.status == .fail ? 0 : 1
            if a != b { return a < b }
            return ($0.score ?? 101) < ($1.score ?? 101)
        }
    }
}
