"""Synthetic ``ClipAnalysis`` fixtures for the v3 measurement-layer tests.

Not a test module (no ``test_`` prefix, so pytest does not collect it). Every
fixture is built programmatically from a small kinematic model so the expected
answers are known in closed form:

* the hips descend the frame at a constant rate with no lateral drift, so the
  smoothed path tangent is image-down and the steering angle comes purely from
  the swing of the ankle midline;
* the ankle midline swings as ``swing_px * sin(2*pi*turn_hz*t)``, so zero
  crossings — and therefore turn boundaries — land on multiples of
  ``1/(2*turn_hz)`` seconds;
* knees are placed to hit an exact target knee flexion, so flexion range and
  flexion rate are known;
* hip width is derived from a target camera azimuth through the same
  anthropometric aspect prior the measurement layer uses, so ``view_class`` is
  deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)

BLAZE_N = 33
#: Same constant as ``core.sports.metrics.ASPECT_FRONTAL_DEFAULT``; duplicated
#: here on purpose so a fixture change cannot silently track a code change.
ASPECT_FRONTAL = 0.191 / 0.53


@dataclass
class SkierParams:
    """Knobs for the synthetic skier. Defaults are a clean parallel skier."""

    clip_id: str = "synthetic"
    fps: float = 15.0
    duration_s: float = 12.0
    #: Sine frequency of the steering swing. One cycle is two turns, so
    #: ``0.5`` Hz gives 1.0 s turns and a turn rate of 1.0 Hz.
    turn_hz: float = 0.5
    swing_px: float = 80.0
    hip_x: float = 320.0
    hip_y0: float = 120.0
    descent_px_s: float = 90.0
    leg_drop_px: float = 190.0
    bob_px: float = 10.0
    azimuth_deg: float = 45.0
    stance_px: float = 55.0
    flexion_left_deg: float = 25.0
    flexion_right_deg: float = 25.0
    flexion_amp_deg: float = 12.0
    #: Per-side overrides for the flexion swing; ``None`` means use the shared
    #: ``flexion_amp_deg``.
    flexion_amp_left_deg: float | None = None
    flexion_amp_right_deg: float | None = None
    incl_px: float = 25.0
    torso_len_px: float = 90.0
    shoulder_w_ratio: float = 1.35
    shoulder_tilt_px: float = 6.0
    foot_len_px: float = 34.0
    toe_base_deg: float = 12.0
    #: Constant half-splay applied to both feet (wedge angle = 2x this).
    wedge_half_deg: float = 0.0
    #: Centres (seconds) at which an extra stem splay is applied.
    stem_times_s: tuple[float, ...] = ()
    stem_half_width_s: float = 0.25
    stem_half_deg: float = 13.0
    knee_bias_px: tuple[float, float] = (0.0, 0.0)
    hands_forward_px: float = 30.0
    pole_flick_px: float = 0.0
    confidence: float = 0.95
    drop_landmarks: tuple[int, ...] = ()
    frame_w: int = 640
    frame_h: int = 480


def _core(t_ms: float, params: SkierParams) -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=t_ms,
            width=params.frame_w,
            height=params.frame_h,
        ),
        detections=[],
        poses=[],
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name="pose_landmarker_full.task",
            latency_ms=1.0,
            device="cpu",
        ),
        error=None,
    )


def _knee_offset(distance: float, flexion_deg: float) -> float:
    """Perpendicular knee offset that yields ``flexion_deg`` at the knee.

    With equal thigh and shank, a knee placed ``b`` off the hip-ankle midpoint
    makes the knee angle ``2*atan2(d/2, b)``; inverting for
    ``flexion = 180 - angle`` gives the offset below.
    """
    flexion = min(max(flexion_deg, 1.0), 170.0)
    half_angle = math.radians((180.0 - flexion) / 2.0)
    return (distance / 2.0) / max(math.tan(half_angle), 1e-6)


def _leg_len_px(params: SkierParams) -> float:
    """Segment-sum leg length at the neutral swing position."""
    mean_flex = 0.5 * (params.flexion_left_deg + params.flexion_right_deg)
    half_angle = math.radians((180.0 - mean_flex) / 2.0)
    return params.leg_drop_px / max(math.sin(half_angle), 1e-6)


def hip_width_px(params: SkierParams) -> float:
    """Hip width that makes ``estimate_view`` report ``params.azimuth_deg``."""
    aspect = ASPECT_FRONTAL * math.sin(math.radians(params.azimuth_deg))
    return aspect * _leg_len_px(params)


def _stem_extra(params: SkierParams, t_s: float) -> float:
    for centre in params.stem_times_s:
        if abs(t_s - centre) <= params.stem_half_width_s:
            return params.stem_half_deg
    return 0.0


def _frame_joints(params: SkierParams, t_s: float) -> list[BlazeJoint]:
    phase = 2.0 * math.pi * params.turn_hz * t_s
    flex_phase = 2.0 * phase
    hip_w = hip_width_px(params)
    hip_x = params.hip_x
    hip_y = params.hip_y0 + params.descent_px_s * t_s + params.bob_px * math.sin(
        flex_phase
    )
    ankle_centre = hip_x + params.swing_px * math.sin(phase)
    ankle_y = hip_y + params.leg_drop_px

    pts: list[tuple[float, float]] = [(hip_x, hip_y)] * BLAZE_N

    hip_l = (hip_x - hip_w / 2.0, hip_y)
    hip_r = (hip_x + hip_w / 2.0, hip_y)
    ankle_l = (ankle_centre - params.stance_px / 2.0, ankle_y)
    ankle_r = (ankle_centre + params.stance_px / 2.0, ankle_y)

    knees: list[tuple[float, float]] = []
    amp_l = (
        params.flexion_amp_deg
        if params.flexion_amp_left_deg is None
        else params.flexion_amp_left_deg
    )
    amp_r = (
        params.flexion_amp_deg
        if params.flexion_amp_right_deg is None
        else params.flexion_amp_right_deg
    )
    flexions = (
        params.flexion_left_deg + amp_l * math.sin(flex_phase),
        params.flexion_right_deg + amp_r * math.sin(flex_phase),
    )
    for (hip, ankle, flexion, bias) in (
        (hip_l, ankle_l, flexions[0], params.knee_bias_px[0]),
        (hip_r, ankle_r, flexions[1], params.knee_bias_px[1]),
    ):
        dx = ankle[0] - hip[0]
        dy = ankle[1] - hip[1]
        dist = math.hypot(dx, dy)
        offset = _knee_offset(dist, flexion)
        # Perpendicular pointing toward +x, i.e. the direction of travel: a
        # normally flexed knee sits ahead of the hip-ankle line.
        px, py = dy / dist, -dx / dist
        mid = ((hip[0] + ankle[0]) / 2.0, (hip[1] + ankle[1]) / 2.0)
        knees.append((mid[0] + offset * px + bias, mid[1] + offset * py))

    sh_mid_x = hip_x - params.incl_px * math.sin(phase)
    sh_y = hip_y - params.torso_len_px
    sh_w = hip_w * params.shoulder_w_ratio
    tilt = params.shoulder_tilt_px * math.sin(phase)
    shoulder_l = (sh_mid_x - sh_w / 2.0, sh_y + tilt)
    shoulder_r = (sh_mid_x + sh_w / 2.0, sh_y - tilt)

    flick = 0.0
    if params.pole_flick_px:
        for k in range(1, int(params.duration_s * 2.0 * params.turn_hz) + 2):
            centre = k / (2.0 * params.turn_hz)
            flick += params.pole_flick_px * math.exp(
                -(((t_s - centre) / 0.12) ** 2)
            )
    wrist_y = hip_y - 25.0
    wrist_l = (hip_x + params.hands_forward_px - 12.0 + flick, wrist_y)
    wrist_r = (hip_x + params.hands_forward_px + 12.0 + flick, wrist_y)
    elbow_l = (
        0.5 * (shoulder_l[0] + wrist_l[0]),
        0.5 * (shoulder_l[1] + wrist_l[1]),
    )
    elbow_r = (
        0.5 * (shoulder_r[0] + wrist_r[0]),
        0.5 * (shoulder_r[1] + wrist_r[1]),
    )

    extra = _stem_extra(params, t_s)
    splay = params.wedge_half_deg + extra
    feet: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for ankle, sign in ((ankle_l, -1.0), (ankle_r, 1.0)):
        angle = math.radians(params.toe_base_deg + sign * splay)
        vx = params.foot_len_px * math.cos(angle)
        vy = params.foot_len_px * math.sin(angle)
        toe = (ankle[0] + vx, ankle[1] + vy)
        heel = (ankle[0] - 0.3 * vx, ankle[1] - 0.3 * vy + 6.0)
        feet.append((heel, toe))

    nose = (sh_mid_x, sh_y - 35.0)
    for i in range(1, 11):
        pts[i] = nose
    pts[0] = nose
    pts[11] = shoulder_l
    pts[12] = shoulder_r
    pts[13] = elbow_l
    pts[14] = elbow_r
    pts[15] = wrist_l
    pts[16] = wrist_r
    for i in (17, 19, 21):
        pts[i] = wrist_l
    for i in (18, 20, 22):
        pts[i] = wrist_r
    pts[23] = hip_l
    pts[24] = hip_r
    pts[25] = knees[0]
    pts[26] = knees[1]
    pts[27] = ankle_l
    pts[28] = ankle_r
    pts[29] = feet[0][0]
    pts[30] = feet[1][0]
    pts[31] = feet[0][1]
    pts[32] = feet[1][1]

    out: list[BlazeJoint] = []
    for i in range(BLAZE_N):
        x, y = pts[i]
        conf = 0.0 if i in params.drop_landmarks else params.confidence
        out.append(BlazeJoint(x=float(x), y=float(y), z=0.0, confidence=float(conf)))
    return out


def make_clip(params: SkierParams) -> ClipAnalysis:
    """Build a ``ClipAnalysis`` from the kinematic model."""
    n = max(int(round(params.duration_s * params.fps)), 1)
    frames: list[AnalyzedFrame] = []
    for i in range(n):
        t_s = i / params.fps
        t_ms = 1000.0 * t_s
        frames.append(
            AnalyzedFrame(
                t_ms=t_ms,
                result=_core(t_ms, params),
                blaze33=_frame_joints(params, t_s),
            )
        )
    return ClipAnalysis(
        clip_id=params.clip_id, fps=params.fps, frame_count=n, frames=frames
    )


def stride_sample(analysis: ClipAnalysis, stride: int) -> ClipAnalysis:
    """Keep every ``stride``-th frame, leaving ``fps`` at the *source* rate.

    This is exactly what ``clients/windows/pipeline/analyze.py`` produces with
    ``FRAME_STRIDE = 2``, and the shape that made v2 report doubled frequencies.
    """
    frames = analysis.frames[::stride]
    return ClipAnalysis(
        clip_id=f"{analysis.clip_id}-stride{stride}",
        fps=analysis.fps,
        frame_count=len(frames),
        frames=frames,
    )


def no_pose_clip(n: int = 8, fps: float = 15.0) -> ClipAnalysis:
    """Frames with no ``blaze33`` at all."""
    params = SkierParams(fps=fps)
    frames = [
        AnalyzedFrame(t_ms=1000.0 * i / fps, result=_core(1000.0 * i / fps, params))
        for i in range(n)
    ]
    return ClipAnalysis(clip_id="no-pose", fps=fps, frame_count=n, frames=frames)


# --- named fixtures ---------------------------------------------------------


def parallel_skier(**overrides: object) -> ClipAnalysis:
    """Clean parallel turns, quarter view, symmetric."""
    return make_clip(replace(SkierParams(clip_id="parallel"), **overrides))


def wedge_skier(**overrides: object) -> ClipAnalysis:
    """Wedge held through every turn, wide stance."""
    base = SkierParams(
        clip_id="wedge",
        wedge_half_deg=14.0,
        stance_px=95.0,
        swing_px=55.0,
        flexion_left_deg=14.0,
        flexion_right_deg=14.0,
        flexion_amp_deg=5.0,
    )
    return make_clip(replace(base, **overrides))


def profile_view_skier(**overrides: object) -> ClipAnalysis:
    """Same motion filmed almost side-on: azimuth well under 25 degrees."""
    base = SkierParams(clip_id="profile", azimuth_deg=10.0)
    return make_clip(replace(base, **overrides))


def frontal_view_skier(**overrides: object) -> ClipAnalysis:
    """Same motion filmed almost face-on: azimuth well over 65 degrees."""
    base = SkierParams(clip_id="frontal", azimuth_deg=85.0)
    return make_clip(replace(base, **overrides))


def stemmed_skier(**overrides: object) -> ClipAnalysis:
    """Parallel except for a stem at three of the twelve edge changes.

    Boundaries fall on whole seconds, so stemming the transitions centred on
    3 s, 5 s and 7 s marks exactly three turns.
    """
    base = SkierParams(
        clip_id="stemmed", stem_times_s=(3.0, 5.0, 7.0), stem_half_deg=13.0
    )
    return make_clip(replace(base, **overrides))


def asymmetric_skier(**overrides: object) -> ClipAnalysis:
    """Deep, actively flexing left leg; nearly straight, passive right leg."""
    base = SkierParams(
        clip_id="asymmetric",
        flexion_left_deg=45.0,
        flexion_right_deg=11.0,
        flexion_amp_left_deg=16.0,
        flexion_amp_right_deg=2.0,
        knee_bias_px=(16.0, 0.0),
    )
    return make_clip(replace(base, **overrides))


def poling_skier(**overrides: object) -> ClipAnalysis:
    """Parallel turns with a wrist flick at every transition."""
    base = SkierParams(clip_id="poling", pole_flick_px=42.0)
    return make_clip(replace(base, **overrides))


def short_clip(**overrides: object) -> ClipAnalysis:
    """Five frames: nothing rate-based or turn-based is measurable."""
    base = SkierParams(clip_id="short", duration_s=5.0 / 15.0)
    return make_clip(replace(base, **overrides))


def low_confidence_clip(**overrides: object) -> ClipAnalysis:
    """Every landmark below the 0.25 confidence gate."""
    base = SkierParams(clip_id="low-conf", confidence=0.05)
    return make_clip(replace(base, **overrides))


def traverse_clip(**overrides: object) -> ClipAnalysis:
    """A straight run: no steering swing at all, so no turns to segment."""
    base = SkierParams(clip_id="traverse", swing_px=0.0, incl_px=0.0)
    return make_clip(replace(base, **overrides))
