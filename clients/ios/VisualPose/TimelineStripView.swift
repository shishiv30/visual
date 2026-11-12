import AVFoundation
import UIKit

final class TimelineStripView: UIView {
    enum DragKind { case none, inHandle, outHandle, eitherHandle, playhead, tapOrPan, pan }

    var onPlayhead: ((Int) -> Void)?
    var onRange: ((Int, Int) -> Void)?
    /// true when a continuous drag (handle / playhead scrub) starts, false when it ends.
    /// Listeners should decode cheap preview frames while true and the exact frame on false.
    var onScrubbing: ((Bool) -> Void)?
    /// True while the user is dragging a handle or the playhead.
    private(set) var isScrubbing = false
    var currentPlayheadMs: Int { playheadMs }

    private let rulerH: CGFloat = 22
    private let filmH: CGFloat = 56
    private let cellW: CGFloat = 88
    private let edgePad: CGFloat = 20
    private let handleStroke: CGFloat = 8
    private let handleWing: CGFloat = 14
    private let handleHit: CGFloat = 28
    private let playheadHit: CGFloat = 16
    private let scrubBand = 48.0
    private let autoScrollZone = 32.0
    private let autoScrollStep = 14.0
    private let panSlop: CGFloat = 10
    private let barH: CGFloat = 12

    private let ink = UIColor(rgb: 0x121212)
    private let paper = UIColor(rgb: 0xF5F5F5)
    private let blue = UIColor(rgb: 0x5E35B1)
    private let passGreen = UIColor(rgb: 0xCE93D8)
    private let seedGreen = UIColor(rgb: 0x00FF00)
    private let dim = UIColor(white: 0, alpha: 140 / 255)
    private let tick = UIColor(rgb: 0x6F6F6F)
    private let rulerBg = UIColor(rgb: 0x1A1A1A)
    private let filmBg = UIColor(rgb: 0x242424)
    private let cellFill = UIColor(rgb: 0x2A2A2A)
    private let cellBorder = UIColor(rgb: 0x121212)

