import Foundation

enum PlayerExport {
    static let shareTargets: [(String, String)] = [
        ("YouTube", "https://www.youtube.com/upload"),
        ("TikTok", "https://www.tiktok.com/upload"),
        ("X", "https://twitter.com/intent/tweet?text={text}"),
        ("Facebook", "https://www.facebook.com/sharer/sharer.php"),
        ("Weibo", "https://service.weibo.com/share/share.php?title={text}"),
        ("Bilibili", "https://member.bilibili.com/platform/upload/video/frame"),
    ]

    static func shareUrl(template: String, text: String) -> String {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-_*")
        let encoded = text.addingPercentEncoding(withAllowedCharacters: allowed) ?? text
        return template.replacingOccurrences(of: "{text}", with: encoded)
    }

    static func downloadFileName(displayName: String?, clipId: String?) -> String {
        let raw: String
        if let displayName, !displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            raw = displayName
        } else if let clipId, !clipId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            raw = clipId
        } else {
            raw = "overlay"
        }
        let stem = raw.replacingOccurrences(of: "[\\\\/:*?\"<>|]", with: "_", options: .regularExpression)
        if stem.lowercased().hasSuffix(".jpg") { return stem }
        return "\(stem).jpg"
    }
}
