import Foundation

enum JsonError: Error {
    case missing(String)
}

enum Json {
    static func object(from text: String) -> [String: Any]? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return nil }
        return obj
    }

    static func stringify(_ obj: Any, pretty: Bool = false) -> String {
        let opts: JSONSerialization.WritingOptions = pretty ? [.prettyPrinted] : []
        guard JSONSerialization.isValidJSONObject(obj),
              let data = try? JSONSerialization.data(withJSONObject: obj, options: opts),
              let text = String(data: data, encoding: .utf8)
        else { return pretty ? "{\n}" : "{}" }
        return text
    }

    static func isNull(_ obj: [String: Any], _ key: String) -> Bool {
        guard let value = obj[key] else { return true }
        return value is NSNull
    }

    static func opt(_ obj: [String: Any], _ key: String) -> Any? {
        guard let value = obj[key], !(value is NSNull) else { return nil }
        return value
    }

    static func optString(_ obj: [String: Any], _ key: String, _ fallback: String = "") -> String {
        guard let value = opt(obj, key) else { return fallback }
        if let s = value as? String { return s }
        if let n = value as? NSNumber { return n.stringValue }
        return fallback
    }

    static func optInt(_ obj: [String: Any], _ key: String, _ fallback: Int = 0) -> Int {
        guard let value = opt(obj, key) else { return fallback }
        if let n = value as? NSNumber { return n.intValue }
        if let s = value as? String, let d = Double(s) { return Int(d) }
        return fallback
    }

    static func optInt64(_ obj: [String: Any], _ key: String, _ fallback: Int64 = 0) -> Int64 {
        guard let value = opt(obj, key) else { return fallback }
        if let n = value as? NSNumber { return n.int64Value }
        if let s = value as? String, let d = Double(s) { return Int64(d) }
        return fallback
    }

    static func optDouble(_ obj: [String: Any], _ key: String, _ fallback: Double = .nan) -> Double {
        guard let value = opt(obj, key) else { return fallback }
        if let n = value as? NSNumber { return n.doubleValue }
        if let s = value as? String, let d = Double(s) { return d }
        return fallback
    }

    static func optBool(_ obj: [String: Any], _ key: String, _ fallback: Bool = false) -> Bool {
        guard let value = opt(obj, key) else { return fallback }
        if let b = value as? Bool { return b }
        if let n = value as? NSNumber { return n.boolValue }
        return fallback
    }

    static func optObject(_ obj: [String: Any], _ key: String) -> [String: Any]? {
        opt(obj, key) as? [String: Any]
    }

    static func optArray(_ obj: [String: Any], _ key: String) -> [Any]? {
        opt(obj, key) as? [Any]
    }

    static func getString(_ obj: [String: Any], _ key: String) -> String {
        opt(obj, key) as? String ?? {
            preconditionFailure("missing \(key)")
        }()
    }

    static func getObject(_ obj: [String: Any], _ key: String) -> [String: Any] {
        opt(obj, key) as? [String: Any] ?? {
            preconditionFailure("missing \(key)")
        }()
    }

    static func getDouble(_ obj: [String: Any], _ key: String) -> Double {
        let value = optDouble(obj, key)
        if value.isNaN { preconditionFailure("missing \(key)") }
        return value
    }

    static func number(_ value: Any) -> Double? {
        if let n = value as? NSNumber { return n.doubleValue }
        if let d = value as? Double { return d }
        if let i = value as? Int { return Double(i) }
        if let f = value as? Float { return Double(f) }
        if let s = value as? String { return Double(s) }
        return nil
    }

    static func strList(_ arr: [Any]?) -> [String] {
        guard let arr else { return [] }
        return arr.map { item in
            if let s = item as? String { return s }
            if let n = item as? NSNumber { return n.stringValue }
            return ""
        }
    }

    static func isFile(_ url: URL) -> Bool {
        var isDir: ObjCBool = false
        let exists = FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir)
        return exists && !isDir.boolValue
    }

    static func isDirectory(_ url: URL) -> Bool {
        var isDir: ObjCBool = false
        let exists = FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir)
        return exists && isDir.boolValue
    }

    static func write(_ url: URL, _ obj: Any, pretty: Bool = false) {
        try? FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(), withIntermediateDirectories: true
        )
        try? stringify(obj, pretty: pretty).write(to: url, atomically: true, encoding: .utf8)
    }

    static func readObject(_ url: URL) -> [String: Any]? {
        guard isFile(url), let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        return object(from: text)
    }

    static func roundEven(_ value: Double) -> Double {
        value.rounded(.toNearestOrEven)
    }

    static func round1(_ value: Float) -> Float {
        Float((Double(value) * 10).rounded(.toNearestOrEven) / 10)
    }

    static func round1(_ value: Double) -> Double {
        (value * 10).rounded(.toNearestOrEven) / 10
    }
}
