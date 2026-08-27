import Foundation

enum Posture {
    static func scores(_ pack: FeaturePack, results: [KeypointResult] = []) -> PostureScores {
        let stability = clamp(
            0.55 * scoreQuiet(pack.upperQuiet) + 0.45 * scoreStanceLock(pack.stanceWidthStd)
        )
        let coordination = clamp(
            0.6 * scoreRhythm(pack.kneeFlexFreq, pack.turnFreq) + 0.4 * scoreHands(pack.handsLow)
        )
        let fromKp = scoreControlFromKeypoints(results)
        let lean = scoreLean(pack.inwardLean)
        let control = fromKp == nil ? lean : clamp(0.65 * fromKp! + 0.35 * lean)
        let balance = scoreBalance(pack.backseat, pack.kneeValgus)
        return PostureScores(
            stability: Json.round1(stability),
            coordination: Json.round1(coordination),
            control: Json.round1(control),
            balance: Json.round1(balance)
        )
    }

    private static func clamp(_ value: Double) -> Double {
        min(max(value, 0), 100)
    }

    private static func scoreQuiet(_ upperQuiet: Double) -> Double {
        clamp(100.0 - upperQuiet * 35.0)
    }

    private static func scoreStanceLock(_ stanceStd: Double) -> Double {
        clamp(100.0 - stanceStd * 40.0)
    }

    private static func scoreRhythm(_ kneeFreq: Double, _ turnFreq: Double) -> Double {
        if kneeFreq <= 0.05 && turnFreq <= 0.05 {
            return 45.0
        }
        let ratio = min(kneeFreq, turnFreq) / max(kneeFreq, max(turnFreq, 1e-3))
        return clamp(40.0 + ratio * 60.0)
    }

    private static func scoreHands(_ handsLow: Double) -> Double {
        clamp(handsLow * 100.0)
    }

    private static func scoreControlFromKeypoints(_ results: [KeypointResult]) -> Double? {
        let known = results.compactMap { $0.score }
        if known.isEmpty { return nil }
        return clamp(known.reduce(0, +) / Double(known.count))
    }

    private static func scoreLean(_ inwardLean: Double) -> Double {
        if inwardLean <= 0.05 { return 55.0 }
        if inwardLean <= 0.35 { return clamp(55.0 + inwardLean * 100.0) }
        return clamp(100.0 - (inwardLean - 0.35) * 80.0)
    }

    private static func scoreBalance(_ backseat: Double, _ kneeValgus: Double) -> Double {
        let seat = clamp(100.0 - abs(backseat) * 80.0)
        let valgus = clamp(100.0 - abs(kneeValgus - 0.15) * 120.0)
        return clamp(0.55 * seat + 0.45 * valgus)
    }
}
