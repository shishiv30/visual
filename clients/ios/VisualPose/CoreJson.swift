import Foundation

enum CoreJson {
    static func poses(_ json: String) -> [CocoPose] {
        guard let root = Json.object(from: json), !hadError(root) else { return [] }
        guard let arr = Json.optArray(root, "poses") else { return [] }
        var out: [CocoPose] = []
        for item in arr {
            guard let poseObj = item as? [String: Any],
                  let kps = Json.optArray(poseObj, "keypoints")
            else { continue }
            var points: [CocoKeypoint] = []
            for kpItem in kps {
                guard let kp = kpItem as? [String: Any] else { continue }
                points.append(
                    CocoKeypoint(
                        x: Float(Json.optDouble(kp, "x", 0)),
                        y: Float(Json.optDouble(kp, "y", 0)),
                        confidence: Float(Json.optDouble(kp, "confidence", 0))
                    )
                )
            }
            if !points.isEmpty {
                out.append(CocoPose(keypoints: points))
            }
        }
        return out
    }

    static func bboxes(_ json: String) -> [BBox] {
        guard let root = Json.object(from: json), !hadError(root) else { return [] }
        guard let arr = Json.optArray(root, "detections") else { return [] }
        var out: [BBox] = []
        for item in arr {
            guard let node = item as? [String: Any],
                  let box = Json.optArray(node, "bbox_xyxy"),
                  box.count >= 4,
                  let x1 = Json.number(box[0]),
                  let y1 = Json.number(box[1]),
                  let x2 = Json.number(box[2]),
                  let y2 = Json.number(box[3])
            else { continue }
            out.append(BBox(x1: Float(x1), y1: Float(y1), x2: Float(x2), y2: Float(y2)))
        }
        return out
    }

    private static func hadError(_ root: [String: Any]) -> Bool {
        !Json.isNull(root, "error")
    }
}
