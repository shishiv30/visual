import Foundation
import XCTest
@testable import VisualPose

final class OverlayMathTests: XCTestCase {
    func testContainLetterboxesWideView() {
        let box = OverlayMath.contain(srcW: 100, srcH: 100, viewW: 200, viewH: 100)
        XCTAssertEqual(box.scale, 1, accuracy: 0.01)
        XCTAssertEqual(box.dx, 50, accuracy: 0.01)
        XCTAssertEqual(box.dy, 0, accuracy: 0.01)
        let mapped = OverlayMath.mapContain(x: 50, y: 50, srcW: 100, srcH: 100, viewW: 200, viewH: 100)
        XCTAssertEqual(mapped.0, 100, accuracy: 0.01)
        XCTAssertEqual(mapped.1, 50, accuracy: 0.01)
        let back = OverlayMath.unmapContain(x: mapped.0, y: mapped.1, srcW: 100, srcH: 100, viewW: 200, viewH: 100)
        XCTAssertEqual(back.0, 50, accuracy: 0.01)
        XCTAssertEqual(back.1, 50, accuracy: 0.01)
    }

    func testZeroScoreIsNotPurple() {
        XCTAssertEqual(ReportTheme.scorePurple(nil).argb, Theme.title.argb)
        XCTAssertEqual(ReportTheme.scorePurple(0).argb, Theme.title.argb)
    }
}

final class ClipRangeTests: XCTestCase {
    func testClampAndPastEnd() {
        XCTAssertEqual(ClipRange.clampPlayheadMs(0, startMs: 100, endMs: 500), 100)
        XCTAssertTrue(ClipRange.pastPlayEnd(posMs: 500, endMs: 500))
        XCTAssertFalse(ClipRange.shouldReseekToStart(posMs: 0, startMs: 100, seekPending: true))
        XCTAssertTrue(ClipRange.shouldReseekToStart(posMs: 0, startMs: 100, seekPending: false))
    }
}

final class I18nTests: XCTestCase {
    func testEnglishIsKeyAndInterpolate() {
        let json = #"{"strings":{"Camera":{"zh":"拍摄"},"Hello {name}":{"zh":"你好 {name}"}}}"#
        I18n.initCatalog(json: json, storedLang: "en")
        XCTAssertEqual(I18n.t("Camera"), "Camera")
        I18n.setLanguage("zh")
        XCTAssertEqual(I18n.t("Camera"), "拍摄")
        XCTAssertEqual(I18n.t("Hello {name}", vars: ["name": "Ada"]), "你好 Ada")
        XCTAssertEqual(I18n.interpolate("In {lo:.1f}s", vars: ["lo": "1.2"]), "In 1.2s")
    }
}

final class PoseTrackTests: XCTestCase {
    private func joint(_ conf: Float, x: Float = 0) -> BlazeJoint {
        BlazeJoint(x: x, y: 0, z: 0, confidence: conf)
    }

    private func frame(_ tMs: Int64, _ confs: [Float], xs: [Float]? = nil) -> PoseFrame {
        let blaze = confs.enumerated().map { i, c in joint(c, x: xs?[i] ?? Float(i)) }
        return PoseFrame(tMs: tMs, poses: [], width: 100, height: 100, blaze33: blaze)
    }

    private func allJoints(_ conf: Float) -> [Float] {
        Array(repeating: conf, count: 33)
    }

    func testBridgesShortGapBetweenTwoGoodAnchors() {
        // Landmark 27 (an ankle-ish index) dips for two frames, flanked by
        // well-tracked samples 100ms apart on either side -- should interpolate.
        let confs0 = allJoints(0.9)
        var xs0 = Array(repeating: Float(0), count: 33)
        xs0[27] = 0
        var confs1 = allJoints(0.9)
        confs1[27] = 0.1
        var confs2 = allJoints(0.9)
        confs2[27] = 0.1
        let confs3 = allJoints(0.9)
        var xs3 = Array(repeating: Float(0), count: 33)
        xs3[27] = 10

        let frames = [
            frame(0, confs0, xs: xs0),
            frame(100, confs1),
            frame(200, confs2),
            frame(300, confs3, xs: xs3),
        ]
        let out = PoseTrack.stabilizeWeakJoints(frames)
        XCTAssertGreaterThanOrEqual(out[1].blaze33[27].confidence, Float(PoseTrack.jointConfMin))
        XCTAssertGreaterThanOrEqual(out[2].blaze33[27].confidence, Float(PoseTrack.jointConfMin))
        XCTAssertGreaterThan(out[1].blaze33[27].x, xs0[27])
        XCTAssertLessThan(out[2].blaze33[27].x, xs3[27])
        // Other landmarks and other frames are untouched.
        XCTAssertEqual(out[1].blaze33[0].confidence, 0.9)
        XCTAssertEqual(out[0].blaze33[27].x, xs0[27])
    }

