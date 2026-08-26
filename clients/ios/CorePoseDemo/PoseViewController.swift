import AVFoundation
import MediaPipeTasksVision
import UIKit

final class PoseViewController: UIViewController, AVCaptureVideoDataOutputSampleBufferDelegate {
    private let preview = UIView()
    private let session = AVCaptureSession()
    private var landmarker: PoseLandmarker?
    private let ci = CIContext()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        view.addSubview(preview)
        preview.frame = view.bounds
        let task = Bundle.main.path(forResource: "pose_landmarker_full", ofType: "task")!
        let options = PoseLandmarkerOptions()
        options.baseOptions.modelAssetPath = task
        options.runningMode = .liveStream
        options.poseLandmarkerLiveStreamDelegate = self
        landmarker = try? PoseLandmarker(options: options)
        startCamera()
    }

    private func startCamera() {
        session.beginConfiguration()
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device) else { return }
        session.addInput(input)
        let out = AVCaptureVideoDataOutput()
        out.setSampleBufferDelegate(self, queue: DispatchQueue(label: "core.pose"))
        session.addOutput(out)
        session.commitConfiguration()
        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.frame = preview.bounds
        preview.layer.addSublayer(layer)
        DispatchQueue.global().async { self.session.startRunning() }
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixel = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let mpImage = try? MPImage(pixelBuffer: pixel)
        let ts = Int(CMSampleBufferGetPresentationTimeStamp(sampleBuffer).seconds * 1000)
        if let mpImage {
            try? landmarker?.detectAsync(image: mpImage, timestampInMilliseconds: ts)
        }
    }
}

extension PoseViewController: PoseLandmarkerLiveStreamDelegate {
    func poseLandmarker(
        _ poseLandmarker: PoseLandmarker,
        didFinishDetection result: PoseLandmarkerResult?,
        timestampInMilliseconds: Int,
        error: Error?
    ) {
        guard let result else { return }
        let poses = result.landmarks
        let w = Float(view.bounds.width)
        let h = Float(view.bounds.height)
        var flat = [Float](repeating: 0, count: poses.count * 33 * 4)
        var o = 0
        for person in poses {
            for i in 0..<33 {
                let lm = person[i]
                flat[o] = lm.x * w; o += 1
                flat[o] = lm.y * h; o += 1
                flat[o] = lm.z * w; o += 1
                flat[o] = lm.visibility ?? 1; o += 1
            }
        }
        flat.withUnsafeBufferPointer { ptr in
            guard let base = ptr.baseAddress else { return }
            if let cstr = core_map_from_blaze33(
                base, Int32(poses.count), Int32(view.bounds.width), Int32(view.bounds.height), 0, "gpu"
            ) {
                let json = String(cString: cstr)
                core_map_free(cstr)
                NSLog("%@", String(json.prefix(240)))
            }
        }
    }
}
