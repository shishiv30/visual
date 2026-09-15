import AVFoundation
import Foundation
import UIKit

enum VideoPose {
    static let maxMs: Int64 = 120_000

    static func analyze(
        asset: AVAsset,
        markers: PoseLandmarkers,
        device: String,
        startMs: Int64 = 0,
        endMs: Int64 = maxMs,
        seeds: [SeedMark] = [],
        seedBox: NormBox? = nil,
        fpsIn: Double = 30,
        onProgress: (Int64, Int64) -> Void
    ) -> [PoseFrame] {
        let durationSec = CMTimeGetSeconds(asset.duration)
        let durationMs = durationSec.isFinite ? max(Int64(durationSec * 1000), 0) : 0
        let fps = fpsIn > 1.0 ? fpsIn : 30.0
        let lo = max(startMs, 0)
        let hi = max(min(endMs, min(durationMs, lo + maxMs)), lo)
        let timedSeeds = ClipRange.collectSeeds(seeds, seedBox: seedBox)
        let halfMs = ClipRange.halfMs(fps: fps)
        let stepMs = ClipRange.strideMs(fps: fps)
        let locator = PoseLocator(device: device)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.requestedTimeToleranceBefore = .zero
        generator.requestedTimeToleranceAfter = .zero
        var frames: [PoseFrame] = []
        var tMs = lo
        while tMs <= hi {
            onProgress(tMs - lo, max(hi - lo, 1))
            if let image = frameImage(generator, tMs: tMs) {
                frames.append(
                    locator.inferFrame(image, tMs: Double(tMs), seeds: timedSeeds, seedBox: seedBox, halfMs: halfMs, markers: markers)
                )
            }
            tMs += stepMs
        }
        return PoseTrack.fillLowScore(PoseTrack.stabilizeWeakJoints(frames))
    }

    static func analyzeBitmap(
        _ image: UIImage,
        markers: PoseLandmarkers,
        device: String,
        seeds: [SeedMark] = [],
        seedBox: NormBox? = nil
    ) -> [PoseFrame] {
        let locator = PoseLocator(device: device)
        let timed = ClipRange.collectSeeds(seeds, seedBox: seedBox)
        return PoseTrack.fillLowScore(
            PoseTrack.stabilizeWeakJoints(
                [locator.inferFrame(image, tMs: 0, seeds: timed, seedBox: seedBox, halfMs: 1e9, markers: markers)]
            )
        )
    }

    private static func frameImage(_ generator: AVAssetImageGenerator, tMs: Int64) -> UIImage? {
        let time = CMTime(value: tMs, timescale: 1000)
        var actual = CMTime.zero
        guard let cg = try? generator.copyCGImage(at: time, actualTime: &actual) else { return nil }
        return UIImage(cgImage: cg, scale: 1, orientation: .up)
    }
}

final class PoseLocator {
    private let device: String
    private var hist: [Float]?
    private var box: PixelBox?
    private var lastMapped: MappedPeople?
    private var lastTs: Int64 = -1

    init(device: String) {
        self.device = device
    }

    func inferFrame(
        _ image: UIImage,
        tMs: Double,
        seeds: [SeedMark],
        seedBox: NormBox?,
        halfMs: Double,
        markers: PoseLandmarkers
    ) -> PoseFrame {
        let w = PoseImage.pixelWidth(image)
        let h = PoseImage.pixelHeight(image)
        let pixels = PoseImage.argbPixels(image)
        let hit = ClipRange.seedAt(tMs: tMs, seeds: seeds, halfMs: halfMs)
        if let hit {
            box = PersonRoi.denormBox(hit.box, width: w, height: h)
            hist = PersonRoi.buildHist(pixels: pixels, width: w, height: h, box: box!)
        } else if hist == nil, let seedBox {
            box = PersonRoi.denormBox(seedBox, width: w, height: h)
            hist = PersonRoi.buildHist(pixels: pixels, width: w, height: h, box: box!)
        } else if let hist, let box {
            self.box = PersonRoi.search(pixels: pixels, width: w, height: h, hist: hist, prev: box)
        }
        let mapped = detect(image, tMs: Int64(tMs), roi: box, markers: markers)
        if !mapped.poses.isEmpty && !mapped.bboxes.isEmpty {
            let det = mapped.bboxes[0]
            box = PixelBox(x1: Double(det.x1), y1: Double(det.y1), x2: Double(det.x2), y2: Double(det.y2))
            let nextHist = PersonRoi.buildHist(pixels: pixels, width: w, height: h, box: box!)
            hist = hist.map { PersonRoi.blendHist($0, nextHist) } ?? nextHist
            lastMapped = mapped
        } else {
            lastMapped = nil
        }
        let pose = mapped.poses.first
        let blaze = mapped.blazePeople.first ?? []
        return PoseFrame(
            tMs: Int64(tMs),
            poses: pose.map { [$0] } ?? [],
            width: w,
            height: h,
            blaze33: blaze,
            bbox: mapped.bboxes.first
        )
    }