    func testHoldsFromOneSidedAnchorWithinHoldMs() {
        let confs0 = allJoints(0.9)
        var confs1 = allJoints(0.9)
        confs1[27] = 0.1
        let frames = [
            frame(0, confs0),
            frame(100, confs1),
        ]
        let out = PoseTrack.stabilizeWeakJoints(frames)
        XCTAssertEqual(out[1].blaze33[27].x, out[0].blaze33[27].x)
        XCTAssertEqual(out[1].blaze33[27].confidence, out[0].blaze33[27].confidence * PoseTrack.interpConf, accuracy: 0.001)
    }

    func testLeavesGapAloneWhenNoAnchorWithinRange() {
        // No good anchor on either side (all weak) -- left alone.
        let confs = allJoints(0.1)
        let frames = [frame(0, confs), frame(100, confs), frame(200, confs)]
        let out = PoseTrack.stabilizeWeakJoints(frames)
        for f in out {
            XCTAssertEqual(f.blaze33[27].confidence, 0.1)
        }
    }

    func testGapLongerThanMaxGapIsNotInterpolated() {
        let confs0 = allJoints(0.9)
        var confsMid = allJoints(0.9)
        confsMid[27] = 0.1
        let confsEnd = allJoints(0.9)
        let frames = [
            frame(0, confs0),
            frame(200, confsMid),
            frame(500, confsEnd), // 500ms gap > maxGapMs (400)
        ]
        let out = PoseTrack.stabilizeWeakJoints(frames)
        XCTAssertEqual(out[1].blaze33[27].confidence, 0.1)
    }
}

final class EvidenceReliabilityTests: XCTestCase {
    private func blaze33Reliable() -> [BlazeJoint] {
        var joints = (0..<33).map { BlazeJoint(x: Float($0), y: 0, z: 0, confidence: 0.9) }
        // Non-core landmarks can stay low without affecting reliability.
        joints[0] = BlazeJoint(x: 0, y: 0, z: 0, confidence: 0.1)
        return joints
    }

    private func blaze33Unreliable() -> [BlazeJoint] {
        var joints = blaze33Reliable()
        joints[SportsSignals.lAnkle] = BlazeJoint(x: 0, y: 0, z: 0, confidence: 0.1)
        return joints
    }

    func testExtractFeaturesMarksCoreLandmarkDropoutAsUnreliable() {
        let frames = [
            AssessFrame(tMs: 0, blaze33: blaze33Reliable()),
            AssessFrame(tMs: 100, blaze33: blaze33Unreliable()),
            AssessFrame(tMs: 200, blaze33: blaze33Reliable()),
        ]
        let pack = SportsSignals.extractFeatures(frames, fpsIn: 30)
        XCTAssertEqual(pack.series.count, 3)
        XCTAssertTrue(pack.series[0].reliable)
        XCTAssertFalse(pack.series[1].reliable)
        XCTAssertTrue(pack.series[2].reliable)
    }
}

final class PlayerExportTests: XCTestCase {
    func testDownloadNameAndShareUrl() {
        XCTAssertEqual(PlayerExport.downloadFileName(displayName: nil, clipId: nil), "overlay.jpg")
        XCTAssertEqual(PlayerExport.downloadFileName(displayName: "a/b", clipId: "x"), "a_b.jpg")
        let url = PlayerExport.shareUrl(
            template: "https://twitter.com/intent/tweet?text={text}",
            text: "Visual Pose"
        )
        XCTAssertTrue(url.contains("Visual%20Pose"))
    }
}
