import Foundation

enum CoreMap {
    static func fromBlaze33(
        xyzVis: [Float]?,
        numPeople: Int,
        width: Int,
        height: Int,
        latencyMs: Float,
        device: String
    ) -> String {
        func invoke(_ ptr: UnsafePointer<Float>?) -> String {
            guard let cstr = core_map_from_blaze33(
                ptr,
                Int32(numPeople),
                Int32(width),
                Int32(height),
                latencyMs,
                device
            ) else {
                return "{\"error\":{\"code\":\"INVALID_INPUT\"}}"
            }
            defer { core_map_free(cstr) }
            return String(cString: cstr)
        }
        if let data = xyzVis {
            return data.withUnsafeBufferPointer { invoke($0.baseAddress) }
        }
        return invoke(nil)
    }
}
