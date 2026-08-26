"""BlazePose 33 kinematic signals for curriculum thresholds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from schemas.clip_analysis import ClipAnalysis

L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_FOOT, R_FOOT = 31, 32
L_WRIST, R_WRIST = 15, 16
NOSE = 0
CONF_MIN = 0.25


@dataclass
class FrameSample:
    t_ms: float
    stance_width: float | None = None
    knee_flex: float | None = None
    inward_lean: float | None = None
    backseat: float | None = None
    knee_valgus: float | None = None
    hip_ir_proxy: float | None = None
    hands_low: float | None = None
    gaze_ok: float | None = None
    quiet: float | None = None
    hip_x: float | None = None
    hip_y: float | None = None


@dataclass
class FeaturePack:
    n: int
    fps: float
    stance_width: float
    stance_width_std: float
    knee_flex_mean: float
    knee_flex_amp: float
    knee_flex_freq: float
    upper_quiet: float
    inward_lean: float
    turn_freq: float
    fall_line: float
    backseat: float
    knee_valgus: float
    hip_ir_proxy: float
    hands_low: float
    gaze_ok: float | None
    foot_ok: bool
    quality: float
    series: list[FrameSample]
    hip_x_mean: float = 0.0


def _xy(frame, index: int) -> tuple[float, float, float] | None:
    if frame.blaze33 is None or len(frame.blaze33) < 33:
        return None
    joint = frame.blaze33[index]
    if joint.confidence < CONF_MIN:
        return None
    return joint.x, joint.y, joint.confidence


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cos = float(np.clip(np.dot(ba, bc) / (nba * nbc), -1.0, 1.0))
    return float(np.degrees(np.arccos(cos)))


def extract_features(analysis: ClipAnalysis) -> FeaturePack:
    fps = analysis.fps if analysis.fps > 1.0 else 15.0
    stance: list[float] = []
    knees: list[float] = []
    leans: list[float] = []
    quiet: list[float] = []
    hips_x: list[float] = []
    hips_y: list[float] = []
    back: list[float] = []
    vis: list[float] = []
    valgus: list[float] = []
    hip_ir: list[float] = []
    hands: list[float] = []
    gaze: list[float] = []
    series: list[FrameSample] = []
    foot_hits = 0
    for frame in analysis.frames:
        lh = _xy(frame, L_HIP)
        rh = _xy(frame, R_HIP)
        la = _xy(frame, L_ANKLE)
        ra = _xy(frame, R_ANKLE)
        lk = _xy(frame, L_KNEE)
        rk = _xy(frame, R_KNEE)
        ls = _xy(frame, L_SHOULDER)
        rs = _xy(frame, R_SHOULDER)
        lf = _xy(frame, L_FOOT)
        rf = _xy(frame, R_FOOT)
        lw = _xy(frame, L_WRIST)
        rw = _xy(frame, R_WRIST)
        nose = _xy(frame, NOSE)
        if lh is None or rh is None:
            continue
        hip_w = abs(lh[0] - rh[0]) + 1e-3
        if la is not None and ra is not None:
            stance.append(abs(la[0] - ra[0]) / hip_w)
        if lf is not None and rf is not None:
            foot_hits += 1
        if (
            lk is not None
            and rk is not None
            and la is not None
            and ra is not None
        ):
            knee_span = abs(lk[0] - rk[0])
            ankle_span = abs(la[0] - ra[0]) + 1e-3
            hip_ir.append(max(0.0, 1.0 - knee_span / ankle_span))
            valgus.append(
                (
                    abs(lk[0] - la[0]) + abs(rk[0] - ra[0])
                )
                / (2.0 * hip_w)
            )
        if lk is not None and la is not None:
            knees.append(
                _angle(
                    np.array([lh[0], lh[1]]),
                    np.array([lk[0], lk[1]]),
                    np.array([la[0], la[1]]),
                )
            )
        if rk is not None and ra is not None:
            knees.append(
                _angle(
                    np.array([rh[0], rh[1]]),
                    np.array([rk[0], rk[1]]),
                    np.array([ra[0], ra[1]]),
                )
            )
        if ls is not None and rs is not None:
            shoulder_mid = 0.5 * (ls[0] + rs[0])
            hip_mid = 0.5 * (lh[0] + rh[0])
            leans.append((shoulder_mid - hip_mid) / hip_w)
            sh_ang = np.arctan2(rs[1] - ls[1], rs[0] - ls[0] + 1e-6)
            hp_ang = np.arctan2(rh[1] - lh[1], rh[0] - lh[0] + 1e-6)
            quiet.append(abs(sh_ang - hp_ang))
            vis.append(min(ls[2], rs[2], lh[2], rh[2]))
            if lw is not None and rw is not None:
                sh_y = 0.5 * (ls[1] + rs[1])
                wr_y = 0.5 * (lw[1] + rw[1])
                hands.append(1.0 if wr_y >= sh_y else 0.0)
        if nose is not None:
            gaze.append(1.0 if nose[2] >= 0.4 else 0.0)
        hips_x.append(0.5 * (lh[0] + rh[0]))
        hips_y.append(0.5 * (lh[1] + rh[1]))
        if la is not None and ra is not None:
            ankle_y = 0.5 * (la[1] + ra[1])
            hip_y = 0.5 * (lh[1] + rh[1])
            torso = abs(hips_y[-1] - ((ls[1] + rs[1]) * 0.5 if ls and rs else hip_y)) + 1e-3
            back.append((hip_y - ankle_y) / torso)
        flex_now: float | None = None
        frame_flex: list[float] = []
        if lk is not None and la is not None:
            left_k = _angle(
                np.array([lh[0], lh[1]]),
                np.array([lk[0], lk[1]]),
                np.array([la[0], la[1]]),
            )
            if np.isfinite(left_k):
                frame_flex.append(180.0 - left_k)
        if rk is not None and ra is not None:
            right_k = _angle(
                np.array([rh[0], rh[1]]),
                np.array([rk[0], rk[1]]),
                np.array([ra[0], ra[1]]),
            )
            if np.isfinite(right_k):
                frame_flex.append(180.0 - right_k)
        if frame_flex:
            flex_now = float(np.mean(frame_flex))
        series.append(
            FrameSample(
                t_ms=float(frame.t_ms),
                stance_width=(
                    stance[-1] if la is not None and ra is not None else None
                ),
                knee_flex=flex_now,
                inward_lean=leans[-1] if ls is not None and rs is not None else None,
                backseat=back[-1] if la is not None and ra is not None else None,
                knee_valgus=valgus[-1] if valgus and lk and rk and la and ra else None,
                hip_ir_proxy=hip_ir[-1] if hip_ir and lk and rk and la and ra else None,
                hands_low=hands[-1] if lw is not None and rw is not None else None,
                gaze_ok=gaze[-1] if nose is not None else None,
                quiet=quiet[-1] if ls is not None and rs is not None else None,
                hip_x=hips_x[-1] if hips_x else None,
                hip_y=hips_y[-1] if hips_y else None,
            )
        )
    n = max(len(series), 1)
    stance_a = np.array(stance, dtype=np.float64) if stance else np.array([1.0])
    knee_a = np.array([k for k in knees if np.isfinite(k)], dtype=np.float64)
    if knee_a.size == 0:
        knee_a = np.array([160.0])
    flex = 180.0 - knee_a
    quiet_a = np.array(quiet, dtype=np.float64) if quiet else np.array([0.2])
    lean_a = np.array(leans, dtype=np.float64) if leans else np.array([0.0])
    hx = np.array(hips_x, dtype=np.float64)
    hy = np.array(hips_y, dtype=np.float64)
    turn_freq = _zero_cross_freq(hx - np.mean(hx), fps) if hx.size > 4 else 0.0
    knee_freq = _zero_cross_freq(flex - np.mean(flex), fps) if flex.size > 4 else 0.0
    fall = 0.0
    if hx.size > 2 and hy.size > 2:
        dx = float(np.std(hx))
        dy = float(np.std(hy) + 1e-3)
        fall = dx / dy
    back_a = np.array(back, dtype=np.float64) if back else np.array([0.0])
    quality = float(np.mean(vis)) if vis else 0.0
    val_a = np.array(valgus, dtype=np.float64) if valgus else np.array([0.2])
    ir_a = np.array(hip_ir, dtype=np.float64) if hip_ir else np.array([0.0])
    hand_a = np.array(hands, dtype=np.float64) if hands else np.array([])
    gaze_score: float | None
    if gaze:
        gaze_score = float(np.mean(gaze))
    else:
        gaze_score = None
    pack = FeaturePack(
        n=n,
        fps=fps,
        stance_width=float(np.median(stance_a)),
        stance_width_std=float(np.std(stance_a)),
        knee_flex_mean=float(np.median(flex)),
        knee_flex_amp=float(np.percentile(flex, 90) - np.percentile(flex, 10)),
        knee_flex_freq=knee_freq,
        upper_quiet=float(np.std(quiet_a)),
        inward_lean=float(np.mean(np.abs(lean_a))),
        turn_freq=turn_freq,
        fall_line=fall,
        backseat=float(np.median(back_a)),
        knee_valgus=float(np.median(val_a)),
        hip_ir_proxy=float(np.median(ir_a)),
        hands_low=float(np.mean(hand_a)) if hand_a.size else 0.0,
        gaze_ok=gaze_score,
        foot_ok=foot_hits >= max(2, n // 8),
        quality=quality,
        series=series,
        hip_x_mean=float(np.mean(hx)) if hx.size else 0.0,
    )
    return pack


def _zero_cross_freq(series: np.ndarray, fps: float) -> float:
    if series.size < 4:
        return 0.0
    sign = np.sign(series)
    sign[sign == 0] = 1
    crosses = int(np.sum(sign[1:] * sign[:-1] < 0))
    dur = series.size / max(fps, 1.0)
    return 0.5 * crosses / max(dur, 1e-3)


CLIP_SIGNALS = (
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
)


def signal_value(pack: FeaturePack, name: str) -> float | None:
    mapping = {
        "stance_width": pack.stance_width,
        "stance_width_std": pack.stance_width_std,
        "knee_flex_mean": pack.knee_flex_mean,
        "knee_flex_amp": pack.knee_flex_amp,
        "knee_flex_freq": pack.knee_flex_freq,
        "upper_quiet": pack.upper_quiet,
        "inward_lean": pack.inward_lean,
        "turn_freq": pack.turn_freq,
        "fall_line": pack.fall_line,
        "backseat": pack.backseat,
        "knee_valgus": pack.knee_valgus,
        "hip_ir_proxy": pack.hip_ir_proxy,
        "hands_low": pack.hands_low,
        "gaze_ok": pack.gaze_ok,
    }
    if name not in CLIP_SIGNALS or name not in mapping:
        return None
    if name.startswith("stance") and not pack.foot_ok:
        return None
    if name in {"knee_valgus", "hip_ir_proxy"} and not pack.foot_ok:
        return None
    return mapping[name]
