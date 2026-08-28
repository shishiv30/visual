import Foundation
import MediaPipeTasksVision
import UIKit

struct PoseLandmarkers {
    let video: any PoseMarker
    let crop: any PoseMarker

    func close() {}
}

enum PoseEngineError: Error {
    case landmarkerUnavailable
}

final class PoseEngine {
    private(set) var device = "cpu"

    func create(mode: RunningMode, numPoses: Int = 2) throws -> PoseLandmarker {
        let preferCpu = PoseEngine.isSimulator()
        let firstGpu = !preferCpu
        do {
            let marker = try build(gpu: firstGpu, mode: mode, numPoses: numPoses)
            device = firstGpu ? "gpu" : "cpu"
            return marker
        } catch {
            let secondGpu = !firstGpu
            let marker = try build(gpu: secondGpu, mode: mode, numPoses: numPoses)
            device = secondGpu ? "gpu" : "cpu"
            return marker
        }
    }

    func createPair() throws -> PoseLandmarkers {
        let video = try create(mode: .video, numPoses: 2)
        let crop = try create(mode: .image, numPoses: 1)
        return PoseLandmarkers(
            video: MediaPipeMarker(video),
            crop: MediaPipeMarker(crop)
        )
    }

    private func build(gpu: Bool, mode: RunningMode, numPoses: Int) throws -> PoseLandmarker {
        guard let task = Bundle.main.path(forResource: "pose_landmarker_full", ofType: "task") else {
            throw PoseEngineError.landmarkerUnavailable
        }
        let options = PoseLandmarkerOptions()
        options.baseOptions.modelAssetPath = task
        options.baseOptions.delegate = gpu ? .GPU : .CPU
        options.runningMode = mode
        options.numPoses = numPoses
        options.minPoseDetectionConfidence = 0.5
        options.minPosePresenceConfidence = 0.5
        options.minTrackingConfidence = 0.5
        return try PoseLandmarker(options: options)
    }

    static func isSimulator() -> Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }
}

final class MediaPipeMarker: PoseMarker {
    private let landmarker: PoseLandmarker

    init(_ landmarker: PoseLandmarker) {
        self.landmarker = landmarker
    }

    func detect(_ image: UIImage) -> [[any PoseLandmarkPoint]] {
        guard let mp = try? MPImage(uiImage: image),
              let result = try? landmarker.detect(image: mp)
        else { return [] }
        return Self.mapLandmarks(result)
    }

    func detectForVideo(_ image: UIImage, timestampMs: Int) -> [[any PoseLandmarkPoint]] {
        guard let mp = try? MPImage(uiImage: image),
              let result = try? landmarker.detect(videoFrame: mp, timestampInMilliseconds: timestampMs)
        else { return [] }
        return Self.mapLandmarks(result)
    }

    private static func mapLandmarks(_ result: PoseLandmarkerResult) -> [[any PoseLandmarkPoint]] {
        result.landmarks.map { person in
            person.map { lm in
                LandmarkXYZ(x: lm.x, y: lm.y, z: lm.z, visibility: lm.visibility?.floatValue)
            }
        }
    }
}
