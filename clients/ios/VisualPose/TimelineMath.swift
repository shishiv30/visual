import Foundation

enum TimelineMath {
    static let minZoom = 1.0
    static let maxZoom = 5.0
    static let minRangeMs = 200
    static let rulerTickPx = 100.0
    static let keyframeHitPx = 10.0

    static func clampZoom(_ zoom: Double) -> Double {
        max(minZoom, min(maxZoom, zoom))
    }

    static func contentWidthPx(viewportWidth: Int, zoom: Double) -> Double {
        max(1.0, Double(viewportWidth)) * clampZoom(zoom)
    }

    static func maxScrollX(viewportWidth: Int, zoom: Double) -> Double {
        max(0.0, contentWidthPx(viewportWidth: viewportWidth, zoom: zoom) - Double(viewportWidth))
    }

    static func clampScrollX(_ scrollX: Double, viewportWidth: Int, zoom: Double) -> Double {
        max(0.0, min(maxScrollX(viewportWidth: viewportWidth, zoom: zoom), scrollX))
    }

    static func msToX(
        tMs: Double,
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double
    ) -> Double {
        let duration = max(1.0, durationMs)
        let content = contentWidthPx(viewportWidth: viewportWidth, zoom: zoom)
        return (tMs / duration) * content - scrollX
    }

    static func xToMs(
        x: Double,
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double
    ) -> Double {
        let duration = max(1.0, durationMs)
        let content = contentWidthPx(viewportWidth: viewportWidth, zoom: zoom)
        let tMs = ((x + scrollX) / content) * duration
        return max(0.0, min(duration, tMs))
    }

    static func clampRange(
        inMs: Int,
        outMs: Int?,
        durationMs: Int,
        minRangeMs: Int = minRangeMs
    ) -> (Int, Int) {
        let duration = max(minRangeMs, durationMs)
        var start = min(max(inMs, 0), duration)
        var end = outMs == nil ? duration : min(max(outMs!, 0), duration)
        if end - start < minRangeMs {
            end = min(duration, start + minRangeMs)
            if end - start < minRangeMs {
                start = max(0, end - minRangeMs)
            }
        }
        return (start, end)
    }

    static func zoomKeepingMs(
        zoom: Double,
        anchorX: Double,
        durationMs: Double,
        viewportWidth: Int,
        oldZoom: Double,
        oldScrollX: Double
    ) -> (Double, Double) {
        let newZoom = clampZoom(zoom)
        let tMs = xToMs(
            x: anchorX, durationMs: durationMs, viewportWidth: viewportWidth, zoom: oldZoom, scrollX: oldScrollX
        )
        let content = contentWidthPx(viewportWidth: viewportWidth, zoom: newZoom)
        let duration = max(1.0, durationMs)
        let newScroll = (tMs / duration) * content - anchorX
        return (newZoom, clampScrollX(newScroll, viewportWidth: viewportWidth, zoom: newZoom))
    }

    static func rulerTickMs(
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        tickPx: Double = rulerTickPx
    ) -> Double {
        let content = contentWidthPx(viewportWidth: viewportWidth, zoom: zoom)
        let duration = max(1.0, durationMs)
        return (tickPx / content) * duration
    }

    static func nearestKeyframeMs(
        x: Double,
        keyframeMs: [Int],
        durationMs: Double,
        viewportWidth: Int,
        zoom: Double,
        scrollX: Double,
        hitPx: Double = keyframeHitPx
    ) -> Int? {
        var best: Int?
        var bestD = hitPx
        for tMs in keyframeMs {
            let kx = msToX(
                tMs: Double(tMs), durationMs: durationMs, viewportWidth: viewportWidth, zoom: zoom, scrollX: scrollX
            )
            let dist = abs(kx - x)
            if dist <= bestD {
                bestD = dist
                best = tMs
            }
        }
        return best
    }

    static func formatRulerTime(_ tMs: Double, fine: Bool) -> String {
        let totalS = max(0.0, tMs / 1000.0)
        let minutes = Int(totalS / 60)
        let seconds = totalS - Double(minutes * 60)
        if fine {
            return String(format: "%d:%04.1f", locale: Locale(identifier: "en_US"), minutes, seconds)
        }
        return String(format: "%d:%02d", locale: Locale(identifier: "en_US"), minutes, Int(seconds))
    }
}
