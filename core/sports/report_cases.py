"""Synthetic clips for report review, and the v3 archetype generator.

Two generations of fixture live here.

``joints`` / ``clip_for`` build the v2 cases: a handful of static skeletons with
a hip that jumps between a few x positions. They exercise the legacy signal
layer and are kept unchanged so ``classify_legacy`` keeps being tested on
exactly what it was tested on before.

:func:`synth_clip` is the v3 generator. The v3 measurement layer reads turns,
view azimuth, edge angle, flexion and pole touches, none of which a static
skeleton has, so the review cases needed a skier that actually skis:

* the hip travels along image ``+x`` at a constant speed, which is what
  ``metrics._forward_axis`` reads as the fore/aft direction;
* the ankle midline sways sinusoidally about the hip, which is what
  ``turns.steering_signal`` reads as steering — one sine cycle is two turns;
* knees, shoulders, feet, wrists and heels are placed from explicit geometric
  knobs (edge tilt, inclination, angulation, wedge splay, pole spike), so a
  case can be aimed at a stage rather than guessed at.

The knobs are *geometry*, not target metric values: a 2D projection mixes
fore/aft and lateral offsets on the same image axis, exactly as a real quarter
view does, so each case's actual metric values are what the fixtures record.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)

#: ``metrics.ASPECT_FRONTAL_DEFAULT`` — bi-iliac breadth over leg length.
ASPECT_FRONTAL = 0.191 / 0.53
THIGH_FRACTION = 0.45
SHANK_FRACTION = 0.55
TORSO_FRACTION = 0.55
FOOT_LEN_PX = 22.0
MIN_ANGULATION_DEG = 0.5


@dataclass(frozen=True)
class ReportCase:
    case_id: str
    clip_id: str
    expect_stages: tuple[str, ...]
    expect_ready: bool | None
    note: str
    frames: int
    stance: float
    knee_drop: float
    lean: float = 0.0
    hip_swing: float = 0.0
    knee_in_alt: tuple[float, float] | None = None
    drop_feet: bool = False
    min_frames: int | None = None
    #: v3 cases carry a :class:`Skier` instead of the static-skeleton knobs.
    skier: "Skier | None" = None
    athlete: dict | None = None
    scene: dict | None = None
    expect_ambiguous: bool | None = None
    expect_unusable: bool = False
    #: Level ids this athlete has already passed, for the classifier prior and
    #: the tree's completed / locked states.
    passed_levels: tuple[str, ...] = ()


#: The piste spine up to and including dynamic parallel — the history a skier
#: working on short turns or carving would have.
PISTE_HISTORY: tuple[str, ...] = (
    "pizza_glide",
    "pizza",
    "sideslip",
    "wedge_christie",
    "parallel",
    "dynamic_parallel",
)


def history_for(case: ReportCase) -> list[dict]:
    """Minimal stored-report stubs for ``case.passed_levels``."""
    return [
        {
            "stage_id": level_id,
            "ready_for_next_stage": True,
            "score_0_100": 88.0,
            "keypoints": [],
        }
        for level_id in case.passed_levels
    ]


@dataclass(frozen=True)
class Skier:
    """Geometric description of one synthetic skier."""

    frames: int = 180
    fps: float = 15.0
    leg_px: float = 150.0
    #: Camera azimuth: 0 is pure profile, 90 face-on (design §3.1).
    azimuth_deg: float = 45.0
    #: Ankle separation in leg lengths.
    stance: float = 0.30
    #: Sine frequency; one cycle is two turns, so turn_rate ~= 2 * turn_hz.
    turn_hz: float = 0.22
    #: Ankle-midline sway as a fraction of leg length; sets turn amplitude.
    steer_amp: float = 0.35
    wedge_deg: float = 0.0
    edge_deg: float = 8.0
    incl_deg: float = 6.0
    angulation_deg: float = 6.0
    separation_deg: float = 8.0
    counter_rotate: bool = True
    knee_fore_px: float = 6.0
    #: Fore-knee travel amplitude; drives flexion range and rate.
    flex_amp_px: float = 0.0
    #: Hip fore/aft offset in leg lengths, positive = hips ahead of the feet.
    hof_bias: float = 0.06
    #: Hip vertical travel in leg lengths.
    bob: float = 0.0
    #: Wrist forward spike at each transition; drives pole-touch detection.
    pole_spike_px: float = 0.0
    hands_forward_px: float = 30.0
    speed_px_s: float = 90.0
    follow_cam: bool = False
    conf: float = 0.95
    #: Landmark indices to blank out (confidence 0).
    drop: tuple[int, ...] = ()
    phase_shift: float = 0.0
    #: Multiplies the left leg's offsets, to create a real asymmetry.
    left_gain: float = 1.0
    #: Sharpens the steering waveform: ``sign(sin) * |sin| ** power``. Above 1
    #: the skier spends less of the arc at a high steering angle, which is what
    #: a Z-shaped skidded turn looks like to ``turn_shape_index``.
    shape_power: float = 1.0


# ---------------------------------------------------------------------------
# v2 cases (legacy signal layer)
# ---------------------------------------------------------------------------


def _empty_core() -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=0.0,
            width=640,
            height=360,
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


def joints(
    *,
    hip_w: float = 40.0,
    stance: float = 1.5,
    knee_drop: float = 40.0,
    knee_in: float = 0.0,
    lean: float = 0.0,
    hip_x: float = 200.0,
    drop_feet: bool = False,
) -> list[BlazeJoint]:
    mid = hip_x
    lh, rh = mid - hip_w / 2, mid + hip_w / 2
    ankle_span = hip_w * stance
    la, ra = mid - ankle_span / 2, mid + ankle_span / 2
    ls, rs = lh + lean * hip_w, rh + lean * hip_w
    pts = [(0.0, 0.0)] * 33
    pts[0] = (mid, 40.0)
    pts[11] = (ls, 80.0)
    pts[12] = (rs, 80.0)
    pts[15] = (ls, 140.0)
    pts[16] = (rs, 140.0)
    pts[23] = (lh, 160.0)
    pts[24] = (rh, 160.0)
    pts[25] = (lh + knee_in, 160.0 + knee_drop)
    pts[26] = (rh - knee_in, 160.0 + knee_drop)
    pts[27] = (la, 280.0)
    pts[28] = (ra, 280.0)
    pts[31] = (la, 300.0)
    pts[32] = (ra, 300.0)
    out: list[BlazeJoint] = []
    for i in range(33):
        x, y = pts[i]
        conf = 0.0 if drop_feet and i in (27, 28, 31, 32) else 0.95
        out.append(BlazeJoint(x=x, y=y, z=0.0, confidence=conf))
    return out


def clip_for(case: ReportCase) -> ClipAnalysis:
    """Build the clip for a case: v3 generator when it carries a ``Skier``."""
    if case.skier is not None:
        return synth_clip(
            case.skier,
            clip_id=case.clip_id,
            scene=case.scene,
            athlete=case.athlete,
        )
    n = case.min_frames if case.min_frames is not None else case.frames
    seq: list[list[BlazeJoint]] = []
    for i in range(n):
        knee_in = 0.0
        if case.knee_in_alt is not None:
            knee_in = case.knee_in_alt[0] if i % 2 == 0 else case.knee_in_alt[1]
        hip_x = 180.0 + (i % 6) * case.hip_swing if case.hip_swing else 200.0
        seq.append(
            joints(
                stance=case.stance,
                knee_drop=case.knee_drop,
                knee_in=knee_in,
                lean=case.lean,
                hip_x=hip_x,
                drop_feet=case.drop_feet,
            )
        )
    frames = [
        AnalyzedFrame(t_ms=i * 66.0, result=_empty_core(), blaze33=body)
        for i, body in enumerate(seq)
    ]
    return ClipAnalysis(
        clip_id=case.clip_id,
        fps=15.0,
        frame_count=len(frames),
        frames=frames,
        scene=case.scene,
        athlete=case.athlete,
    )


# ---------------------------------------------------------------------------
# v3 generator
# ---------------------------------------------------------------------------


def _shoulder_mid(
    hip: tuple[float, float],
    ankle: tuple[float, float],
    torso: float,
    leg: float,
    incl_deg: float,
    angulation_deg: float,
) -> tuple[float, float]:
    """Place the shoulder midpoint to hit a target inclination *and* angulation.

    ``metrics.build_series`` reads inclination as the shoulder-to-ankle line
    against image down and angulation as that minus the shoulder-to-hip line, so
    both are fixed by one point. Solving for it (rather than nudging a lean
    offset) is what lets a case aim at a banking index, which is the carve gate.
    """
    incl = math.radians(incl_deg)
    torso_angle = math.radians(incl_deg - angulation_deg)
    if abs(incl_deg - (incl_deg - angulation_deg)) < MIN_ANGULATION_DEG:
        return hip[0] - math.tan(incl) * torso, hip[1] - torso
    delta_x = ankle[0] - hip[0]
    denom = math.tan(incl) - math.tan(torso_angle)
    a = (delta_x - leg * math.tan(torso_angle)) / denom
    if not math.isfinite(a) or not (0.4 * (leg + torso) < a < 2.0 * (leg + torso)):
        return hip[0] - math.tan(incl) * torso, hip[1] - torso
    return ankle[0] - a * math.tan(incl), ankle[1] - a


def synth_clip(
    sk: Skier,
    clip_id: str = "synth",
    scene: dict | None = None,
    athlete: dict | None = None,
) -> ClipAnalysis:
    """One synthetic clip from a :class:`Skier`."""
    leg = sk.leg_px
    thigh, shank = leg * THIGH_FRACTION, leg * SHANK_FRACTION
    torso = leg * TORSO_FRACTION
    hip_w = max(6.0, ASPECT_FRONTAL * leg * math.sin(math.radians(sk.azimuth_deg)))
    sin_az = max(
        math.sin(math.radians(sk.azimuth_deg)), math.sin(math.radians(25.0))
    )
    splay = FOOT_LEN_PX * math.tan(math.radians(sk.wedge_deg / 2.0))
    edge_dx = math.tan(math.radians(sk.edge_deg)) * sin_az * shank
    frames: list[AnalyzedFrame] = []
    for i in range(sk.frames):
        seconds = i / sk.fps
        omega = 2.0 * math.pi * sk.turn_hz * seconds + sk.phase_shift
        wave = math.sin(omega)
        phase = math.copysign(abs(wave) ** sk.shape_power, wave)
        turning_left = phase >= 0.0
        lean_sign = -1.0 if turning_left else 1.0
        hip_x = 200.0 + (0.0 if sk.follow_cam else sk.speed_px_s * seconds)
        hip_y = 300.0 + sk.bob * leg * 0.5 * math.cos(2.0 * omega)
        ankle_mid_x = hip_x + sk.steer_amp * leg * phase - sk.hof_bias * leg
        ankle_mid_y = hip_y + leg
        half = 0.5 * sk.stance * leg
        pts = [(0.0, 0.0)] * 33
        pts[23] = (hip_x - hip_w / 2.0, hip_y)
        pts[24] = (hip_x + hip_w / 2.0, hip_y)
        fore = sk.knee_fore_px + sk.flex_amp_px * 0.5 * (1.0 - math.cos(2.0 * omega))
        for ankle_i, sign in ((27, -1.0), (28, +1.0)):
            gain = sk.left_gain if sign < 0 else 1.0
            ax = ankle_mid_x + sign * half
            ay = ankle_mid_y
            pts[ankle_i] = (ax, ay)
            pts[ankle_i + 2] = (ax - 8.0, ay + FOOT_LEN_PX * 0.4)
            pts[ankle_i + 4] = (ax + 8.0 + sign * splay, ay + FOOT_LEN_PX)
            pts[ankle_i - 2] = (
                ax + (fore + lean_sign * edge_dx) * gain,
                ay - shank,
            )
        sh_x, sh_y = _shoulder_mid(
            (hip_x, hip_y),
            (ankle_mid_x, ankle_mid_y),
            torso,
            leg,
            sk.incl_deg * lean_sign,
            sk.angulation_deg * lean_sign,
        )
        sep_sign = -lean_sign if sk.counter_rotate else lean_sign
        sep = math.radians(sk.separation_deg) * sep_sign
        for shoulder_i, sign in ((11, -1.0), (12, +1.0)):
            dx = sign * hip_w / 2.0
            pts[shoulder_i] = (
                sh_x + dx * math.cos(sep),
                sh_y + dx * math.sin(sep),
            )
        pts[0] = (sh_x, sh_y - torso * 0.5)
        spike = sk.pole_spike_px * max(0.0, 1.0 - abs(phase) * 6.0)
        for wrist_i, sign in ((15, -1.0), (16, +1.0)):
            pts[wrist_i] = (
                hip_x + sk.hands_forward_px + spike,
                hip_y - torso * 0.35 + sign * hip_w * 0.4,
            )
            pts[wrist_i - 2] = (
                hip_x + sk.hands_forward_px * 0.4,
                hip_y - torso * 0.5,
            )
        body = [
            BlazeJoint(
                x=pts[k][0],
                y=pts[k][1],
                z=0.0,
                confidence=0.0 if k in sk.drop else sk.conf,
            )
            for k in range(33)
        ]
        frames.append(
            AnalyzedFrame(
                t_ms=i * (1000.0 / sk.fps), result=_empty_core(), blaze33=body
            )
        )
    scene_block = dict(scene or {})
    scene_block.setdefault("fps_effective", sk.fps)
    return ClipAnalysis(
        clip_id=clip_id,
        fps=sk.fps,
        frame_count=len(frames),
        frames=frames,
        scene=scene_block,
        athlete=athlete,
    )


# ---------------------------------------------------------------------------
# archetypes
# ---------------------------------------------------------------------------

WEDGE_GLIDE = Skier(
    frames=90,
    stance=0.60,
    wedge_deg=26.0,
    turn_hz=0.05,
    steer_amp=0.05,
    edge_deg=3.0,
    incl_deg=2.0,
    angulation_deg=1.0,
    separation_deg=2.0,
    knee_fore_px=10.0,
)
WEDGE_TURNS = Skier(
    frames=200,
    stance=0.60,
    wedge_deg=22.0,
    turn_hz=0.16,
    steer_amp=0.30,
    edge_deg=4.0,
    incl_deg=3.0,
    angulation_deg=2.0,
    separation_deg=4.0,
    knee_fore_px=10.0,
)
SIDESLIP = Skier(
    frames=90,
    stance=0.28,
    wedge_deg=2.0,
    turn_hz=0.03,
    steer_amp=0.03,
    edge_deg=14.0,
    incl_deg=4.0,
    angulation_deg=4.0,
    separation_deg=2.0,
    knee_fore_px=4.0,
)
PARALLEL = Skier(
    frames=180,
    stance=0.30,
    turn_hz=0.22,
    steer_amp=0.35,
    edge_deg=8.0,
    incl_deg=6.0,
    angulation_deg=6.0,
    separation_deg=8.0,
    knee_fore_px=6.0,
    flex_amp_px=8.0,
)
CARVE = Skier(
    frames=180,
    stance=0.28,
    turn_hz=0.18,
    steer_amp=0.40,
    edge_deg=24.0,
    incl_deg=14.0,
    angulation_deg=18.0,
    separation_deg=8.0,
    knee_fore_px=2.0,
)
MOGUL = Skier(
    frames=150,
    stance=0.30,
    turn_hz=0.45,
    steer_amp=0.30,
    edge_deg=6.0,
    incl_deg=4.0,
    angulation_deg=4.0,
    separation_deg=6.0,
    knee_fore_px=6.0,
    flex_amp_px=40.0,
    bob=0.30,
)
#: Short skidded turns: fast, and Z-shaped rather than round, which is what
#: separates them from the round parallel turn the stage below asks for.
SKID_SHORT = Skier(
    frames=150,
    stance=0.28,
    turn_hz=0.35,
    steer_amp=0.30,
    edge_deg=8.0,
    incl_deg=6.0,
    angulation_deg=6.0,
    separation_deg=18.0,
    knee_fore_px=4.0,
    pole_spike_px=22.0,
    shape_power=3.0,
)
#: Filmed almost side-on: every lateral metric is suppressed (§3.1).
PROFILE_VIEW = Skier(
    frames=120,
    azimuth_deg=12.0,
    stance=0.30,
    turn_hz=0.22,
    steer_amp=0.35,
    edge_deg=8.0,
    incl_deg=6.0,
    angulation_deg=6.0,
)
#: Unusable: the hips and knees are missing, so there is no body scale.
NO_SCALE = Skier(frames=40, drop=(23, 24, 25, 26, 27, 28), conf=0.9)


CASES: tuple[ReportCase, ...] = (
    # -- v2 static-skeleton cases ------------------------------------------
    # ``banking_index`` is in ``INJURY_RISK_METRICS`` but not in
    # ``INJURY_RISK_SWEEP``: it blocks only on stages that list it as a core
    # metric, because on a wedge rung the index divides two noise-level angles
    # and is unreliable. Every pizza_glide gate passes and the score is ~92,
    # so the advance is allowed.
    ReportCase(
        case_id="wedge_glide_pass",
        clip_id="case-glide",
        expect_stages=("pizza_glide",),
        expect_ready=True,
        note="wide stance, real wedge, no turns → 犁式直滑，所有关卡通过，banking_index 不阻断此级别",
        frames=90,
        stance=1.8,
        knee_drop=50.0,
        skier=WEDGE_GLIDE,
    ),
    ReportCase(
        case_id="wedge_turns",
        clip_id="case-pizza",
        expect_stages=("pizza", "pizza_glide"),
        expect_ready=None,
        note="wide stance with linked steering → 犁式转弯",
        frames=200,
        stance=1.8,
        knee_drop=50.0,
        skier=WEDGE_TURNS,
    ),
    ReportCase(
        case_id="sideslip_quiet",
        clip_id="case-sideslip",
        expect_stages=("sideslip",),
        expect_ready=None,
        note="edge release, quiet torso, no turns → 侧滑",
        frames=90,
        stance=0.9,
        knee_drop=45.0,
        skier=SIDESLIP,
    ),
    ReportCase(
        case_id="parallel_linked",
        clip_id="case-parallel",
        expect_stages=("parallel", "dynamic_parallel"),
        expect_ready=None,
        note="hip-width stance, linked C-turns → 平行式",
        frames=180,
        stance=0.8,
        knee_drop=45.0,
        skier=PARALLEL,
    ),
    ReportCase(
        case_id="carve_angulated",
        clip_id="case-carve",
        expect_stages=("carve_long", "carve_medium", "carve_short", "parallel"),
        expect_ready=None,
        note="high edge angle with angulation → 刻滑",
        frames=180,
        stance=0.85,
        knee_drop=48.0,
        skier=CARVE,
    ),
    ReportCase(
        case_id="mogul_absorb",
        clip_id="case-mogul",
        expect_stages=("mogul_absorb", "mogul_fallline"),
        expect_ready=None,
        note="已过搓雪小弯：膝屈伸大、髋起伏明显 → 雪包吸收（蘑菇枝）",
        frames=150,
        stance=0.85,
        knee_drop=40.0,
        skier=MOGUL,
        passed_levels=PISTE_HISTORY + ("mogul_wedge", "skid_short"),
        scene={"terrain_type": "mogul"},
    ),
    ReportCase(
        case_id="unknown_refilm",
        clip_id="case-unknown",
        expect_stages=("unknown",),
        expect_ready=False,
        note="too few frames → 请重拍",
        frames=2,
        stance=1.0,
        knee_drop=40.0,
        min_frames=2,
        expect_unusable=True,
    ),
    # -- v3 cases ----------------------------------------------------------
    ReportCase(
        case_id="profile_view_unknown_metrics",
        clip_id="case-profile",
        expect_stages=(
            "pizza_glide",
            "pizza",
            "mogul_wedge",
            "sideslip",
            "wedge_christie",
            "parallel",
            "dynamic_parallel",
            "skid_short",
            "mogul_absorb",
            "mogul_fallline",
        ),
        expect_ready=None,
        note="侧面拍摄：横向指标全部不可测，只出拍摄提示；置信度不足时给出两个候选",
        frames=120,
        stance=0.9,
        knee_drop=45.0,
        skier=PROFILE_VIEW,
        expect_ambiguous=True,
    ),
    ReportCase(
        case_id="child_carving_not_applicable",
        clip_id="case-child",
        expect_stages=(
            "pizza_glide",
            "pizza",
            "sideslip",
            "wedge_christie",
            "parallel",
            "dynamic_parallel",
            "skid_short",
        ),
        expect_ready=None,
        note="9 岁儿童：刻滑不适用，站距不扣分",
        frames=180,
        stance=0.85,
        knee_drop=45.0,
        skier=CARVE,
        athlete={
            "age_years": 9.0,
            "height_m": 1.35,
            "mass_kg": 30.0,
            "sex": "female",
            "ski_cm": 110.0,
        },
    ),
    ReportCase(
        case_id="firm_snow_scene_supplied",
        clip_id="case-firm",
        expect_stages=(
            "firm_snow",
            "parallel",
            "dynamic_parallel",
            "carve_long",
            "carve_medium",
            "carve_short",
            "skid_short",
        ),
        expect_ready=None,
        note="硬雪场景已填：firm_snow 进入候选",
        frames=180,
        stance=0.85,
        knee_drop=45.0,
        skier=CARVE,
        scene={"snow_surface": "hardpack", "slope_band": "blue"},
    ),
    ReportCase(
        case_id="skid_short_with_history",
        clip_id="case-skid",
        expect_stages=("skid_short",),
        expect_ready=False,
        note="已过平行式：快而 Z 形的小弯 → 搓雪小弯，且技能树有已完成节点",
        frames=150,
        stance=0.9,
        knee_drop=45.0,
        skier=SKID_SHORT,
        passed_levels=PISTE_HISTORY,
    ),
    ReportCase(
        case_id="carve_with_history",
        clip_id="case-carve-history",
        expect_stages=("carve_long",),
        expect_ready=None,
        note="已过动态平行式：高刃角带折屈 → 刻滑大弯",
        frames=180,
        stance=0.85,
        knee_drop=48.0,
        skier=CARVE,
        passed_levels=PISTE_HISTORY,
    ),
    ReportCase(
        case_id="no_body_scale_unusable",
        clip_id="case-noscale",
        expect_stages=("unknown",),
        expect_ready=False,
        note="髋膝踝缺失：无法建立身体尺度 → 请重拍",
        frames=40,
        stance=1.0,
        knee_drop=40.0,
        skier=NO_SCALE,
        expect_unusable=True,
    ),
)
