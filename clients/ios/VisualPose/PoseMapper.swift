import Foundation
import UIKit

protocol PoseLandmarkPoint {
    var x: Float { get }
    var y: Float { get }
    var z: Float { get }
    var visibility: Float? { get }
}

struct LandmarkXYZ: PoseLandmarkPoint {
    var x: Float
    var y: Float
    var z: Float
    var visibility: Float?
}

protocol PoseMarker: AnyObject {
    func detect(_ image: UIImage) -> [[any PoseLandmarkPoint]]
    func detectForVideo(_ image: UIImage, timestampMs: Int) -> [[any PoseLandmarkPoint]]
}

struct MappedPeople {
    var poses: [CocoPose]
    var blazePeople: [[BlazeJoint]]
    var bboxes: [BBox]
}

enum PoseMapper {
    static func fromLandmarks(
        _ poses: [[any PoseLandmarkPoint]],
        width: Int,
        height: Int,
        device: String
    ) -> MappedPeople {
        let w = Float(max(width, 1))
        let h = Float(max(height, 1))
        let n = poses.count
        var flat = [Float](repeating: 0, count: n * 33 * 4)
        var blazePeople: [[BlazeJoint]] = []
        var o = 0
        for person in poses {
            var joints: [BlazeJoint] = []
            joints.reserveCapacity(33)
            for i in 0..<33 {
                if i >= person.count {
                    joints.append(BlazeJoint(x: 0, y: 0, z: 0, confidence: 0))
                    o += 4
                    continue
                }
                let lm = person[i]
                let x = lm.x * w
                let y = lm.y * h
                let z = lm.z * w
                let vis = lm.visibility ?? 1
                joints.append(BlazeJoint(x: x, y: y, z: z, confidence: vis))
                flat[o] = x; o += 1
                flat[o] = y; o += 1
                flat[o] = z; o += 1
                flat[o] = vis; o += 1
            }
            blazePeople.append(joints)
        }
        let json = CoreMap.fromBlaze33(
            xyzVis: flat,
            numPeople: n,
            width: max(width, 1),
            height: max(height, 1),
            latencyMs: 0,
            device: device
        )
        return MappedPeople(
            poses: CoreJson.poses(json),
            blazePeople: blazePeople,
            bboxes: CoreJson.bboxes(json)
        )
    }
}
