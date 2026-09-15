import Foundation

struct FrameSample {
    var tMs: Double
    var stanceWidth: Double? = nil
    var kneeFlex: Double? = nil
    var inwardLean: Double? = nil
    var backseat: Double? = nil
    var kneeValgus: Double? = nil
    var hipIrProxy: Double? = nil
    var handsLow: Double? = nil
    var gazeOk: Double? = nil
    var quiet: Double? = nil
    var hipX: Double? = nil
    var hipY: Double? = nil
    /// True only if every core landmark (shoulders, hips, knees, ankles) was
    /// tracked at >= `SportsSignals.evidenceCoreConfMin` confidence in this
    /// frame. Used only to keep evidence-frame selection off a noisy frame
    /// (see `SportsSignals.evidenceCoreConfMin`) -- it does not gate any of
    /// the signal values above, which already have their own confMin gate in
    /// `SportsSignals.xy`.
    var reliable: Bool = true
}

struct FeaturePack {
    var n: Int
    var fps: Double
    var stanceWidth: Double
    var stanceWidthStd: Double
    var kneeFlexMean: Double
    var kneeFlexAmp: Double
    var kneeFlexFreq: Double
    var upperQuiet: Double
    var inwardLean: Double
    var turnFreq: Double
    var fallLine: Double
    var backseat: Double
    var kneeValgus: Double
    var hipIrProxy: Double
    var handsLow: Double
    var gazeOk: Double?
    var footOk: Bool
    var quality: Double
    var series: [FrameSample]
    var hipXMean: Double = 0
}

struct AssessFrame {
    var tMs: Double
    var blaze33: [BlazeJoint]
}

enum SportsSignals {
    static let lShoulder = 11
    static let rShoulder = 12
    static let lHip = 23
    static let rHip = 24
    static let lKnee = 25
    static let rKnee = 26
    static let lAnkle = 27
    static let rAnkle = 28
    static let lFoot = 31
    static let rFoot = 32
    static let lWrist = 15
    static let rWrist = 16
    static let nose = 0
    static let confMin: Float = 0.25
    /// A frame can clear `confMin`'s gate (so it still contributes a value)
    /// yet have a core joint tracked so weakly -- occluded by snow spray,
    /// motion blur, a mid-turn self-occlusion -- that its coordinates are
    /// noise rather than signal. That noise then reads as "the most extreme
    /// frame" and gets handed to the coach as photographic evidence of a
    /// fault that was never there. Evidence selection (unlike the signal
    /// value itself) needs a stricter bar: see `Assess.evidenceMs`'s use of
    /// `FrameSample.reliable`.
    static let evidenceCoreConfMin: Float = 0.5
    static let coreLandmarks = [lShoulder, rShoulder, lHip, rHip, lKnee, rKnee, lAnkle, rAnkle]

    private static let clipSignals: Set<String> = [
        "stance_width",
        "stance_width_std",
        "knee_flex_mean",
        "knee_flex_amp",
        "knee_flex_freq",
        "upper_quiet",
        "inward_lean",
        "turn_freq",
        "fall_line",
        "backseat",
        "knee_valgus",
        "hip_ir_proxy",
        "hands_low",
        "gaze_ok",
    ]

