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

final class PlayerExportTests: XCTestCase {
    func testDownloadNameAndShareUrl() {
        XCTAssertEqual(PlayerExport.downloadFileName(nil, clipId: nil), "overlay.jpg")
        XCTAssertEqual(PlayerExport.downloadFileName("a/b", clipId: "x"), "a_b.jpg")
        let url = PlayerExport.shareUrl("https://twitter.com/intent/tweet?text={text}", "Visual Pose")
        XCTAssertTrue(url.contains("Visual%20Pose"))
    }
}