    private func detect(
        _ image: UIImage,
        tMs: Int64,
        roi: PixelBox?,
        markers: PoseLandmarkers
    ) -> MappedPeople {
        let w = PoseImage.pixelWidth(image)
        let h = PoseImage.pixelHeight(image)
        var mapped: MappedPeople?
        if let roi {
            let cropped = detectCrop(image, roi: roi, marker: markers.crop)
            let ok = PoseFilter.isPlausible(cropped, frameW: w, frameH: h) || !cropped.poses.isEmpty
            if ok && !PoseFilter.cropDisagreesWithPrev(lastMapped, cropped) {
                mapped = cropped
            }
        }
        if mapped == nil {
            mapped = detectFull(image, tMs: tMs, marker: markers.video)
            mapped = PoseFilter.pickPrimary(mapped!, prev: lastMapped?.bboxes.first)
            if !PoseFilter.isPlausible(mapped!, frameW: w, frameH: h) {
                let retryBox = mapped!.bboxes.first ?? lastMapped?.bboxes.first
                if let retryBox {
                    let retry = detectCrop(
                        image,
                        roi: PoseFilter.cropBoxForRetry(retryBox, frameW: w, frameH: h),
                        marker: markers.crop
                    )
                    let retryOk = PoseFilter.isPlausible(retry, frameW: w, frameH: h) || !retry.poses.isEmpty
                    if retryOk && !PoseFilter.cropDisagreesWithPrev(lastMapped, retry) {
                        mapped = retry
                    }
                }
                if !PoseFilter.isPlausible(mapped!, frameW: w, frameH: h) && mapped!.poses.isEmpty {
                    mapped = MappedPeople(poses: [], blazePeople: [], bboxes: [])
                }
            }
        }
        return PoseFilter.emaSmooth(lastMapped, mapped!)
    }

    private func detectCrop(_ src: UIImage, roi: PixelBox, marker: any PoseMarker) -> MappedPeople {
        let spec = PersonRoi.cropRect(roi, width: PoseImage.pixelWidth(src), height: PoseImage.pixelHeight(src))
        let srcW = PoseImage.pixelWidth(src)
        let srcH = PoseImage.pixelHeight(src)
        let cw = max(spec.x2 - spec.ox, 2)
        let ch = max(spec.y2 - spec.oy, 2)
        var crop = src
        if !(cw >= srcW - 1 && ch >= srcH - 1) {
            crop = PoseImage.cropped(src, ox: spec.ox, oy: spec.oy, width: cw, height: ch)
        }
        if spec.scale > 1.0 + 1e-6 {
            let sw = max(Int(Double(cw) * spec.scale), 2)
            let sh = max(Int(Double(ch) * spec.scale), 2)
            crop = PoseImage.scaled(crop, width: sw, height: sh)
        }
        let mapped = PoseMapper.fromLandmarks(
            marker.detect(crop),
            width: PoseImage.pixelWidth(crop),
            height: PoseImage.pixelHeight(crop),
            device: device
        )
        let picked = PoseFilter.pickPrimary(mapped, prev: lastMapped?.bboxes.first)
        return remap(picked, spec)
    }

    private func detectFull(_ src: UIImage, tMs: Int64, marker: any PoseMarker) -> MappedPeople {
        let ts = max(tMs, lastTs + 1)
        lastTs = ts
        return PoseMapper.fromLandmarks(
            marker.detectForVideo(src, timestampMs: Int(ts)),
            width: PoseImage.pixelWidth(src),
            height: PoseImage.pixelHeight(src),
            device: device
        )
    }

    private func remap(_ mapped: MappedPeople, _ spec: CropSpec) -> MappedPeople {
        func pt(_ x: Float, _ y: Float) -> (Float, Float) {
            let (nx, ny) = PersonRoi.remapPoint(x: Double(x), y: Double(y), ox: spec.ox, oy: spec.oy, scale: spec.scale)
            return (Float(nx), Float(ny))
        }
        let poses = mapped.poses.map { pose in
            CocoPose(
                keypoints: pose.keypoints.map { kp in
                    let (x, y) = pt(kp.x, kp.y)
                    return CocoKeypoint(x: x, y: y, confidence: kp.confidence)
                }
            )
        }
        let blaze = mapped.blazePeople.map { person in
            person.map { joint in
                let (x, y) = pt(joint.x, joint.y)
                return BlazeJoint(x: x, y: y, z: joint.z, confidence: joint.confidence)
            }
        }
        let boxes = mapped.bboxes.map { box in
            let (x1, y1) = pt(box.x1, box.y1)
            let (x2, y2) = pt(box.x2, box.y2)
            return BBox(x1: x1, y1: y1, x2: x2, y2: y2)
        }
        return MappedPeople(poses: poses, blazePeople: blaze, bboxes: boxes)
    }
}

enum PoseImage {
    static func pixelWidth(_ image: UIImage) -> Int {
        image.cgImage?.width ?? Int(image.size.width * image.scale)
    }

    static func pixelHeight(_ image: UIImage) -> Int {
        image.cgImage?.height ?? Int(image.size.height * image.scale)
    }

    static func argbPixels(_ image: UIImage) -> [UInt32] {
        guard let cg = image.cgImage else { return [] }
        let w = cg.width
        let h = cg.height
        var pixels = [UInt32](repeating: 0, count: w * h)
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        let info = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.premultipliedFirst.rawValue
        pixels.withUnsafeMutableBytes { raw in
            guard let ctx = CGContext(
                data: raw.baseAddress,
                width: w,
                height: h,
                bitsPerComponent: 8,
                bytesPerRow: w * 4,
                space: colorSpace,
                bitmapInfo: info
            ) else { return }
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
        }
        return pixels
    }

    static func cropped(_ image: UIImage, ox: Int, oy: Int, width: Int, height: Int) -> UIImage {
        guard let cg = image.cgImage,
              let part = cg.cropping(to: CGRect(x: ox, y: oy, width: width, height: height))
        else { return image }
        return UIImage(cgImage: part, scale: 1, orientation: .up)
    }

    static func scaled(_ image: UIImage, width: Int, height: Int) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: width, height: height), format: format)
        return renderer.image { _ in
            image.draw(in: CGRect(x: 0, y: 0, width: width, height: height))
        }
    }
}