    private var durationMs = 1
    private var inMs = 0
    private var outMs = 1
    private var playheadMs = 0
    private var zoom = 1.0
    private var scrollXpx = 0.0
    private var mediaURL: URL?
    private var generator: AVAssetImageGenerator?
    private var thumbs: [Int: UIImage] = [:]
    private var inflight = Set<Int>()
    private var keyframesMs: [Int] = []
    private var drag = DragKind.none
    private var pressX: CGFloat = 0
    private var pressScroll = 0.0
    private var lastX: CGFloat = 0
    private weak var trackedTouch: UITouch?
    // Time value the current drag is steering; moved by finger deltas, see applyDrag.
    private var grabMs = 0.0
    private var scrubRate = 1.0
    private var displayLink: CADisplayLink?
    private let haptic = UISelectionFeedbackGenerator()
    private var trimEnabled = true
    private let thumbQueue = DispatchQueue(label: "visualpose.timeline.thumbs")

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = ink
        isUserInteractionEnabled = true
        isMultipleTouchEnabled = true
        let pinch = UIPinchGestureRecognizer(target: self, action: #selector(pinched(_:)))
        addGestureRecognizer(pinch)
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        backgroundColor = ink
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: rulerH + filmH + barH)
    }

    func bindVideo(url: URL, duration: Int) {
        clear()
        mediaURL = url
        durationMs = max(1, duration)
        inMs = 0
        outMs = durationMs
        playheadMs = 0
        zoom = 1
        scrollXpx = 0
        let asset = AVAsset(url: url)
        let gen = AVAssetImageGenerator(asset: asset)
        gen.appliesPreferredTrackTransform = true
        // Filmstrip cells don't need frame accuracy; letting the generator pick a nearby sync
        // frame is far cheaper and keeps the decoder free for the preview frame.
        let tolerance = CMTime(value: 500, timescale: 1000)
        gen.requestedTimeToleranceBefore = tolerance
        gen.requestedTimeToleranceAfter = tolerance
        gen.maximumSize = CGSize(width: cellW * 2, height: filmH * 2)
        generator = gen
        isHidden = false
        setNeedsDisplay()
    }

    func clear() {
        mediaURL = nil
        drag = .none
        trackedTouch = nil
        endScrub()
        generator = nil
        inflight.removeAll()
        thumbs.removeAll()
        keyframesMs = []
        setNeedsDisplay()
    }

    func setRange(startMs: Int, endMs: Int?) {
        let clamped = TimelineMath.clampRange(inMs: startMs, outMs: endMs, durationMs: durationMs)
        inMs = clamped.0
        outMs = clamped.1
        setNeedsDisplay()
    }

    func setPlayheadMs(_ tMs: Int) {
        playheadMs = min(max(tMs, 0), durationMs)
        setNeedsDisplay()
    }

    func setKeyframes(_ timesMs: [Int]) {
        keyframesMs = Array(Set(timesMs)).sorted()
        setNeedsDisplay()
    }

    func setTrimEnabled(_ enabled: Bool) {
        trimEnabled = enabled
        setNeedsDisplay()
    }

    @objc private func pinched(_ gr: UIPinchGestureRecognizer) {
        if gr.state == .began {
            // Two fingers: this is a zoom, not a handle drag.
            drag = .none
            trackedTouch = nil
            endScrub()
        }
        applyZoom(zoom * Double(gr.scale), anchorX: Double(gr.location(in: self).x))
        gr.scale = 1
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard mediaURL != nil else { return }
        if trackedTouch != nil {
            // A second finger joined: hand over to the pinch recognizer.
            drag = .none
            trackedTouch = nil
            endScrub()
            setNeedsDisplay()
            return
        }
        guard let touch = touches.first else { return }
        trackedTouch = touch
        let x = touch.location(in: self).x
        pressX = x
        lastX = x
        pressScroll = scrollXpx
        scrubRate = 1
        let hit = hit(x)
        if hit == .inHandle || hit == .outHandle || hit == .eitherHandle {
            drag = hit
            grabMs = Double(hit == .outHandle ? outMs : inMs)
            haptic.selectionChanged()
            haptic.prepare()
            beginScrub()
            if hit != .eitherHandle {
                emitPlayhead(Int(grabMs.rounded()))
            }
            setNeedsDisplay()
            return
        }
        if let keyMs = hitKeyframe(x) {
            drag = .none
            emitPlayhead(keyMs)
            setNeedsDisplay()
            return
        }
        if hit == .playhead || zoom <= 1.0 + 1e-6 {
            // Unzoomed: press anywhere = jump + scrub. On the playhead: scrub from it.
            drag = .playhead
            if hit != .playhead {
                emitPlayhead(msOf(x))
            }
            grabMs = Double(playheadMs)
            beginScrub()
        } else {
            // Zoomed: a drag on empty film pans; only a clean tap seeks (on touch up).
            drag = .tapOrPan
        }
        setNeedsDisplay()
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = trackedTouch, touches.contains(touch) else { return }
        let p = touch.location(in: self)
        let x = p.x
        let dx = x - lastX
        lastX = x
        if drag == .eitherHandle {
            if abs(x - pressX) <= panSlop / 2 { return }
            // Handles overlap: the first move direction decides which one is grabbed.
            drag = x < pressX ? .inHandle : .outHandle
            grabMs = Double(drag == .inHandle ? inMs : outMs)
            applyDrag(Double(x - pressX))
            setNeedsDisplay()
            return
        }
        if drag == .tapOrPan, abs(x - pressX) > panSlop {
            drag = .pan
        }
        switch drag {
        case .pan:
            setScroll(pressScroll - Double(x - pressX))
        case .inHandle, .outHandle, .playhead:
            scrubRate = TimelineMath.scrubRate(
                offStripPx: TimelineMath.offStripPx(y: Double(p.y), top: 0, bottom: Double(rulerH + filmH)),
                bandPx: scrubBand
            )
            applyDrag(Double(dx))
            ensureAutoScroll()
        default:
            break
        }
        setNeedsDisplay()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = trackedTouch, touches.contains(touch) else { return }
        if drag == .tapOrPan {
            emitPlayhead(msOf(touch.location(in: self).x))
        }
        finishGesture()
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = trackedTouch, touches.contains(touch) else { return }
        finishGesture()
    }

    private func finishGesture() {
        drag = .none
        trackedTouch = nil
        endScrub()
        setNeedsDisplay()
    }

    /// Move the dragged handle / playhead by a finger delta, scaled by the scrub rate. Deltas
    /// (not absolute x) mean the handle never jumps to the finger on press.
    private func applyDrag(_ dxPx: Double) {
        grabMs += TimelineMath.dxToMs(
            dxPx: dxPx, durationMs: Double(durationMs), viewportWidth: Int(viewportW()), zoom: zoom, rate: scrubRate
        )
        switch drag {
        case .inHandle:
            grabMs = min(max(grabMs, 0), Double(max(0, outMs - TimelineMath.minRangeMs)))
            let clamped = TimelineMath.clampRange(inMs: Int(grabMs.rounded()), outMs: outMs, durationMs: durationMs)
            if clamped.0 != inMs || clamped.1 != outMs {
                inMs = clamped.0
                outMs = clamped.1
                onRange?(inMs, outMs)
            }
            emitPlayhead(inMs)
        case .outHandle:
            let lo = Double(min(durationMs, inMs + TimelineMath.minRangeMs))
            grabMs = min(max(grabMs, lo), Double(durationMs))
            let clamped = TimelineMath.clampRange(inMs: inMs, outMs: Int(grabMs.rounded()), durationMs: durationMs)
            if clamped.0 != inMs || clamped.1 != outMs {
                inMs = clamped.0
                outMs = clamped.1
                onRange?(inMs, outMs)
            }
            emitPlayhead(outMs)
        case .playhead:
            grabMs = min(max(grabMs, 0), Double(durationMs))
            emitPlayhead(Int(grabMs.rounded()))
        default:
            break
        }
    }

    private func ensureAutoScroll() {
        guard displayLink == nil, zoom > 1.0 + 1e-6 else { return }
        let link = CADisplayLink(target: self, selector: #selector(autoScrollTick))
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    private func stopAutoScroll() {
        displayLink?.invalidate()
        displayLink = nil
    }

    @objc private func autoScrollTick() {
        let active = drag == .inHandle || drag == .outHandle || drag == .playhead
        guard active, zoom > 1.0 + 1e-6 else {
            stopAutoScroll()
            return
        }
        let step = TimelineMath.edgeAutoScrollPx(
            x: Double(lastX - edgePad),
            viewportWidth: Int(viewportW()),
            zonePx: autoScrollZone,
            maxStepPx: autoScrollStep
        )
        guard step != 0 else { return }
        let before = scrollXpx
        setScroll(scrollXpx + step)
        let moved = scrollXpx - before
        if moved != 0 {
            // Content slid under a still finger: carry the grabbed time with it (rate 1).
            let keep = scrubRate
            scrubRate = 1
            applyDrag(moved)
            scrubRate = keep
            setNeedsDisplay()
        }
    }

    private func beginScrub() {
        guard !isScrubbing else { return }
        isScrubbing = true
        onScrubbing?(true)
    }

    private func endScrub() {
        scrubRate = 1
        stopAutoScroll()
        guard isScrubbing else { return }
        isScrubbing = false
        onScrubbing?(false)
    }

    override func draw(_ rect: CGRect) {
        ink.setFill()
        UIRectFill(bounds)
        guard mediaURL != nil else { return }
        paintRuler()
        paintFilm()
        paintDim()
        paintTrimEdge(inMs, start: true)
        paintTrimEdge(outMs, start: false)
        paintKeyframes()
        let x = xOf(Double(playheadMs))
        paper.setStroke()
        let play = UIBezierPath()
        play.move(to: CGPoint(x: x, y: 0))
        play.addLine(to: CGPoint(x: x, y: rulerH + filmH))
        play.lineWidth = 2
        play.stroke()
        paintScrollBar()
        paintScrubBubble()
    }

    /// Exact time (and fine-scrub rate) above the finger while dragging — the finger hides the handle.
    private func paintScrubBubble() {
        let tMs: Int
        switch drag {
        case .inHandle: tMs = inMs
        case .outHandle: tMs = outMs
        case .playhead: tMs = playheadMs
        default: return
        }
        let secs = Double(tMs) / 1000
        var label = String(
            format: "%d:%05.2f", locale: Locale(identifier: "en_US"), Int(secs / 60), secs.truncatingRemainder(dividingBy: 60)
        )
        if scrubRate < 1 {
            label += "  " + (scrubRate >= 0.5 ? "½×" : scrubRate >= 0.25 ? "¼×" : "⅒×")
        }
        let attrs: [NSAttributedString.Key: Any] = [
            .font: UIFont.monospacedDigitSystemFont(ofSize: 11, weight: .semibold),
            .foregroundColor: paper,
        ]
        let text = label as NSString
        let size = text.size(withAttributes: attrs)
        let w = size.width + 12
        let h = rulerH - 2
        let cx = min(max(xOf(Double(tMs)), w / 2), bounds.width - w / 2)
        let rect = CGRect(x: cx - w / 2, y: 1, width: w, height: h)
        blue.setFill()
        UIBezierPath(roundedRect: rect, cornerRadius: h / 2).fill()
        text.draw(at: CGPoint(x: rect.minX + 6, y: rect.midY - size.height / 2), withAttributes: attrs)
    }

    private func paintRuler() {
        rulerBg.setFill()
        UIBezierPath(rect: CGRect(x: contentLeft(), y: 0, width: contentRight() - contentLeft(), height: rulerH)).fill()
        let span = Double(durationMs)
        let step = TimelineMath.rulerTickMs(durationMs: span, viewportWidth: Int(viewportW()), zoom: zoom)
        let fine = step < 1000
        tick.setStroke()
        var tMs = 0.0
        let attrs: [NSAttributedString.Key: Any] = [
            .font: UIFont.systemFont(ofSize: 11),
            .foregroundColor: paper,
        ]
        while tMs <= span + 0.1 {
            let x = xOf(tMs)
            if x >= -40, x <= bounds.width + 40 {
                let tickPath = UIBezierPath()
                tickPath.move(to: CGPoint(x: x, y: rulerH - 6))
                tickPath.addLine(to: CGPoint(x: x, y: rulerH))
                tickPath.lineWidth = 1
                tickPath.stroke()
                (TimelineMath.formatRulerTime(tMs, fine: fine) as NSString).draw(
                    at: CGPoint(x: x + 3, y: 2),
                    withAttributes: attrs
                )
            }
            tMs += step
        }
        let endX = xOf(span)
        if abs(endX - xOf(max(0, tMs - step))) > 40 {
            let tickPath = UIBezierPath()
            tickPath.move(to: CGPoint(x: endX, y: rulerH - 6))
            tickPath.addLine(to: CGPoint(x: endX, y: rulerH))
            tickPath.lineWidth = 1
            tickPath.stroke()
            let label = TimelineMath.formatRulerTime(span, fine: fine) as NSString
            let w = label.size(withAttributes: attrs).width
            label.draw(at: CGPoint(x: endX - w, y: 2), withAttributes: attrs)
        }
    }

    private func paintFilm() {
        filmBg.setFill()
        UIBezierPath(rect: CGRect(x: contentLeft(), y: rulerH, width: contentRight() - contentLeft(), height: filmH)).fill()
        let content = TimelineMath.contentWidthPx(viewportWidth: Int(viewportW()), zoom: zoom)
        let n = max(1, Int((content / Double(cellW)).rounded()))
        let cell = content / Double(n)
        let startI = max(0, Int(scrollXpx / cell) - 1)
        let endI = min(n, Int((scrollXpx + Double(viewportW())) / cell) + 2)
        cellBorder.setStroke()
        for i in startI..<endI {
            let x0 = contentLeft() + CGFloat(Double(i) * cell - scrollXpx)
            let tMs = (Double(i) + 0.5) / Double(n) * Double(durationMs)
            let dest = CGRect(x: x0, y: rulerH, width: CGFloat(cell), height: filmH)
            if let pix = thumbAt(Int(tMs)) {
                pix.draw(in: dest)
            } else {
                cellFill.setFill()
                UIBezierPath(rect: dest).fill()
            }
            UIBezierPath(rect: dest).stroke()
        }
    }

    private func paintDim() {
        dim.setFill()
        let leftW = max(contentLeft(), xOf(Double(inMs)))
        UIBezierPath(rect: CGRect(x: contentLeft(), y: rulerH, width: leftW - contentLeft(), height: filmH)).fill()
        let rightX = xOf(Double(outMs))
        UIBezierPath(rect: CGRect(x: rightX, y: rulerH, width: contentRight() - rightX, height: filmH)).fill()
    }

    private func paintTrimEdge(_ tMs: Int, start: Bool) {
        let x = xOf(Double(tMs))
        let top = rulerH
        let bot = rulerH + filmH
        let half = handleStroke / 2
        let active = (start && drag == .inHandle) || (!start && drag == .outHandle)
        let color = active ? passGreen : blue
        color.setFill()
        UIBezierPath(rect: CGRect(x: x - half, y: top, width: handleStroke, height: bot - top)).fill()
        color.setStroke()
        let wing = UIBezierPath()
        wing.lineWidth = handleStroke
        wing.lineCapStyle = .square
        if start {
            wing.move(to: CGPoint(x: x, y: top))
            wing.addLine(to: CGPoint(x: x + handleWing, y: top))
            wing.move(to: CGPoint(x: x, y: bot))
            wing.addLine(to: CGPoint(x: x + handleWing, y: bot))
        } else {
            wing.move(to: CGPoint(x: x, y: top))
            wing.addLine(to: CGPoint(x: x - handleWing, y: top))
            wing.move(to: CGPoint(x: x, y: bot))
            wing.addLine(to: CGPoint(x: x - handleWing, y: bot))
        }
        wing.stroke()
    }

    private func paintKeyframes() {
        let y = rulerH + 8
        let fill = trimEnabled ? seedGreen : passGreen
        fill.setFill()
        ink.setStroke()
        for tMs in keyframesMs {
            let x = xOf(Double(tMs))
            if x < -12 || x > bounds.width + 12 { continue }
            let diamond = UIBezierPath()
            diamond.move(to: CGPoint(x: x, y: y - 6))
            diamond.addLine(to: CGPoint(x: x + 5, y: y))
            diamond.addLine(to: CGPoint(x: x, y: y + 6))
            diamond.addLine(to: CGPoint(x: x - 5, y: y))
            diamond.close()
            diamond.fill()
            diamond.lineWidth = 1
            diamond.stroke()
        }
    }

    private func paintScrollBar() {
        let maximum = TimelineMath.maxScrollX(viewportWidth: Int(viewportW()), zoom: zoom)
        if maximum <= 0 { return }
        let track = CGRect(x: contentLeft(), y: rulerH + filmH, width: contentRight() - contentLeft(), height: barH)
        UIColor(rgb: 0x1A1A1A).setFill()
        UIBezierPath(rect: track).fill()
        let inner = contentRight() - contentLeft()
        let thumbW = max(24, CGFloat(Double(viewportW()) / (Double(viewportW()) + maximum) * Double(inner)))
        let maxX = inner - thumbW
        let x = contentLeft() + (maximum <= 0 ? 0 : CGFloat(scrollXpx / maximum) * maxX)
        blue.setFill()
        UIBezierPath(roundedRect: CGRect(x: x, y: track.minY + 3, width: thumbW, height: track.height - 6), cornerRadius: 4).fill()
    }

    private func thumbAt(_ tMs: Int) -> UIImage? {
        let key = Int((Float(tMs) / 80).rounded()) * 80
        if let cached = thumbs[key] { return cached }
        requestThumb(key)
        return nil
    }

    private func requestThumb(_ key: Int) {
        if thumbs[key] != nil || inflight.contains(key) || generator == nil { return }
        inflight.insert(key)
        let time = CMTime(value: CMTimeValue(key), timescale: 1000)
        thumbQueue.async { [weak self] in
            guard let self, let gen = self.generator else { return }
            let image = try? gen.copyCGImage(at: time, actualTime: nil)
            let ui = image.map { UIImage(cgImage: $0) }
            DispatchQueue.main.async {
                self.inflight.remove(key)
                if self.mediaURL == nil {
                    return
                }
                if let ui {
                    self.thumbs[key] = ui
                    self.setNeedsDisplay()
                }
            }
        }
    }

    private func hit(_ x: CGFloat) -> DragKind {
        if trimEnabled {
            let inDist = abs(x - xOf(Double(inMs)))
            let outDist = abs(x - xOf(Double(outMs)))
            let inHit = inDist <= handleHit
            let outHit = outDist <= handleHit
            if inHit && outHit {
                // Handles nearly on top of each other: let the first move direction decide.
                if abs(inDist - outDist) < 8 { return .eitherHandle }
                return inDist <= outDist ? .inHandle : .outHandle
            }
            if inHit { return .inHandle }
            if outHit { return .outHandle }
        }
        if abs(x - xOf(Double(playheadMs))) <= playheadHit {
            return .playhead
        }
        return .none
    }

    private func hitKeyframe(_ x: CGFloat) -> Int? {
        TimelineMath.nearestKeyframeMs(
            x: Double(x - edgePad),
            keyframeMs: keyframesMs,
            durationMs: Double(durationMs),
            viewportWidth: Int(viewportW()),
            zoom: zoom,
            scrollX: scrollXpx,
            hitPx: 10
        )
    }

    private func seekToX(_ x: CGFloat) {
        emitPlayhead(msOf(x))
        setNeedsDisplay()
    }

    private func emitPlayhead(_ tMs: Int) {
        playheadMs = min(max(tMs, 0), durationMs)
        onPlayhead?(playheadMs)
    }

    private func applyZoom(_ nextZoom: Double, anchorX: Double) {
        let kept = TimelineMath.zoomKeepingMs(
            zoom: nextZoom,
            anchorX: anchorX - Double(edgePad),
            durationMs: Double(durationMs),
            viewportWidth: Int(viewportW()),
            oldZoom: zoom,
            oldScrollX: scrollXpx
        )
        zoom = kept.0
        scrollXpx = kept.1
        setNeedsDisplay()
    }

    private func setScroll(_ next: Double) {
        scrollXpx = TimelineMath.clampScrollX(next, viewportWidth: Int(viewportW()), zoom: zoom)
        setNeedsDisplay()
    }

    private func viewportW() -> CGFloat { max(1, bounds.width - 2 * edgePad) }
    private func contentLeft() -> CGFloat { edgePad }
    private func contentRight() -> CGFloat { bounds.width - edgePad }

    private func xOf(_ tMs: Double) -> CGFloat {
        contentLeft() + CGFloat(TimelineMath.msToX(
            tMs: tMs,
            durationMs: Double(durationMs),
            viewportWidth: Int(viewportW()),
            zoom: zoom,
            scrollX: scrollXpx
        ))
    }

    private func msOf(_ x: CGFloat) -> Int {
        Int(TimelineMath.xToMs(
            x: Double(x - edgePad),
            durationMs: Double(durationMs),
            viewportWidth: Int(viewportW()),
            zoom: zoom,
            scrollX: scrollXpx
        ).rounded())
    }
}

/// Off-main-thread, latest-wins video frame loader for scrubbing.
///
/// `AVAssetImageGenerator.copyCGImage` with zero tolerance decodes from the previous sync frame
/// up to the target at full resolution; calling it on the main thread for every `touchesMoved`
/// blocked touch delivery, so trim handles lagged and then jumped. This class decodes on a
/// serial queue, keeps only the newest pending request, uses a fast nearest-sync-frame decode
/// while scrubbing and refines to the exact frame once the finger rests (or on release).
final class FrameScrubber {
    static let settleSeconds = 0.12

    private struct Req {
        let tMs: Int
        let precise: Bool
        let seq: Int
        let gen: Int
    }

    private let queue = DispatchQueue(label: "visualpose.frame.scrubber", qos: .userInteractive)
    private let lock = NSLock()
    private let maxSize: CGSize
    private let onFrame: (Int, UIImage) -> Void

    // Guarded by `lock`.
    private var pending: Req?
    private var drainQueued = false
    private var seq = 0
    private var gen = 0
    private var fastGen: AVAssetImageGenerator?
    private var exactGen: AVAssetImageGenerator?

    // Main thread only.
    private var deliveredSeq = -1
    private var lastTMs = -1
    private var lastPrecise = false
    private var settle: DispatchWorkItem?

    init(maxSize: CGSize, onFrame: @escaping (Int, UIImage) -> Void) {
        self.maxSize = maxSize
        self.onFrame = onFrame
    }

    func bind(url: URL) {
        let asset = AVAsset(url: url)
        let fast = AVAssetImageGenerator(asset: asset)
        fast.appliesPreferredTrackTransform = true
        fast.maximumSize = maxSize
        fast.requestedTimeToleranceBefore = .positiveInfinity
        fast.requestedTimeToleranceAfter = .positiveInfinity
        let exact = AVAssetImageGenerator(asset: asset)
        exact.appliesPreferredTrackTransform = true
        exact.maximumSize = maxSize
        exact.requestedTimeToleranceBefore = .zero
        exact.requestedTimeToleranceAfter = .zero
        lock.lock()
        gen += 1
        pending = nil
        fastGen = fast
        exactGen = exact
        lock.unlock()
        cancelSettle()
        lastTMs = -1
        deliveredSeq = -1
    }

    func clear() {
        lock.lock()
        gen += 1
        pending = nil
        fastGen = nil
        exactGen = nil
        lock.unlock()
        cancelSettle()
        lastTMs = -1
    }

    /// Request the frame at `tMs`. Safe to call on every touch move. Main thread only.
    func request(_ tMs: Int, precise: Bool) {
        guard tMs >= 0 else { return }
        if tMs == lastTMs, lastPrecise || !precise { return }
        cancelSettle()
        lastTMs = tMs
        lastPrecise = precise
        lock.lock()
        seq += 1
        pending = Req(tMs: tMs, precise: precise, seq: seq, gen: gen)
        let shouldQueue = !drainQueued
        drainQueued = true
        lock.unlock()
        if shouldQueue {
            queue.async { [weak self] in self?.drain() }
        }
        if !precise {
            let item = DispatchWorkItem { [weak self] in
                guard let self else { return }
                self.request(self.lastTMs, precise: true)
            }
            settle = item
            DispatchQueue.main.asyncAfter(deadline: .now() + Self.settleSeconds, execute: item)
        }
    }

    private func cancelSettle() {
        settle?.cancel()
        settle = nil
    }

    private func drain() {
        lock.lock()
        let req = pending
        pending = nil
        drainQueued = false
        let generator: AVAssetImageGenerator? = req.flatMap { $0.precise ? exactGen : fastGen }
        let currentGen = gen
        lock.unlock()
        guard let req, let generator, req.gen == currentGen else { return }
        let time = CMTime(value: CMTimeValue(req.tMs), timescale: 1000)
        guard let cg = try? generator.copyCGImage(at: time, actualTime: nil) else { return }
        let image = UIImage(cgImage: cg)
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.lock.lock()
            let live = req.gen == self.gen
            self.lock.unlock()
            // Drop results already superseded on screen, or from a previous video.
            guard live, req.seq >= self.deliveredSeq else { return }
            self.deliveredSeq = req.seq
            self.onFrame(req.tMs, image)
        }
    }
}
