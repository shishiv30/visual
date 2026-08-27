import Foundation

enum I18n {
    static let `default` = "en"
    static let supported = ["en", "es", "zh", "ko", "ja", "fr", "de", "it", "pt"]
    static let labels: [(String, String)] = [
        ("en", "English"),
        ("es", "Español"),
        ("zh", "中文"),
        ("ko", "한국어"),
        ("ja", "日本語"),
        ("fr", "Français"),
        ("de", "Deutsch"),
        ("it", "Italiano"),
        ("pt", "Português"),
    ]

    private static let langKey = "language"
    private static var catalog: [String: [String: String]] = [:]
    private static var lang: String = `default`

    static func language() -> String { lang }

    static func initCatalog(json: String, storedLang: String?) {
        catalog = loadCatalogJson(json)
        if let storedLang, supported.contains(storedLang) {
            lang = storedLang
        } else {
            lang = UserDefaults.standard.string(forKey: langKey).flatMap { supported.contains($0) ? $0 : nil } ?? `default`
        }
    }

    static func setLanguage(_ code: String) {
        lang = supported.contains(code) ? code : `default`
        UserDefaults.standard.set(lang, forKey: langKey)
    }

    static func t(_ key: String, vars: [String: String] = [:], lang code: String? = nil) -> String {
        let use = code ?? lang
        let raw: String
        if use == `default` {
            raw = key
        } else {
            raw = catalog[key]?[use] ?? key
        }
        return interpolate(raw, vars: vars)
    }

    static func loadCatalogJson(_ json: String) -> [String: [String: String]] {
        guard let data = json.data(using: .utf8),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let strings = root["strings"] as? [String: Any]
        else { return [:] }
        var out: [String: [String: String]] = [:]
        for (key, value) in strings {
            guard let node = value as? [String: Any] else { continue }
            var langs: [String: String] = [:]
            for (code, text) in node {
                if let text = text as? String { langs[code] = text }
            }
            out[key] = langs
        }
        return out
    }

    static func interpolate(_ template: String, vars: [String: String]) -> String {
        var out = template
        for (name, value) in vars {
            out = out.replacingOccurrences(of: "{\(name)}", with: value)
            if let regex = try? NSRegularExpression(pattern: "\\{\(NSRegularExpression.escapedPattern(for: name)):[^}]+\\}") {
                out = regex.stringByReplacingMatches(
                    in: out,
                    range: NSRange(out.startIndex..., in: out),
                    withTemplate: NSRegularExpression.escapedTemplate(for: value)
                )
            }
        }
        return out
    }
}