    static func extractFeatures(_ frames: [AssessFrame], fpsIn: Double) -> FeaturePack {
        let fps = fpsIn > 1.0 ? fpsIn : 15.0
        var stance: [Double] = []
        var knees: [Double] = []
        var leans: [Double] = []
        var quiet: [Double] = []
        var hipsX: [Double] = []
        var hipsY: [Double] = []
        var back: [Double] = []
        var vis: [Double] = []
        var valgus: [Double] = []
        var hipIr: [Double] = []
        var hands: [Double] = []
        var gaze: [Double] = []
        var series: [FrameSample] = []
        var footHits = 0
        for frame in frames {
            guard let lh = xy(frame, lHip), let rh = xy(frame, rHip) else { continue }
            let la = xy(frame, lAnkle)
            let ra = xy(frame, rAnkle)
            let lk = xy(frame, lKnee)
            let rk = xy(frame, rKnee)
            let ls = xy(frame, lShoulder)
            let rs = xy(frame, rShoulder)
            let lf = xy(frame, lFoot)
            let rf = xy(frame, rFoot)
            let lw = xy(frame, lWrist)
            let rw = xy(frame, rWrist)
            let nosePt = xy(frame, nose)
            let hipW = abs(lh[0] - rh[0]) + 1e-3
            if let la, let ra {
                stance.append(abs(la[0] - ra[0]) / hipW)
            }
            if lf != nil && rf != nil {
                footHits += 1
            }
            if let lk, let rk, let la, let ra {
                let kneeSpan = abs(lk[0] - rk[0])
                let ankleSpan = abs(la[0] - ra[0]) + 1e-3
                hipIr.append(max(0.0, 1.0 - kneeSpan / ankleSpan))
                valgus.append((abs(lk[0] - la[0]) + abs(rk[0] - ra[0])) / (2.0 * hipW))
            }
            if let lk, let la {
                knees.append(SportsMath.angleDeg(ax: lh[0], ay: lh[1], bx: lk[0], by: lk[1], cx: la[0], cy: la[1]))
            }
            if let rk, let ra {
                knees.append(SportsMath.angleDeg(ax: rh[0], ay: rh[1], bx: rk[0], by: rk[1], cx: ra[0], cy: ra[1]))
            }
            if let ls, let rs {
                let shoulderMid = 0.5 * (ls[0] + rs[0])
                let hipMid = 0.5 * (lh[0] + rh[0])
                leans.append((shoulderMid - hipMid) / hipW)
                let shAng = atan2(rs[1] - ls[1], rs[0] - ls[0] + 1e-6)
                let hpAng = atan2(rh[1] - lh[1], rh[0] - lh[0] + 1e-6)
                quiet.append(abs(shAng - hpAng))
                vis.append(min(ls[2], min(rs[2], min(lh[2], rh[2]))))
                if let lw, let rw {
                    let shY = 0.5 * (ls[1] + rs[1])
                    let wrY = 0.5 * (lw[1] + rw[1])
                    hands.append(wrY >= shY ? 1.0 : 0.0)
                }
            }
            if let nosePt {
                gaze.append(nosePt[2] >= 0.4 ? 1.0 : 0.0)
            }
            hipsX.append(0.5 * (lh[0] + rh[0]))
            hipsY.append(0.5 * (lh[1] + rh[1]))
            if let la, let ra {
                let ankleY = 0.5 * (la[1] + ra[1])
                let hipY = 0.5 * (lh[1] + rh[1])
                let torso = abs(
                    hipsY.last! - ((ls != nil && rs != nil) ? (ls![1] + rs![1]) * 0.5 : hipY)
                ) + 1e-3
                back.append((hipY - ankleY) / torso)
            }
            var frameFlex: [Double] = []
            if let lk, let la {
                let leftK = SportsMath.angleDeg(ax: lh[0], ay: lh[1], bx: lk[0], by: lk[1], cx: la[0], cy: la[1])
                if leftK.isFinite {
                    frameFlex.append(180.0 - leftK)
                }
            }
            if let rk, let ra {
                let rightK = SportsMath.angleDeg(ax: rh[0], ay: rh[1], bx: rk[0], by: rk[1], cx: ra[0], cy: ra[1])
                if rightK.isFinite {
                    frameFlex.append(180.0 - rightK)
                }
            }
            let flexNow: Double? = frameFlex.isEmpty ? nil : frameFlex.reduce(0, +) / Double(frameFlex.count)
            series.append(
                FrameSample(
                    tMs: frame.tMs,
                    stanceWidth: (la != nil && ra != nil) ? stance.last : nil,
                    kneeFlex: flexNow,
                    inwardLean: (ls != nil && rs != nil) ? leans.last : nil,
                    backseat: (la != nil && ra != nil) ? back.last : nil,
                    kneeValgus: (!valgus.isEmpty && lk != nil && rk != nil && la != nil && ra != nil)
                        ? valgus.last : nil,
                    hipIrProxy: (!hipIr.isEmpty && lk != nil && rk != nil && la != nil && ra != nil)
                        ? hipIr.last : nil,
                    handsLow: (lw != nil && rw != nil) ? hands.last : nil,
                    gazeOk: nosePt != nil ? gaze.last : nil,
                    quiet: (ls != nil && rs != nil) ? quiet.last : nil,
                    hipX: hipsX.last,
                    hipY: hipsY.last,
                    reliable: isReliable(frame)
                )
            )
        }
        let n = max(series.count, 1)
        let stanceA = stance.isEmpty ? [1.0] : stance
        let kneeFinite = knees.filter { $0.isFinite }
        let kneeA = kneeFinite.isEmpty ? [160.0] : kneeFinite
        let flex = kneeA.map { 180.0 - $0 }
        let quietA = quiet.isEmpty ? [0.2] : quiet
        let leanA = leans.isEmpty ? [0.0] : leans
        let hx = hipsX
        let hy = hipsY
        let turnFreq: Double
        if hx.count > 4 {
            let mu = SportsMath.mean(hx)
            turnFreq = SportsMath.zeroCrossFreq(hx.map { $0 - mu }, fps: fps)
        } else {
            turnFreq = 0
        }
        let kneeFreq: Double
        if flex.count > 4 {
            let mu = SportsMath.mean(flex)
            kneeFreq = SportsMath.zeroCrossFreq(flex.map { $0 - mu }, fps: fps)
        } else {
            kneeFreq = 0
        }
        var fall = 0.0
        if hx.count > 2 && hy.count > 2 {
            let dx = SportsMath.std(hx)
            let dy = SportsMath.std(hy) + 1e-3
            fall = dx / dy
        }
        let backA = back.isEmpty ? [0.0] : back
        let quality = vis.isEmpty ? 0.0 : vis.reduce(0, +) / Double(vis.count)
        let valA = valgus.isEmpty ? [0.2] : valgus
        let irA = hipIr.isEmpty ? [0.0] : hipIr
        let handA = hands
        let gazeScore: Double? = gaze.isEmpty ? nil : gaze.reduce(0, +) / Double(gaze.count)
        return FeaturePack(
            n: n,
            fps: fps,
            stanceWidth: SportsMath.median(stanceA),
            stanceWidthStd: SportsMath.std(stanceA),
            kneeFlexMean: SportsMath.median(flex),
            kneeFlexAmp: SportsMath.percentile(flex, 90) - SportsMath.percentile(flex, 10),
            kneeFlexFreq: kneeFreq,
            upperQuiet: SportsMath.std(quietA),
            inwardLean: SportsMath.mean(leanA.map { abs($0) }),
            turnFreq: turnFreq,
            fallLine: fall,
            backseat: SportsMath.median(backA),
            kneeValgus: SportsMath.median(valA),
            hipIrProxy: SportsMath.median(irA),
            handsLow: handA.isEmpty ? 0.0 : SportsMath.mean(handA),
            gazeOk: gazeScore,
            footOk: footHits >= max(2, n / 8),
            quality: quality,
            series: series,
            hipXMean: hx.isEmpty ? 0.0 : SportsMath.mean(hx)
        )
    }

