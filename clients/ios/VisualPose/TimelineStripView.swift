import AVFoundation
import UIKit

final class TimelineStripView: UIView {
    enum DragKind { case none, inHandle, outHandle, playhead, pan }

    var onPlayhead: ((Int) -> Void)?
    var onRange: ((Int, Int) -> Void)?

    private let rulerH: CGFloat = 22
    private let filmH: CGFloat = 56
    private let cellW: CGFloat = 88
    private let edgePad: CGFloat = 20
    private let handleStroke: CGFloat = 8
    private let handleWing: CGFloat = 14
    private let handleHit: CGFloat = 28
    private let playheadHit: CGFloat = 8
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
    private var panning = false
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
        gen.requestedTimeToleranceBefore = .zero
        gen.requestedTimeToleranceAfter = .zero
        gen.maximumSize = CGSize(width: cellW * 2, height: filmH * 2)
        generator = gen
        isHidden = false
        setNeedsDisplay()
    }

    func clear() {
        mediaURL = nil
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
        applyZoom(zoom * Double(gr.scale), anchorX: Double(gr.location(in: self).x))
        gr.scale = 1
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard mediaURL != nil, let touch = touches.first else { return }
        let x = touch.location(in: self).x
        pressX = x
        pressScroll = scrollXpx
        panning = false
        let hit = hit(x)
        if hit == .inHandle || hit == .outHandle {
            drag = hit
            emitPlayhead(hit == .inHandle ? inMs : outMs)
            return
        }
        if let keyMs = hitKeyframe(x) {
            drag = .none
            emitPlayhead(keyMs)
            return
        }
        drag = hit == .none ? .playhead : hit
        if drag == .playhead, hit == .none {
            seekToX(x)
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        let x = touch.location(in: self).x
        let dx = x - pressX
        if drag == .playhead, !panning, zoom > 1.0 + 1e-6, abs(dx) > panSlop {
            drag = .pan
            panning = true
        }
        switch drag {
        case .pan:
            setScroll(pressScroll - Double(dx))
        case .inHandle:
            let clamped = TimelineMath.clampRange(inMs: msOf(x), outMs: outMs, durationMs: durationMs)
            inMs = clamped.0
            outMs = clamped.1
            emitPlayhead(inMs)
            onRange?(inMs, outMs)
        case .outHandle:
            let clamped = TimelineMath.clampRange(inMs: inMs, outMs: msOf(x), durationMs: durationMs)
            inMs = clamped.0
            outMs = clamped.1
            emitPlayhead(outMs)
            onRange?(inMs, outMs)
        case .playhead:
            seekToX(x)
        case .none:
            break
        }
        setNeedsDisplay()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        drag = .none
        panning = false
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        drag = .none
        panning = false
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
        blue.setFill()
        UIBezierPath(rect: CGRect(x: x - half, y: top, width: handleStroke, height: bot - top)).fill()
        blue.setStroke()
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
