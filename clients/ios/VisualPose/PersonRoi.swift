import Foundation

struct PixelBox {
    var x1: Double
    var y1: Double
    var x2: Double
    var y2: Double

    func toBBox() -> BBox {
        BBox(x1: Float(x1), y1: Float(y1), x2: Float(x2), y2: Float(y2))
    }
}

struct CropSpec {
    var ox: Int
    var oy: Int
    var x2: Int
    var y2: Int
    var scale: Double
}

enum PersonRoi {
    static let histHBins = 30
    static let histSBins = 32
    static let minSat: Float = 40
    static let maxVal: Float = 250
    static let searchExpand = 1.8
    static let posePad = 0.35
    static let minCropSide = 256
    static let termCount = 12
    static let termEps = 1.0

    static func denormBox(_ seed: NormBox, width: Int, height: Int) -> PixelBox {
        PixelBox(
            x1: Double(seed.x1) * Double(width),
            y1: Double(seed.y1) * Double(height),
            x2: Double(seed.x2) * Double(width),
            y2: Double(seed.y2) * Double(height)
        )
    }

    static func clipBox(_ box: PixelBox, width: Int, height: Int) -> [Int] {
        let nx1 = Int(max(0.0, min(box.x1, box.x2)))
        let ny1 = Int(max(0.0, min(box.y1, box.y2)))
        let nx2 = Int(min(Double(width), max(box.x1, box.x2)))
        let ny2 = Int(min(Double(height), max(box.y1, box.y2)))
        if nx2 <= nx1 || ny2 <= ny1 {
            return [0, 0, width, height]
        }
        return [nx1, ny1, nx2, ny2]
    }

    static func cropRect(
        _ box: PixelBox,
        width: Int,
        height: Int,
        pad: Double = posePad,
        minSide: Int = minCropSide
    ) -> CropSpec {
        let bw = max(1.0, box.x2 - box.x1)
        let bh = max(1.0, box.y2 - box.y1)
        let padded = PixelBox(
            x1: box.x1 - bw * pad,
            y1: box.y1 - bh * pad,
            x2: box.x2 + bw * pad,
            y2: box.y2 + bh * pad
        )
        let clipped = clipBox(padded, width: width, height: height)
        let cw = max(clipped[2] - clipped[0], 1)
        let ch = max(clipped[3] - clipped[1], 1)
        let shortest = min(cw, ch)
        let scale = shortest < minSide ? Double(minSide) / Double(shortest) : 1.0
        return CropSpec(ox: clipped[0], oy: clipped[1], x2: clipped[2], y2: clipped[3], scale: scale)
    }

    static func remapPoint(x: Double, y: Double, ox: Int, oy: Int, scale: Double) -> (Double, Double) {
        let inv = scale == 0 ? 1.0 : 1.0 / scale
        return (x * inv + Double(ox), y * inv + Double(oy))
    }

    static func buildHist(pixels: [UInt32], width: Int, height: Int, box: PixelBox) -> [Float] {
        var hist = [Float](repeating: 0, count: histHBins * histSBins)
        let clip = clipBox(box, width: width, height: height)
        var hsv: [Float] = [0, 0, 0]
        for y in clip[1]..<clip[3] {
            for x in clip[0]..<clip[2] {
                toHsv(pixels[y * width + x], &hsv)
                let h = hsv[0]
                let s = hsv[1]
                let v = hsv[2]
                if s < minSat || v < 32 || v > maxVal { continue }
                let hb = min(max(Int((Double(h) / 180.0) * Double(histHBins)), 0), histHBins - 1)
                let sb = min(max(Int((Double(s) / 256.0) * Double(histSBins)), 0), histSBins - 1)
                hist[hb * histSBins + sb] += 1
            }
        }
        var maxv: Float = 0
        for value in hist where value > maxv {
            maxv = value
        }
        if maxv > 0 {
            let gain = 255 / maxv
            for i in hist.indices {
                hist[i] *= gain
            }
        }
        return hist
    }