    static func signalValue(_ pack: FeaturePack, name: String) -> Double? {
        let mapping: [String: Double?] = [
            "stance_width": pack.stanceWidth,
            "stance_width_std": pack.stanceWidthStd,
            "knee_flex_mean": pack.kneeFlexMean,
            "knee_flex_amp": pack.kneeFlexAmp,
            "knee_flex_freq": pack.kneeFlexFreq,
            "upper_quiet": pack.upperQuiet,
            "inward_lean": pack.inwardLean,
            "turn_freq": pack.turnFreq,
            "fall_line": pack.fallLine,
            "backseat": pack.backseat,
            "knee_valgus": pack.kneeValgus,
            "hip_ir_proxy": pack.hipIrProxy,
            "hands_low": pack.handsLow,
            "gaze_ok": pack.gazeOk,
        ]
        guard clipSignals.contains(name), mapping.keys.contains(name) else { return nil }
        if name.hasPrefix("stance") && !pack.footOk {
            return nil
        }
        if (name == "knee_valgus" || name == "hip_ir_proxy") && !pack.footOk {
            return nil
        }
        return mapping[name]!
    }

    static func sampleSignal(_ sample: FrameSample, name: String) -> Double? {
        switch name {
        case "stance_width": return sample.stanceWidth
        case "knee_flex_mean": return sample.kneeFlex
        case "inward_lean": return sample.inwardLean.map { abs($0) }
        case "backseat": return sample.backseat
        case "knee_valgus": return sample.kneeValgus
        case "hip_ir_proxy": return sample.hipIrProxy
        case "hands_low": return sample.handsLow
        case "gaze_ok": return sample.gazeOk
        case "upper_quiet": return sample.quiet
        default: return nil
        }
    }

    /// See `evidenceCoreConfMin`: true only if every core landmark clears
    /// that stricter bar in this frame.
    private static func isReliable(_ frame: AssessFrame) -> Bool {
        guard frame.blaze33.count >= 33 else { return false }
        for idx in coreLandmarks where frame.blaze33[idx].confidence < evidenceCoreConfMin {
            return false
        }
        return true
    }

    private static func xy(_ frame: AssessFrame, _ index: Int) -> [Double]? {
        guard frame.blaze33.count >= 33 else { return nil }
        let joint = frame.blaze33[index]
        if joint.confidence < confMin { return nil }
        return [Double(joint.x), Double(joint.y), Double(joint.confidence)]
    }
}
