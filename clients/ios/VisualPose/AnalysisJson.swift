import Foundation

enum AnalysisJson {
    static func save(_ file: URL, clipId: String, frames: [PoseFrame]) {
        var arr: [[String: Any]] = []
        for frame in frames {
            let poses: [[String: Any]] = frame.poses.map { pose in
                [
                    "keypoints": pose.keypoints.map { kp -> [String: Any] in
                        [
                            "x": Double(kp.x),
                            "y": Double(kp.y),
                            "confidence": Double(kp.confidence),
                        ]
                    },
                ]
            }
            let blaze: [[String: Any]] = frame.blaze33.map { joint in
                [
                    "x": Double(joint.x),
                    "y": Double(joint.y),
                    "z": Double(joint.z),
                    "confidence": Double(joint.confidence),
                ]
            }
            var obj: [String: Any] = [
                "t_ms": frame.tMs,
                "width": frame.width,
                "height": frame.height,
                "poses": poses,
                "blaze33": blaze,
            ]
            if let box = frame.bbox {
                obj["bbox"] = [Double(box.x1), Double(box.y1), Double(box.x2), Double(box.y2)]
            } else {
                obj["bbox"] = NSNull()
            }
            arr.append(obj)
        }
        Json.write(file, ["clip_id": clipId, "frames": arr], pretty: false)
    }

    static func load(_ file: URL) -> [PoseFrame] {
        guard Json.isFile(file),
              let text = try? String(contentsOf: file, encoding: .utf8),
              let root = Json.object(from: text),
              let arr = Json.optArray(root, "frames")
        else { return [] }
        var frames: [PoseFrame] = []
        for item in arr {
            guard let obj = item as? [String: Any] else { continue }
            var poses: [CocoPose] = []
            for poseItem in Json.optArray(obj, "poses") ?? [] {
                guard let poseObj = poseItem as? [String: Any],
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
                    poses.append(CocoPose(keypoints: points))
                }
            }
            var blaze: [BlazeJoint] = []
            for jointItem in Json.optArray(obj, "blaze33") ?? [] {
                guard let joint = jointItem as? [String: Any] else { continue }
                blaze.append(
                    BlazeJoint(
                        x: Float(Json.optDouble(joint, "x", 0)),
                        y: Float(Json.optDouble(joint, "y", 0)),
                        z: Float(Json.optDouble(joint, "z", 0)),
                        confidence: Float(Json.optDouble(joint, "confidence", 0))
                    )
                )
            }
            let bbox: BBox?
            if let boxArr = Json.optArray(obj, "bbox"), boxArr.count >= 4,
               let x1 = Json.number(boxArr[0]),
               let y1 = Json.number(boxArr[1]),
               let x2 = Json.number(boxArr[2]),
               let y2 = Json.number(boxArr[3])
            {
                bbox = BBox(x1: Float(x1), y1: Float(y1), x2: Float(x2), y2: Float(y2))
            } else {
                bbox = nil
            }
            frames.append(
                PoseFrame(
                    tMs: Json.optInt64(obj, "t_ms"),
                    poses: poses,
                    width: max(Json.optInt(obj, "width", 1), 1),
                    height: max(Json.optInt(obj, "height", 1), 1),
                    blaze33: blaze,
                    bbox: bbox
                )
            )
        }
        return frames
    }

    static func toAssessFrames(_ frames: [PoseFrame]) -> [AssessFrame] {
        frames.map { AssessFrame(tMs: Double($0.tMs), blaze33: $0.blaze33) }
    }
}