    static func search(
        pixels: [UInt32],
        width: Int,
        height: Int,
        hist: [Float],
        prev: PixelBox
    ) -> PixelBox {
        let back = backProject(pixels: pixels, width: width, height: height, hist: hist)
        let window = expandWindow(prev, width: width, height: height, scale: searchExpand)
        var x = window[0]
        var y = window[1]
        var w = window[2]
        var h = window[3]
        for _ in 0..<termCount {
            var m00 = 0.0
            var m10 = 0.0
            var m01 = 0.0
            let x2 = min(x + w, width)
            let y2 = min(y + h, height)
            if y < y2 && x < x2 {
                for py in y..<y2 {
                    let row = py * width
                    for px in x..<x2 {
                        let mass = Double(back[row + px])
                        m00 += mass
                        m10 += Double(px) * mass
                        m01 += Double(py) * mass
                    }
                }
            }
            if m00 < 1.0 { break }
            let cx = Int(m10 / m00)
            let cy = Int(m01 / m00)
            let nx = min(max(cx - w / 2, 0), width - 1)
            let ny = min(max(cy - h / 2, 0), height - 1)
            let dx = abs(nx - x)
            let dy = abs(ny - y)
            x = nx
            y = ny
            if Double(dx) < termEps && Double(dy) < termEps { break }
        }
        if w >= 8 && h >= 8 {
            return PixelBox(
                x1: Double(x),
                y1: Double(y),
                x2: Double(min(x + w, width)),
                y2: Double(min(y + h, height))
            )
        }
        return peakFallback(back, width: width, height: height, prev: prev)
    }

    static func blendHist(_ prev: [Float], _ next: [Float], alpha: Float = 0.15) -> [Float] {
        var mixed = [Float](repeating: 0, count: prev.count)
        var maxv: Float = 0
        for i in prev.indices {
            let value = (1 - alpha) * prev[i] + alpha * next[i]
            mixed[i] = value
            if value > maxv { maxv = value }
        }
        if maxv > 0 {
            let gain = 255 / maxv
            for i in mixed.indices {
                mixed[i] *= gain
            }
        }
        return mixed
    }

    private static func backProject(pixels: [UInt32], width: Int, height: Int, hist: [Float]) -> [Float] {
        var out = [Float](repeating: 0, count: pixels.count)
        var hsv: [Float] = [0, 0, 0]
        for i in pixels.indices {
            toHsv(pixels[i], &hsv)
            let hb = min(max(Int((Double(hsv[0]) / 180.0) * Double(histHBins)), 0), histHBins - 1)
            let sb = min(max(Int((Double(hsv[1]) / 256.0) * Double(histSBins)), 0), histSBins - 1)
            out[i] = hist[hb * histSBins + sb]
        }
        return out
    }

    private static func expandWindow(_ box: PixelBox, width: Int, height: Int, scale: Double) -> [Int] {
        let cx = 0.5 * (box.x1 + box.x2)
        let cy = 0.5 * (box.y1 + box.y2)
        let bw = max(8.0, (box.x2 - box.x1) * scale)
        let bh = max(8.0, (box.y2 - box.y1) * scale)
        let nx1 = Int(max(0.0, cx - bw / 2.0))
        let ny1 = Int(max(0.0, cy - bh / 2.0))
        let nw = max(min(width - nx1, Int(bw)), 1)
        let nh = max(min(height - ny1, Int(bh)), 1)
        return [nx1, ny1, nw, nh]
    }

    private static func peakFallback(_ back: [Float], width: Int, height: Int, prev: PixelBox) -> PixelBox {
        let sw = max(1, width / 4)
        let sh = max(1, height / 4)
        var best: Float = -1
        var px = width / 2
        var py = height / 2
        for sy in 0..<sh {
            for sx in 0..<sw {
                let value = back[min(sy * 4, height - 1) * width + min(sx * 4, width - 1)]
                if value > best {
                    best = value
                    px = sx * 4
                    py = sy * 4
                }
            }
        }
        let bw = max(16.0, prev.x2 - prev.x1)
        let bh = max(16.0, prev.y2 - prev.y1)
        return PixelBox(
            x1: max(0.0, Double(px) - bw / 2),
            y1: max(0.0, Double(py) - bh / 2),
            x2: min(Double(width), Double(px) + bw / 2),
            y2: min(Double(height), Double(py) + bh / 2)
        )
    }

    private static func toHsv(_ argb: UInt32, _ out: inout [Float]) {
        let r = Int((argb >> 16) & 0xFF)
        let g = Int((argb >> 8) & 0xFF)
        let b = Int(argb & 0xFF)
        let maxc = max(r, max(g, b))
        let minc = min(r, min(g, b))
        let delta = maxc - minc
        let v = Float(maxc)
        let s: Float = maxc == 0 ? 0 : Float(delta) * 255 / Float(maxc)
        let h: Float
        if delta == 0 {
            h = 0
        } else if maxc == r {
            h = 60 * ((Float(g - b) / Float(delta) + 6).truncatingRemainder(dividingBy: 6))
        } else if maxc == g {
            h = 60 * (Float(b - r) / Float(delta) + 2)
        } else {
            h = 60 * (Float(r - g) / Float(delta) + 4)
        }
        out[0] = min(max(h / 2, 0), 179)
        out[1] = min(max(s, 0), 255)
        out[2] = v
    }
}
