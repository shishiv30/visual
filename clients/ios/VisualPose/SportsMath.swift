import Foundation

enum SportsMath {
    static func mean(_ values: [Double]) -> Double {
        if values.isEmpty { return 0 }
        return values.reduce(0, +) / Double(values.count)
    }

    static func median(_ values: [Double]) -> Double {
        if values.isEmpty { return 0 }
        let sorted = values.sorted()
        let mid = sorted.count / 2
        if sorted.count % 2 == 0 {
            return (sorted[mid - 1] + sorted[mid]) / 2.0
        }
        return sorted[mid]
    }

    static func std(_ values: [Double]) -> Double {
        if values.isEmpty { return 0 }
        let mu = mean(values)
        let varPop = values.reduce(0.0) { $0 + pow($1 - mu, 2) } / Double(values.count)
        return sqrt(varPop)
    }

    static func percentile(_ values: [Double], _ p: Double) -> Double {
        if values.isEmpty { return 0 }
        let sorted = values.sorted()
        if sorted.count == 1 { return sorted[0] }
        let idx = (p / 100.0) * Double(sorted.count - 1)
        let lo = min(max(Int(idx), 0), sorted.count - 1)
        let hi = min(lo + 1, sorted.count - 1)
        let frac = idx - Double(lo)
        return sorted[lo] * (1.0 - frac) + sorted[hi] * frac
    }

    static func angleDeg(ax: Double, ay: Double, bx: Double, by: Double, cx: Double, cy: Double) -> Double {
        let bax = ax - bx
        let bay = ay - by
        let bcx = cx - bx
        let bcy = cy - by
        let nba = sqrt(bax * bax + bay * bay)
        let nbc = sqrt(bcx * bcx + bcy * bcy)
        if nba < 1e-6 || nbc < 1e-6 { return .nan }
        let cos = min(max((bax * bcx + bay * bcy) / (nba * nbc), -1.0), 1.0)
        return acos(cos) * 180.0 / .pi
    }

    static func zeroCrossFreq(_ series: [Double], fps: Double) -> Double {
        if series.count < 4 { return 0 }
        let sign = series.map { value -> Double in
            let s = value == 0 ? 0.0 : (value > 0 ? 1.0 : -1.0)
            return s == 0 ? 1.0 : s
        }
        var crosses = 0
        for i in 1..<sign.count {
            if sign[i] * sign[i - 1] < 0 {
                crosses += 1
            }
        }
        let dur = Double(series.count) / max(fps, 1.0)
        return 0.5 * Double(crosses) / max(dur, 1e-3)
    }
}
