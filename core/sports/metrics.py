"""Metric catalog for ski report v3 (design §3.1-§3.4).

This module replaces v2's 14 whole-clip signals (``core/sports/signals.py``)
with the 36-entry catalog of design §3.4, every entry carrying the forms the
curriculum gates actually compare: ``A`` (whole-clip robust aggregate), ``T``
(per-turn series) and ``C`` (count of faulty turns). Nothing here modifies or
imports v2; both layers coexist until a later change swaps the caller over.

Design decisions that apply to the whole module
-----------------------------------------------

**Registry is the source of truth.** :data:`REGISTRY` (a tuple of
:class:`MetricSpec`) declares every metric's id, unit, forms, noise class,
denominator, preconditions and description. Report code, the classifier and the
scorer are all expected to read the registry rather than hard-code metric
names.

**fps_effective everywhere.** Every rate is computed from ``fps_effective =
source_fps / frame_stride`` (see :func:`effective_fps`). v2 divided a
stride-sampled frame count by the *source* fps (``signals.py:266``) with
``FRAME_STRIDE = 2`` upstream (``clients/windows/pipeline/analyze.py:32``), so
every frequency it reported was ~2x the true value. Passing the sampled rate
here is the fix, and ``tests/test_metrics.py`` pins it: the same motion sampled
at stride 1 and stride 2 must yield the same Hz.

**Scene and profile come from the shared v3 types.** The §2.2 scene facts live
in :class:`core.sports.scene.SceneContext` and the §2.3 profile derivations in
:class:`core.sports.profile.AthleteContext`; this module consumes them rather
than defining its own. :func:`compute_metrics` accepts either the typed objects
or the ``scene`` / ``athlete`` blocks that :class:`ClipAnalysis` now carries, and
falls back to those blocks when the caller passes neither — so the pipeline's
recorded ``fps_effective`` is picked up automatically.

**Suppress, never fabricate.** A metric whose preconditions are unmet returns
``state="unknown"`` with a machine-readable ``reason``; a metric excluded by the
profile returns ``state="not_applicable"``. Neither ever returns a number. In
particular there is no analogue of v2's ``+ 1e-3`` denominators
(``signals.py:113``, ``signals.py:168``), where a missing shoulder turned the
fore/aft ratio into a ~1000x outlier: every ratio here goes through
:func:`_safe_ratio`, which refuses to divide by a denominator below an
explicit, unit-aware floor.

**View gating (§3.1).** Lateral metrics need the frontal plane to be visible
(``azimuth_deg >= 25``, design §3.1) and are otherwise suppressed with reason
``view_too_profile``. Symmetrically — this is an addition, stated as an
assumption — fore/aft (sagittal) metrics need the sagittal plane to be visible
and are suppressed above ``65`` degrees with reason ``view_too_frontal``,
because in a face-on view the fore/aft axis lies along the camera axis and is
not measurable from 2D at all. The consequence worth putting in the filming
chapter: the quarter view, 25-65 degrees, is the only framing in which both
families are measurable.

**Normalization (§3.2).** stance and lateral CoM offsets divide by **leg
length**, knee valgus by **shank length**, fore/aft by **leg length plus an
explicit shin angle**. Hip width is never used as a ruler: it collapses with
view angle, which is what made v2's lateral metrics explode in profile clips.

**Left and right are never pooled.** v2 appended both knees into one list
(``signals.py:134-148``) and took a median over the mixture, which is blind to
asymmetry by construction. Here every paired metric is computed per side and
both sides are kept as ``<id>_left`` / ``<id>_right`` values alongside the
combined ``<id>``; :data:`PAIRED_METRICS` feeds ``asymmetry_index``.

Where the design names a quantity without giving a formula, the formula chosen
here is documented at the function that computes it, with the assumption stated
in the text. Those are: ``edge_angle_proxy``, ``separation_angle``,
``turn_shape_index``, ``edge_change_duration``, ``rotation_count``,
``braking_count``, ``asymmetry_index``, ``pole_touch_rate``,
``pole_touch_timing``, ``camera_motion`` and ``hands_in_view``.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Literal, Sequence

import numpy as np

from core.sports.profile import AthleteContext
from core.sports.scene import CameraMotion, SceneContext, ViewClass
from core.sports.turns import (
    L_ANKLE,
    L_FOOT,
    L_HEEL,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    R_ANKLE,
    R_FOOT,
    R_HEEL,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
    LandmarkArrays,
    SteeringSignal,
    Turn,
    Window,
    landmark_arrays,
    steering_signal,
    window_mask,
)
from schemas.clip_analysis import ClipAnalysis

Form = Literal["A", "T", "C"]
State = Literal["ok", "unknown", "not_applicable"]
ViewReq = Literal["any", "lateral", "sagittal"]

# --- view and framing -------------------------------------------------------

#: Design §3.1: lateral metrics are computed only at or above this azimuth.
LATERAL_MIN_AZIMUTH_DEG = 25.0
#: Added (documented) mirror of the above for fore/aft metrics.
SAGITTAL_MAX_AZIMUTH_DEG = 65.0
QUARTER_MAX_AZIMUTH_DEG = 60.0
REASON_TOO_PROFILE = "view_too_profile"
REASON_TOO_FRONTAL = "view_too_frontal"
REASON_NO_TURNS = "no_turns_segmented"
REASON_NO_SCALE = "body_scale_unavailable"
REASON_NO_SAMPLES = "no_usable_samples"
REASON_NON_FINITE = "non_finite_value"
#: Prefix of the reason that names the joints a metric needed and this clip
#: never tracked, e.g. ``landmark_missing:left_ankle+right_ankle``. The joint
#: slugs are :data:`LANDMARK_SLUGS` values; the display layer localizes them.
REASON_LANDMARK_MISSING = "landmark_missing"

# --- anthropometry (§2.3) ---------------------------------------------------

#: Leg length as a fraction of stature (design §2.3, ``leg_len_m ~ 0.53*h``).
LEG_LENGTH_RATIO = 0.53
#: Shank (knee-to-floor) as a fraction of stature, Drillis & Contini.
SHANK_LENGTH_RATIO = 0.246
#: Bi-iliac breadth as a fraction of stature; used only for the frontal aspect
#: prior. Both terms scale with stature, so the ratio is height-invariant and
#: the prior is a constant unless a caller supplies a measured hip width.
HIP_WIDTH_RATIO = 0.191
ASPECT_FRONTAL_DEFAULT = HIP_WIDTH_RATIO / LEG_LENGTH_RATIO

# --- denominator floors (never 1e-3) ----------------------------------------

MIN_LEG_LEN_PX = 12.0
MIN_SHANK_LEN_PX = 6.0
MIN_TORSO_LEN_PX = 8.0
MIN_SPAN_S = 0.1
MIN_ANGLE_SUM_DEG = 1.5
#: ``banking_index`` divides |inclination| by |inclination| + |angulation|. Both
#: terms are noise-level on a skier who is not edging at all — a wedge glide sits
#: at a few degrees of each — so the ratio is a coin flip well above
#: ``MIN_ANGLE_SUM_DEG``. Below this combined angle the split between banking and
#: angulation is not a measurement, so the metric reports ``unknown`` instead.
MIN_BANKING_ANGLE_SUM_DEG = 8.0

# --- fault bands ------------------------------------------------------------

#: A transition wedge above this is a stem rather than a parallel edge change.
STEM_WEDGE_DEG = 15.0
#: hip_over_foot below this at the finish is back-seat (fraction of leg length).
BACKSEAT_RATIO = -0.05
#: Upper body turning into the new arc with the skis, in degrees of change.
ROTATION_DEG = 8.0
#: turn_shape_index below this with a late steering peak reads as braking.
BRAKING_SHAPE_MAX = 0.35
BRAKING_PEAK_PHASE = 0.66
#: Fraction of the arc amplitude that counts as "holding the arc".
SHAPE_HOLD_FRACTION = 0.5
#: Fraction of the arc amplitude that counts as "flat / between edges".
EDGE_BAND_FRACTION = 0.25

# --- pole detection ---------------------------------------------------------

POLE_SPIKE_MAD_K = 2.0
POLE_SPIKE_MIN_LEG_PER_S = 0.6
POLE_REFRACTORY_S = 0.25
POLE_MATCH_FRACTION = 0.35

# --- asymmetry --------------------------------------------------------------

#: Relative floor on the pooled sd: 5 % of the pair's mean magnitude. This is
#: the guard that keeps a near-constant pair from producing a huge z score.
ASYM_REL_FLOOR = 0.05
ASYM_ABS_FLOOR = 1e-6
ASYM_Z_CLIP = 6.0

# --- camera motion ----------------------------------------------------------

CAMERA_STATIC_TRAVEL = 3.0
CAMERA_FOLLOW_TRAVEL = 1.0
#: Reported when the hips are not trackable at all.
CAMERA_UNKNOWN = "unknown"

# --- misc -------------------------------------------------------------------

MIN_WRIST_FRACTION = 0.2
CORE_LANDMARKS = (
    L_SHOULDER,
    R_SHOULDER,
    L_HIP,
    R_HIP,
    L_KNEE,
    R_KNEE,
    L_ANKLE,
    R_ANKLE,
)
#: Slug per BlazePose index the catalog can require, so a suppressed metric can
#: name the joint that was absent instead of saying "not measured".
LANDMARK_SLUGS: dict[int, str] = {
    L_SHOULDER: "left_shoulder",
    R_SHOULDER: "right_shoulder",
    L_WRIST: "left_wrist",
    R_WRIST: "right_wrist",
    L_HIP: "left_hip",
    R_HIP: "right_hip",
    L_KNEE: "left_knee",
    R_KNEE: "right_knee",
    L_ANKLE: "left_ankle",
    R_ANKLE: "right_ankle",
    L_HEEL: "left_heel",
    R_HEEL: "right_heel",
    L_FOOT: "left_foot",
    R_FOOT: "right_foot",
}
SIDES: tuple[str, str] = ("left", "right")
RELIABILITY_NOISE = {"low": 1.0, "medium": 0.9, "high": 0.75}
#: Frame count at which the sample-size factor saturates.
RELIABILITY_SAMPLES_FULL = 20.0
#: Turn count at which it saturates for turn-based metrics: eight arcs is a
#: full sample for a per-turn statistic, where twenty frames is for a per-frame
#: one.
RELIABILITY_TURNS_FULL = 8.0
RELIABILITY_QUALITY_FULL = 0.7
#: Age bands for which carving metrics are not applicable (§2.3: bending a ski
#: requires mass, so carving gates are marked n/a below age-13-17).
CARVING_EXCLUDED_BANDS = ("age-3-6", "age-7-12")


def carving_applicable(athlete: AthleteContext | None) -> bool:
    """Whether carving-specific metrics apply to this athlete (§2.3).

    An unknown age never excludes a metric: the policy is that a profile may
    mark a gate not-applicable, never silently lower a standard, and absence of
    information is not evidence.
    """
    if athlete is None:
        return True
    band = athlete.age_band
    return band is None or band not in CARVING_EXCLUDED_BANDS


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricRequires:
    """Preconditions a metric needs before it may return a number."""

    view: ViewReq = "any"
    landmarks: tuple[int, ...] = ()
    turns: bool = False

    def landmark_reason(self, missing: frozenset[int]) -> str | None:
        """Reason naming the required joints this clip never tracked.

        ``landmarks`` was declared for all 36 catalog entries and read nowhere,
        so a metric that could not be computed because a joint was absent
        reported the generic ``no_usable_samples`` — the least useful thing the
        filming chapter can say. Returns ``None`` when nothing required is
        missing, which is the common case.
        """
        absent = [index for index in self.landmarks if index in missing]
        if not absent:
            return None
        slugs = sorted(
            {LANDMARK_SLUGS.get(index, str(index)) for index in absent}
        )
        return f"{REASON_LANDMARK_MISSING}:{'+'.join(slugs)}"

    def view_reason(self, azimuth_deg: float | None) -> str | None:
        if self.view == "any" or azimuth_deg is None:
            return None
        if self.view == "lateral" and azimuth_deg < LATERAL_MIN_AZIMUTH_DEG:
            return REASON_TOO_PROFILE
        if self.view == "sagittal" and azimuth_deg > SAGITTAL_MAX_AZIMUTH_DEG:
            return REASON_TOO_FRONTAL
        return None


@dataclass(frozen=True)
class MetricSpec:
    """One catalog entry. The registry of these is the single source of truth."""

    id: str
    unit: str
    forms: tuple[Form, ...]
    noise_class: str
    denominator: str
    requires: MetricRequires
    description: str
    per_side: bool = False
    scored: bool = True
    carving_only: bool = False
    group: str = ""

    @property
    def side_ids(self) -> tuple[str, ...]:
        if not self.per_side:
            return ()
        return tuple(f"{self.id}_{side}" for side in SIDES)


def _req(
    view: ViewReq = "any",
    landmarks: tuple[int, ...] = (),
    turns: bool = False,
) -> MetricRequires:
    return MetricRequires(view=view, landmarks=landmarks, turns=turns)


_ANKLES = (L_ANKLE, R_ANKLE)
_KNEES = (L_KNEE, R_KNEE)
_HIPS = (L_HIP, R_HIP)
_SHOULDERS = (L_SHOULDER, R_SHOULDER)
_FEET = (L_FOOT, R_FOOT)
_WRISTS = (L_WRIST, R_WRIST)

REGISTRY: tuple[MetricSpec, ...] = (
    # -- stance and balance (6) --
    MetricSpec(
        "stance_width",
        "ratio",
        ("A", "T"),
        "medium",
        "leg_length",
        _req("lateral", _ANKLES + _HIPS + _KNEES),
        "Ankle separation divided by leg length, median over usable frames.",
        group="stance",
    ),
    MetricSpec(
        "stance_width_var",
        "ratio",
        ("A",),
        "medium",
        "leg_length",
        _req("lateral", _ANKLES + _HIPS + _KNEES),
        "Interquartile range of the per-frame stance_width series.",
        group="stance",
    ),
    MetricSpec(
        "wedge_angle",
        "deg",
        ("A", "T"),
        "high",
        "none",
        _req("lateral", _ANKLES + _FEET),
        "Angle between the two ankle-to-foot_index vectors (wedge / stem).",
        group="stance",
    ),
    MetricSpec(
        "shin_angle_fore_aft",
        "deg",
        ("A", "T"),
        "medium",
        "none",
        _req("sagittal", _ANKLES + _KNEES),
        "Shank vector against image vertical, signed positive when forward.",
        per_side=True,
        group="stance",
    ),
    MetricSpec(
        "hip_over_foot",
        "ratio",
        ("A", "T", "C"),
        "medium",
        "leg_length",
        _req("sagittal", _ANKLES + _HIPS),
        "Fore/aft hip-to-ankle offset over leg length, read at the transition.",
        per_side=True,
        group="stance",
    ),
    MetricSpec(
        "com_vertical_travel",
        "ratio",
        ("A", "T"),
        "low",
        "leg_length",
        _req("any", _HIPS, turns=True),
        "Detrended hip height range within a turn, over leg length.",
        group="stance",
    ),
    # -- edging and steering (7) --
    MetricSpec(
        "edge_angle_proxy",
        "deg",
        ("A", "T"),
        "high",
        "none",
        _req("lateral", _ANKLES + _KNEES),
        "Shank tilt from the slope normal, corrected for lateral foreshortening.",
        per_side=True,
        carving_only=True,
        group="edging",
    ),
    MetricSpec(
        "inclination",
        "deg",
        ("A", "T"),
        "medium",
        "none",
        _req("lateral", _SHOULDERS + _ANKLES),
        "Shoulder-mid to ankle-mid line against image vertical.",
        group="edging",
    ),
    MetricSpec(
        "angulation",
        "deg",
        ("A", "T"),
        "high",
        "none",
        _req("lateral", _SHOULDERS + _HIPS + _ANKLES),
        "Inclination minus the hip-to-shoulder line angle.",
        carving_only=True,
        group="edging",
    ),
    MetricSpec(
        "banking_index",
        "ratio",
        ("A", "T"),
        "high",
        "inclination_plus_angulation",
        _req("lateral", _SHOULDERS + _HIPS + _ANKLES),
        "|inclination| / (|inclination| + |angulation|): banking versus angulation.",
        carving_only=True,
        group="edging",
    ),
    MetricSpec(
        "separation_angle",
        "deg",
        ("A", "T"),
        "medium",
        "none",
        _req("lateral", _SHOULDERS + _HIPS),
        "Signed shoulder-line minus pelvis-line angle in the image plane.",
        group="edging",
    ),
    MetricSpec(
        "upper_body_quiet",
        "deg",
        ("A",),
        "medium",
        "none",
        _req("lateral", _SHOULDERS + _HIPS),
        "Standard deviation of separation_angle, in degrees.",
        group="edging",
    ),
    MetricSpec(
        "knee_valgus",
        "ratio",
        ("A", "T"),
        "medium",
        "shank_length",
        _req("lateral", _KNEES + _ANKLES + _HIPS),
        "Knee-to-ankle offset toward the midline, over shank length.",
        per_side=True,
        group="edging",
    ),
    # -- rhythm and turn shape (8) --
    MetricSpec(
        "turn_rate",
        "Hz",
        ("A",),
        "low",
        "seconds",
        _req("any", (), turns=True),
        "Turns per second across the segmented span, using fps_effective.",
        group="rhythm",
    ),
    MetricSpec(
        "turn_duration_var",
        "ratio",
        ("A",),
        "low",
        "mean_duration",
        _req("any", (), turns=True),
        "Coefficient of variation of turn duration (rhythm consistency).",
        group="rhythm",
    ),
    MetricSpec(
        "turn_amplitude",
        "deg",
        ("A", "T"),
        "medium",
        "none",
        _req("any", (), turns=True),
        "Peak steering amplitude per turn, mean over turns.",
        group="rhythm",
    ),
    MetricSpec(
        "turn_shape_index",
        "ratio",
        ("A", "T"),
        "medium",
        "turn_duration",
        _req("any", (), turns=True),
        "Fraction of the arc spent holding at least half the peak steering angle.",
        group="rhythm",
    ),
    MetricSpec(
        "edge_change_duration",
        "s",
        ("A", "T"),
        "medium",
        "none",
        _req("any", (), turns=True),
        "Time spent inside the flat band around a turn boundary.",
        group="rhythm",
    ),
    MetricSpec(
        "flexion_range",
        "deg",
        ("A", "T"),
        "medium",
        "none",
        _req("any", _HIPS + _KNEES + _ANKLES),
        "Knee flexion p90 minus p10.",
        per_side=True,
        group="rhythm",
    ),
    MetricSpec(
        "flexion_rate",
        "Hz",
        ("A",),
        "medium",
        "seconds",
        _req("any", _HIPS + _KNEES + _ANKLES),
        "Knee flexion cycles per second, using fps_effective.",
        group="rhythm",
    ),
    MetricSpec(
        "pressure_peak_phase",
        "ratio",
        ("A", "T"),
        "high",
        "turn_duration",
        _req("any", _HIPS + _KNEES + _ANKLES, turns=True),
        "Where in the arc flexion is deepest: 0 at initiation, 1 at finish.",
        group="rhythm",
    ),
    # -- faults counted per turn (5) --
    MetricSpec(
        "stem_count",
        "count",
        ("C",),
        "high",
        "turns",
        _req("lateral", _ANKLES + _FEET, turns=True),
        "Turns whose transition shows a wedge angle above the stem band.",
        group="faults",
    ),
    MetricSpec(
        "backseat_count",
        "count",
        ("C",),
        "medium",
        "turns",
        _req("sagittal", _ANKLES + _HIPS, turns=True),
        "Turns whose finish shows the hips behind the back-seat band.",
        group="faults",
    ),
    MetricSpec(
        "rotation_count",
        "count",
        ("C",),
        "high",
        "turns",
        _req("lateral", _SHOULDERS + _HIPS, turns=True),
        "Turns where the upper body leads the skis into the new arc.",
        group="faults",
    ),
    MetricSpec(
        "braking_count",
        "count",
        ("C",),
        "high",
        "turns",
        _req("any", (), turns=True),
        "Turns whose arc collapses into a late steering spike (braking).",
        group="faults",
    ),
    MetricSpec(
        "asymmetry_index",
        "ratio",
        ("A",),
        "high",
        "pooled_sd",
        _req("any", ()),
        "Mean signed left-right difference across paired metrics, over pooled sd.",
        group="faults",
    ),
    # -- pole and hands (3) --
    MetricSpec(
        "hands_in_view",
        "ratio",
        ("A",),
        "medium",
        "frames",
        _req("sagittal", _WRISTS + _HIPS),
        "Fraction of frames with both wrists forward of the hip line.",
        group="poles",
    ),
    MetricSpec(
        "pole_touch_rate",
        "ratio",
        ("A",),
        "high",
        "turns",
        _req("any", _WRISTS, turns=True),
        "Turns with a wrist-velocity spike near the transition, over turns.",
        group="poles",
    ),
    MetricSpec(
        "pole_touch_timing",
        "s",
        ("A", "T"),
        "high",
        "none",
        _req("any", _WRISTS, turns=True),
        "Mean signed offset of the pole-touch spike from the transition.",
        group="poles",
    ),
    # -- quality and scene (7), never scored --
    MetricSpec(
        "view_azimuth_deg",
        "deg",
        ("A",),
        "medium",
        "none",
        _req("any", _HIPS + _KNEES + _ANKLES),
        "Estimated camera azimuth: 0 is pure profile, 90 is face-on.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "view_class",
        "class",
        ("A",),
        "medium",
        "none",
        _req("any", _HIPS + _KNEES + _ANKLES),
        "profile / quarter / frontal, banded from view_azimuth_deg.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "landmark_quality",
        "ratio",
        ("A",),
        "low",
        "frames",
        _req("any", ()),
        "Mean over frames of the weakest core-landmark visibility.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "usable_frame_ratio",
        "ratio",
        ("A",),
        "low",
        "frames",
        _req("any", ()),
        "Fraction of frames with a usable pelvis and both ankles.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "camera_motion",
        "class",
        ("A",),
        "high",
        "none",
        _req("any", _HIPS),
        "static / panning / follow, inferred from hip travel over body scale.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "fps_effective",
        "Hz",
        ("A",),
        "low",
        "none",
        _req("any", ()),
        "Sampled frame rate: source fps divided by the frame stride.",
        scored=False,
        group="quality",
    ),
    MetricSpec(
        "turn_count",
        "count",
        ("A",),
        "low",
        "none",
        _req("any", ()),
        "Number of segmented turns.",
        scored=False,
        group="quality",
    ),
)

BY_ID: dict[str, MetricSpec] = {spec.id: spec for spec in REGISTRY}
#: Paired metrics whose left/right values feed ``asymmetry_index``.
PAIRED_METRICS: tuple[str, ...] = tuple(
    spec.id for spec in REGISTRY if spec.per_side
)


def metric_ids(include_sides: bool = True) -> tuple[str, ...]:
    """All metric ids, optionally including the ``_left`` / ``_right`` variants."""
    out: list[str] = []
    for spec in REGISTRY:
        out.append(spec.id)
        if include_sides:
            out.extend(spec.side_ids)
    return tuple(out)


def spec_for(metric_id: str) -> MetricSpec | None:
    """Registry entry for an id, resolving ``_left`` / ``_right`` variants."""
    if metric_id in BY_ID:
        return BY_ID[metric_id]
    for suffix in SIDES:
        tail = f"_{suffix}"
        if metric_id.endswith(tail):
            base = BY_ID.get(metric_id[: -len(tail)])
            return base if base is not None and base.per_side else None
    return None


# ---------------------------------------------------------------------------
# inputs and outputs
# ---------------------------------------------------------------------------


def build_athlete_context(
    profile: Any, clip_date: date | None = None
) -> AthleteContext:
    """Coerce whatever the caller has into an :class:`AthleteContext`.

    Accepts, in order: an :class:`AthleteContext`; the ``athlete`` block a
    ``ClipAnalysis`` carries (``AthleteContext.to_dict`` shape); the stored
    ``AthleteProfile`` snapshot shape (``birthday`` / ``height_cm`` /
    ``weight_kg`` / ``ski_cm`` / ``gender``); or any object with those
    attributes. ``core`` must not import from ``clients``, hence the duck
    typing. ``None`` and unusable input give an empty context, never an error.
    """
    if profile is None:
        return AthleteContext()
    if isinstance(profile, AthleteContext):
        return profile
    if isinstance(profile, dict):
        context = AthleteContext.from_dict(profile)
        if context.is_complete or context.height_m is not None:
            return context
        return AthleteContext.from_profile_snapshot(profile, clip_date=clip_date)
    snapshot = {
        key: getattr(profile, key, None)
        for key in ("birthday", "height_cm", "weight_kg", "ski_cm", "gender")
    }
    if any(value is not None for value in snapshot.values()):
        return AthleteContext.from_profile_snapshot(snapshot, clip_date=clip_date)
    return AthleteContext()


def resolve_scene(scene: Any, fps_effective: float | None = None) -> SceneContext:
    """Coerce a scene block or :class:`SceneContext` into a context."""
    if isinstance(scene, SceneContext):
        if fps_effective is None:
            return scene
        return scene.with_fps_effective(fps_effective)
    return SceneContext.from_dict(scene, fps_effective=fps_effective)


@dataclass
class ViewEstimate:
    """Camera-relative framing estimate (design §3.1)."""

    shoulder_w_px: float | None
    hip_w_px: float | None
    torso_len_px: float | None
    leg_len_px: float | None
    aspect: float | None
    azimuth_deg: float | None
    #: ``core.sports.scene.ViewClass``; a str enum, so it compares equal to
    #: ``"profile"`` / ``"quarter"`` / ``"frontal"``.
    view_class: ViewClass
    reason: str | None = None

    @property
    def lateral_ok(self) -> bool:
        return (
            self.azimuth_deg is not None
            and self.azimuth_deg >= LATERAL_MIN_AZIMUTH_DEG
        )

    @property
    def sagittal_ok(self) -> bool:
        return (
            self.azimuth_deg is not None
            and self.azimuth_deg <= SAGITTAL_MAX_AZIMUTH_DEG
        )


@dataclass
class BodyScale:
    """Pixel rulers plus the §2.3 anthropometric priors."""

    leg_len_px: float | None
    shank_len_px: float | None
    torso_len_px: float | None
    px_per_m: float | None
    height_m: float | None = None
    leg_len_m: float | None = None
    mass_kg: float | None = None
    bmi: float | None = None

    @property
    def ok(self) -> bool:
        return self.leg_len_px is not None and self.leg_len_px >= MIN_LEG_LEN_PX

    def to_cm(self, ratio_of_leg: float | None) -> float | None:
        """Convert a leg-length ratio to centimetres when ``px_per_m`` exists."""
        if ratio_of_leg is None or self.leg_len_m is None:
            return None
        return ratio_of_leg * self.leg_len_m * 100.0


@dataclass
class MetricValue:
    """One measured metric, or an explicit statement that it was not measured."""

    metric_id: str
    value: float | None
    unit: str
    form: Form
    reliability: float
    state: State
    reason: str | None = None
    per_turn: list[float | None] | None = None
    faulty_turns: int | None = None
    total_turns: int | None = None
    evidence_ms: int | None = None
    #: Label for categorical metrics (``unit == "class"``); ``value`` is ``None``.
    text: str | None = None
    side: str | None = None

    @property
    def ok(self) -> bool:
        return self.state == "ok"


@dataclass
class MetricPack:
    """Everything the classifier, scorer and report read from this layer."""

    metrics: dict[str, MetricValue] = field(default_factory=dict)
    view: ViewEstimate | None = None
    scale: BodyScale | None = None
    athlete: AthleteContext | None = None
    scene: SceneContext | None = None
    fps_effective: float = 0.0
    turn_count: int = 0
    landmark_quality: float = 0.0
    usable_frame_ratio: float = 0.0
    camera_motion: str = CAMERA_UNKNOWN
    n_frames: int = 0

    def __getitem__(self, metric_id: str) -> MetricValue:
        return self.metrics[metric_id]

    def get(self, metric_id: str) -> MetricValue | None:
        return self.metrics.get(metric_id)

    def value(self, metric_id: str) -> float | None:
        item = self.metrics.get(metric_id)
        if item is None or item.state != "ok":
            return None
        return item.value

    def ok_ids(self) -> tuple[str, ...]:
        return tuple(k for k, v in self.metrics.items() if v.state == "ok")


# ---------------------------------------------------------------------------
# small numeric helpers
# ---------------------------------------------------------------------------


def effective_fps(source_fps: float, frame_stride: int = 1) -> float:
    """``source_fps / frame_stride``, floored at 1 Hz.

    This is the quantity the whole module runs on. The analysis pipeline samples
    every ``FRAME_STRIDE``-th frame (``clients/windows/pipeline/analyze.py:32``,
    stride 2) while v2 divided the resulting sample count by the *source* fps
    (``signals.py:266``), inflating every reported frequency by the stride.
    """
    fps = float(source_fps) if np.isfinite(source_fps) and source_fps > 0 else 15.0
    stride = int(frame_stride) if frame_stride and frame_stride > 0 else 1
    return max(fps / float(stride), 1.0)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _first_positive(*values: Any) -> float:
    """First finite, positive candidate; 1.0 if there is none."""
    for value in values:
        out = _as_float(value)
        if out is not None and out > 0.0:
            return max(out, 1.0)
    return 1.0


def _finite(series: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(series, dtype=np.float64).ravel()
    return arr[np.isfinite(arr)]


def _median(series: Sequence[float] | np.ndarray) -> float | None:
    good = _finite(series)
    if good.size == 0:
        return None
    return float(np.median(good))


def _mean(series: Sequence[float] | np.ndarray) -> float | None:
    good = _finite(series)
    if good.size == 0:
        return None
    return float(np.mean(good))


def _std(series: Sequence[float] | np.ndarray) -> float | None:
    good = _finite(series)
    if good.size < 2:
        return None
    return float(np.std(good))


def _iqr(series: Sequence[float] | np.ndarray) -> float | None:
    good = _finite(series)
    if good.size < 4:
        return None
    return float(np.percentile(good, 75) - np.percentile(good, 25))


def _p_range(
    series: Sequence[float] | np.ndarray, lo: float = 10.0, hi: float = 90.0
) -> float | None:
    good = _finite(series)
    if good.size < 4:
        return None
    return float(np.percentile(good, hi) - np.percentile(good, lo))


def _count(series: Sequence[float] | np.ndarray) -> int:
    return int(_finite(series).size)


def _safe_ratio(
    numerator: float | np.ndarray,
    denominator: float | None,
    floor: float,
) -> Any:
    """Divide only when the denominator clears an explicit floor.

    Returns ``nan`` (elementwise for arrays) otherwise. This exists so that the
    v2 pattern of adding ``1e-3`` to a possibly-missing denominator
    (``signals.py:113``, ``signals.py:168``) cannot be reproduced: there, a
    missing shoulder pair left ``torso = 1e-3`` and the fore/aft ratio came out
    roughly a thousand times too large.
    """
    if denominator is None or not np.isfinite(denominator) or denominator < floor:
        if isinstance(numerator, np.ndarray):
            return np.full(numerator.shape, np.nan)
        return float("nan")
    return numerator / float(denominator)


def _wrap_deg(values: Any) -> Any:
    """Wrap degrees into ``[-180, 180)``."""
    return (np.asarray(values, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _signed_angle_from_down(dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Signed angle of ``(dx, dy)`` from image-down, positive toward +x."""
    return np.degrees(np.arctan2(dx, dy))


def _clamp01(value: float) -> float:
    return float(min(max(value, 0.0), 1.0))


def _norm(vec: np.ndarray) -> np.ndarray:
    return np.hypot(vec[:, 0], vec[:, 1])


def _nan_reduce(func: Any, columns: list[np.ndarray]) -> np.ndarray:
    """Reduce a list of equal-length arrays elementwise, ignoring ``nan``.

    An all-``nan`` row legitimately means "not measurable in this frame", so the
    ``RuntimeWarning`` numpy raises for it is suppressed rather than surfaced.
    """
    if not columns or columns[0].size == 0:
        return np.array([], dtype=np.float64)
    stacked = np.stack(columns, axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = func(stacked, axis=1)
    return np.asarray(out, dtype=np.float64)


def _detrend(series: np.ndarray) -> np.ndarray:
    """Remove the least-squares linear trend, ignoring ``nan``.

    Used on hip height: with a static camera the skier also translates down the
    frame, and that translation would otherwise be counted as vertical travel.
    Assumption: the camera is level and the descent is close to linear in image
    space over the clip.
    """
    values = np.asarray(series, dtype=np.float64)
    good = np.isfinite(values)
    if np.count_nonzero(good) < 3:
        return values.copy()
    idx = np.arange(values.size, dtype=np.float64)
    slope, intercept = np.polyfit(idx[good], values[good], 1)
    return values - (slope * idx + intercept)


def _decorrelate(series: np.ndarray, regressor: np.ndarray) -> np.ndarray:
    """Remove the part of ``series`` linearly explained by ``regressor``.

    The mean of ``series`` is preserved: only the regressor-explained
    *variation* is subtracted, so a constant offset survives.

    This is what makes a fore/aft reading possible away from a turn boundary. A
    single 2D view mixes the sagittal and frontal axes, so the image-x offset
    between hip and ankle is ``fore_aft * cos(az) + lateral * sin(az)``, and in
    mid-arc the lateral term is several times the back-seat threshold - in a 22
    degree steering swing at quarter view it reaches ~0.4 leg lengths against a
    0.05 band. Regressing the offset on the measured steering displacement of
    the ankle midline and keeping the intercept attributes the arc-synchronous
    part to the projection and leaves the fore/aft part.

    Assumption: the athlete's true fore/aft offset does not itself correlate
    with the arc phase. Where it does (a skier who genuinely falls back only at
    the finish) this correction is conservative - it removes some of the real
    signal, so the metric under-reports rather than inventing a fault.
    """
    values = np.asarray(series, dtype=np.float64)
    x = np.asarray(regressor, dtype=np.float64)
    good = np.isfinite(values) & np.isfinite(x)
    if np.count_nonzero(good) < 6:
        return values.copy()
    xv = x[good]
    yv = values[good]
    x_mean = float(np.mean(xv))
    var = float(np.sum((xv - x_mean) ** 2))
    if var < 1e-9:
        return values.copy()
    slope = float(np.sum((xv - x_mean) * (yv - float(np.mean(yv)))) / var)
    return values - slope * (x - x_mean)


def _zero_cross_rate(series: np.ndarray, fps_effective: float) -> float | None:
    """Cycles per second from sign changes, using ``fps_effective``.

    Same estimator as v2's ``_zero_cross_freq`` (``signals.py:260``) with the
    denominator corrected: the sample count is divided by the *sampled* rate, so
    a stride-2 clip and a stride-1 clip of the same motion agree.
    """
    values = _finite(series)
    if values.size < 4:
        return None
    centred = values - float(np.median(values))
    sign = np.sign(centred)
    sign[sign == 0] = 1.0
    crosses = int(np.count_nonzero(sign[1:] * sign[:-1] < 0))
    span_s = values.size / max(float(fps_effective), 1.0)
    if span_s < MIN_SPAN_S:
        return None
    return 0.5 * crosses / span_s


# ---------------------------------------------------------------------------
# per-frame series
# ---------------------------------------------------------------------------


@dataclass
class FrameSeries:
    """Per-frame raw quantities, all ``(n,)`` arrays with ``nan`` for missing."""

    t_ms: np.ndarray
    hip_mid: np.ndarray
    ankle_mid: np.ndarray
    shoulder_mid: np.ndarray
    forward_sign: float
    forward_source: str
    stance_width: np.ndarray
    wedge_deg: np.ndarray
    shin_deg: dict[str, np.ndarray]
    hip_over_foot: dict[str, np.ndarray]
    valgus: dict[str, np.ndarray]
    flexion: dict[str, np.ndarray]
    flexion_mean: np.ndarray
    edge_deg: dict[str, np.ndarray]
    inclination: np.ndarray
    angulation: np.ndarray
    banking: np.ndarray
    separation: np.ndarray
    hip_y_detrended: np.ndarray
    hands_forward: np.ndarray
    wrist_speed: np.ndarray
    usable: np.ndarray


def _forward_axis(arrays: LandmarkArrays, hip_mid: np.ndarray) -> tuple[float, str]:
    """Sign of the direction of travel along image +x.

    Preference order, documented because it is an added assumption: the toe-heel
    vector (``foot_index - heel``, the landmarks §2.1 asks the app to start
    using) points where the skier faces and works even for a stationary skier;
    failing that, the net hip displacement; failing that, ``+1`` with the source
    recorded so reliability can be reduced.
    """
    toe = np.concatenate(
        [
            arrays.x[:, L_FOOT] - arrays.x[:, L_HEEL],
            arrays.x[:, R_FOOT] - arrays.x[:, R_HEEL],
        ]
    )
    toe_mean = _mean(toe)
    if toe_mean is not None and abs(toe_mean) > 1.0:
        return (1.0 if toe_mean > 0 else -1.0), "toe_heel"
    good = np.isfinite(hip_mid[:, 0])
    if np.count_nonzero(good) >= 2:
        xs = hip_mid[good, 0]
        drift = float(xs[-1] - xs[0])
        if abs(drift) > 1.0:
            return (1.0 if drift > 0 else -1.0), "hip_drift"
    return 1.0, "assumed_plus_x"


def _knee_flexion(
    hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray
) -> np.ndarray:
    """``180 - angle(hip, knee, ankle)`` in degrees, ``nan`` when degenerate."""
    u = hip - knee
    w = ankle - knee
    nu = _norm(u)
    nw = _norm(w)
    dot = u[:, 0] * w[:, 0] + u[:, 1] * w[:, 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = dot / (nu * nw)
    cos = np.where((nu < 1e-6) | (nw < 1e-6), np.nan, cos)
    cos = np.clip(cos, -1.0, 1.0)
    return 180.0 - np.degrees(np.arccos(cos))


def _segment_len(
    arrays: LandmarkArrays, a: int, b: int
) -> np.ndarray:
    pa = arrays.point(a)
    pb = arrays.point(b)
    return _norm(pa - pb)


def estimate_body_scale(
    arrays: LandmarkArrays, athlete: AthleteContext
) -> BodyScale:
    """Median pixel rulers plus the profile priors.

    Leg length is the *sum of segments* (hip-knee plus knee-ankle) rather than
    the straight hip-to-ankle distance, so a flexed knee does not shrink the
    ruler mid-turn. ``px_per_m`` uses the §2.3 prior ``leg_len_m = 0.53*height``
    and is ``None`` without a profile; it is an approximation because leg length
    foreshortens with view angle, so it is used for the report's centimetre
    display only, never for a score.
    """
    thigh = np.concatenate(
        [_segment_len(arrays, L_HIP, L_KNEE), _segment_len(arrays, R_HIP, R_KNEE)]
    )
    shank = np.concatenate(
        [_segment_len(arrays, L_KNEE, L_ANKLE), _segment_len(arrays, R_KNEE, R_ANKLE)]
    )
    thigh_med = _median(thigh)
    shank_med = _median(shank)
    leg = None
    if thigh_med is not None and shank_med is not None:
        leg = thigh_med + shank_med
    elif shank_med is not None:
        # Fall back on the anthropometric ratio between the two segments.
        leg = shank_med * (LEG_LENGTH_RATIO / SHANK_LENGTH_RATIO)
    torso = _median(
        _norm(arrays.mid(L_SHOULDER, R_SHOULDER) - arrays.mid(L_HIP, R_HIP))
    )
    px_per_m = None
    leg_len_m = athlete.leg_len_m
    if leg is not None and leg >= MIN_LEG_LEN_PX and leg_len_m:
        px_per_m = leg / leg_len_m
    return BodyScale(
        leg_len_px=leg,
        shank_len_px=shank_med,
        torso_len_px=torso,
        px_per_m=px_per_m,
        height_m=athlete.height_m,
        leg_len_m=leg_len_m,
        mass_kg=athlete.mass_kg,
        bmi=athlete.bmi,
    )


def estimate_view(arrays: LandmarkArrays, scale: BodyScale) -> ViewEstimate:
    """Estimate camera azimuth from the hip-width-to-leg-length aspect (§3.1).

    ``aspect = hip_w_px / leg_len_px`` is scale free; dividing by the expected
    frontal aspect and taking ``asin`` gives 0 degrees for a pure profile and 90
    for face-on. The frontal prior is the anthropometric constant
    ``0.191/0.53`` (bi-iliac breadth over leg length); both terms scale with
    stature, so the prior is height-invariant and the view estimate needs no
    profile at all - which is why this takes no :class:`AthleteContext`.
    """
    hip_w = _median(np.abs(arrays.x[:, L_HIP] - arrays.x[:, R_HIP]))
    shoulder_w = _median(np.abs(arrays.x[:, L_SHOULDER] - arrays.x[:, R_SHOULDER]))
    leg = scale.leg_len_px
    aspect = None
    azimuth = None
    if hip_w is not None and leg is not None and leg >= MIN_LEG_LEN_PX:
        aspect = hip_w / leg
        ratio = _clamp01(aspect / max(ASPECT_FRONTAL_DEFAULT, 1e-6))
        azimuth = float(np.degrees(np.arcsin(ratio)))
    if azimuth is None:
        view_class = ViewClass.QUARTER
        reason: str | None = REASON_NO_SCALE
    elif azimuth < LATERAL_MIN_AZIMUTH_DEG:
        view_class = ViewClass.PROFILE
        reason = REASON_TOO_PROFILE
    elif azimuth <= QUARTER_MAX_AZIMUTH_DEG:
        view_class = ViewClass.QUARTER
        reason = None
    else:
        view_class = ViewClass.FRONTAL
        reason = REASON_TOO_FRONTAL if azimuth > SAGITTAL_MAX_AZIMUTH_DEG else None
    return ViewEstimate(
        shoulder_w_px=shoulder_w,
        hip_w_px=hip_w,
        torso_len_px=scale.torso_len_px,
        leg_len_px=leg,
        aspect=aspect,
        azimuth_deg=azimuth,
        view_class=view_class,
        reason=reason,
    )


def build_series(
    arrays: LandmarkArrays,
    scale: BodyScale,
    view: ViewEstimate,
    fps_effective: float,
) -> FrameSeries:
    """Compute every per-frame quantity the catalog needs.

    Formulas, with the assumption for each invented one stated inline:

    * ``stance_width`` - horizontal ankle separation over leg length (§3.2).
    * ``wedge_angle`` - unsigned angle between the two ankle-to-foot_index
      vectors. Uncorrected for perspective; reliability carries the view
      penalty.
    * ``shin_angle_fore_aft`` - signed angle of ankle-to-knee from image
      vertical, multiplied by the travel-direction sign so positive means the
      knee is ahead of the foot.
    * ``hip_over_foot`` - fore/aft hip-to-ankle offset over leg length, per
      side, signed forward-positive, with the arc's lateral projection removed
      by :func:`_decorrelate` so that a reading taken away from a boundary
      (which is what ``backseat_count`` needs) is not dominated by the steering
      swing.
    * ``edge_angle_proxy`` (**invented formula**) - the shank tilt from the
      image vertical after undoing lateral foreshortening: the lateral
      component is divided by ``sin(azimuth)``, clamped at ``sin(25 deg)``.
      Assumption: the slope normal is approximated by the image vertical, since
      slope-angle recovery from one uncalibrated camera is out of scope (§11),
      and the frontal-plane offset projects as ``sin(azimuth)``.
    * ``inclination`` / ``angulation`` / ``banking_index`` - signed angles of
      the shoulder-to-ankle line and the shoulder-to-hip line from image down;
      angulation is their difference; the banking index divides ``|incl|`` by
      ``|incl| + |ang|`` and is ``nan`` when that sum is under 1.5 degrees,
      because below that the split is noise, not a measurement.
    * ``separation_angle`` (**invented formula**) - signed difference of the
      shoulder-line and pelvis-line tilts in the image plane. Assumption: true
      three-dimensional yaw separation is not recoverable from a single 2D
      view, so this measures the same projected quantity as v2's ``upper_quiet``
      (``signals.py:153-155``) but signed and in degrees; its reliability
      carries the lateral view factor because the projection collapses toward a
      profile view.
    * ``knee_valgus`` - knee-to-ankle offset toward the body midline over shank
      length (§3.2: local to the segment measured).
    * ``hands_forward`` (**invented formula**) - both wrists ahead of the hip
      midline along the travel direction. Assumption: "forward of the hip line"
      is read along the fore/aft axis, not vertically as v2 did with
      ``hands_low`` (``signals.py:157-160``).
    * ``wrist_speed`` - faster of the two wrists, in leg lengths per second,
      the input to pole-touch detection.
    """
    n = arrays.n
    hip_mid = arrays.mid(L_HIP, R_HIP)
    ankle_mid = arrays.mid(L_ANKLE, R_ANKLE)
    shoulder_mid = arrays.mid(L_SHOULDER, R_SHOULDER)
    forward_sign, forward_source = _forward_axis(arrays, hip_mid)
    leg = scale.leg_len_px
    shank = scale.shank_len_px

    stance = _safe_ratio(
        np.abs(arrays.x[:, L_ANKLE] - arrays.x[:, R_ANKLE]), leg, MIN_LEG_LEN_PX
    )

    foot_l = arrays.point(L_FOOT) - arrays.point(L_ANKLE)
    foot_r = arrays.point(R_FOOT) - arrays.point(R_ANKLE)
    nl, nr = _norm(foot_l), _norm(foot_r)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos_wedge = (
            foot_l[:, 0] * foot_r[:, 0] + foot_l[:, 1] * foot_r[:, 1]
        ) / (nl * nr)
    cos_wedge = np.where((nl < 1e-6) | (nr < 1e-6), np.nan, cos_wedge)
    wedge = np.degrees(np.arccos(np.clip(cos_wedge, -1.0, 1.0)))

    sin_az = (
        float(np.sin(np.radians(max(view.azimuth_deg, LATERAL_MIN_AZIMUTH_DEG))))
        if view.azimuth_deg is not None
        else float(np.sin(np.radians(LATERAL_MIN_AZIMUTH_DEG)))
    )
    sin_az = max(sin_az, float(np.sin(np.radians(LATERAL_MIN_AZIMUTH_DEG))))

    #: Steering displacement of the ankle midline, in leg lengths: the
    #: regressor used to strip the arc's lateral projection out of the fore/aft
    #: readings (see :func:`_decorrelate`).
    steer_offset = np.asarray(
        _safe_ratio(ankle_mid[:, 0] - hip_mid[:, 0], leg, MIN_LEG_LEN_PX),
        dtype=np.float64,
    )

    shin: dict[str, np.ndarray] = {}
    hof: dict[str, np.ndarray] = {}
    valgus: dict[str, np.ndarray] = {}
    flexion: dict[str, np.ndarray] = {}
    edge: dict[str, np.ndarray] = {}
    joints = {
        "left": (L_HIP, L_KNEE, L_ANKLE),
        "right": (R_HIP, R_KNEE, R_ANKLE),
    }
    for side, (hip_i, knee_i, ankle_i) in joints.items():
        knee = arrays.point(knee_i)
        ankle = arrays.point(ankle_i)
        hip = arrays.point(hip_i)
        dx = knee[:, 0] - ankle[:, 0]
        dy = knee[:, 1] - ankle[:, 1]
        shin[side] = forward_sign * _signed_angle_from_down(dx, -dy)
        hof[side] = _decorrelate(
            np.asarray(
                _safe_ratio(
                    forward_sign * (hip[:, 0] - ankle[:, 0]), leg, MIN_LEG_LEN_PX
                ),
                dtype=np.float64,
            ),
            steer_offset,
        )
        inward = np.sign(hip_mid[:, 0] - ankle[:, 0])
        fallback = np.sign(hip_mid[:, 0] - hip[:, 0])
        inward = np.where(
            np.abs(hip_mid[:, 0] - ankle[:, 0]) < 1.0, fallback, inward
        )
        inward = np.where(inward == 0.0, np.nan, inward)
        valgus[side] = _safe_ratio(inward * dx, shank, MIN_SHANK_LEN_PX)
        flexion[side] = _knee_flexion(hip, knee, ankle)
        edge[side] = np.degrees(
            np.arctan2(np.abs(dx) / sin_az, np.abs(dy))
        )
        edge[side] = np.where(np.isfinite(dx) & np.isfinite(dy), edge[side], np.nan)

    flexion_mean = _nan_reduce(np.nanmean, [flexion["left"], flexion["right"]])

    incl = _signed_angle_from_down(
        ankle_mid[:, 0] - shoulder_mid[:, 0], ankle_mid[:, 1] - shoulder_mid[:, 1]
    )
    torso_ang = _signed_angle_from_down(
        hip_mid[:, 0] - shoulder_mid[:, 0], hip_mid[:, 1] - shoulder_mid[:, 1]
    )
    angulation = _wrap_deg(incl - torso_ang)
    denom = np.abs(incl) + np.abs(angulation)
    with np.errstate(invalid="ignore", divide="ignore"):
        banking = np.abs(incl) / denom
    banking = np.where(denom < MIN_BANKING_ANGLE_SUM_DEG, np.nan, banking)

    sh_ang = np.degrees(
        np.arctan2(
            arrays.y[:, R_SHOULDER] - arrays.y[:, L_SHOULDER],
            arrays.x[:, R_SHOULDER] - arrays.x[:, L_SHOULDER],
        )
    )
    hp_ang = np.degrees(
        np.arctan2(
            arrays.y[:, R_HIP] - arrays.y[:, L_HIP],
            arrays.x[:, R_HIP] - arrays.x[:, L_HIP],
        )
    )
    separation = _wrap_deg(sh_ang - hp_ang)

    hip_y = _detrend(hip_mid[:, 1])

    wrist_l = arrays.point(L_WRIST)
    wrist_r = arrays.point(R_WRIST)
    fwd_l = forward_sign * (wrist_l[:, 0] - hip_mid[:, 0])
    fwd_r = forward_sign * (wrist_r[:, 0] - hip_mid[:, 0])
    both = np.isfinite(fwd_l) & np.isfinite(fwd_r)
    hands = np.where(both, ((fwd_l > 0.0) & (fwd_r > 0.0)).astype(np.float64), np.nan)

    dt = 1.0 / max(float(fps_effective), 1.0)
    speeds = []
    for wrist in (wrist_l, wrist_r):
        step = np.full(n, np.nan)
        if n >= 2:
            delta = np.hypot(np.diff(wrist[:, 0]), np.diff(wrist[:, 1]))
            step[1:] = delta
        speeds.append(np.asarray(_safe_ratio(step / dt, leg, MIN_LEG_LEN_PX)))
    wrist_speed = _nan_reduce(np.nanmax, speeds)

    usable = (
        np.isfinite(hip_mid[:, 0])
        & np.isfinite(ankle_mid[:, 0])
    )
    return FrameSeries(
        t_ms=arrays.t_ms,
        hip_mid=hip_mid,
        ankle_mid=ankle_mid,
        shoulder_mid=shoulder_mid,
        forward_sign=forward_sign,
        forward_source=forward_source,
        stance_width=np.asarray(stance, dtype=np.float64),
        wedge_deg=wedge,
        shin_deg=shin,
        hip_over_foot=hof,
        valgus=valgus,
        flexion=flexion,
        flexion_mean=flexion_mean,
        edge_deg=edge,
        inclination=incl,
        angulation=angulation,
        banking=np.asarray(banking, dtype=np.float64),
        separation=separation,
        hip_y_detrended=hip_y,
        hands_forward=hands,
        wrist_speed=wrist_speed,
        usable=usable,
    )


# ---------------------------------------------------------------------------
# metric value construction
# ---------------------------------------------------------------------------


class _Builder:
    """Assembles :class:`MetricValue` objects with consistent gating."""

    def __init__(
        self,
        view: ViewEstimate,
        athlete: AthleteContext,
        landmark_quality: float,
        turns: list[Turn],
        forward_source: str,
        missing_landmarks: frozenset[int] = frozenset(),
    ) -> None:
        self.view = view
        self.athlete = athlete
        self.landmark_quality = landmark_quality
        self.turns = turns
        self.forward_source = forward_source
        #: Indices with no finite coordinate anywhere in the clip.
        self.missing_landmarks = missing_landmarks

    # -- reliability ----------------------------------------------------
    def reliability(self, spec: MetricSpec, samples: int) -> float:
        """``f(landmark_quality, view_azimuth, sample_count, noise_class)``.

        Multiplicative, each factor in ``[0, 1]``: landmark quality against a
        0.7 target, a view factor that decays as the metric's plane rotates
        away from the camera, a sample-count factor saturating at 20 samples,
        and a fixed penalty per noise class.
        """
        quality = _clamp01(self.landmark_quality / RELIABILITY_QUALITY_FULL)
        target = (
            RELIABILITY_TURNS_FULL
            if spec.requires.turns
            else RELIABILITY_SAMPLES_FULL
        )
        sample = _clamp01(samples / target)
        noise = RELIABILITY_NOISE.get(spec.noise_class, 0.8)
        view_factor = 1.0
        az = self.view.azimuth_deg
        if az is not None:
            if spec.requires.view == "lateral":
                view_factor = _clamp01(
                    float(np.sin(np.radians(az))) / float(np.sin(np.radians(45.0)))
                )
            elif spec.requires.view == "sagittal":
                view_factor = _clamp01(
                    float(np.cos(np.radians(az))) / float(np.cos(np.radians(45.0)))
                )
        if spec.requires.view == "sagittal" and self.forward_source == "assumed_plus_x":
            view_factor *= 0.7
        return _clamp01(quality * sample * noise * view_factor)

    # -- gates ----------------------------------------------------------
    def blocked(self, spec: MetricSpec) -> MetricValue | None:
        """Return a suppressed value if a precondition fails, else ``None``."""
        if spec.carving_only and not carving_applicable(self.athlete):
            band = self.athlete.age_band or "unknown"
            return self.not_applicable(spec, f"not_applicable_age_band:{band}")
        reason = spec.requires.view_reason(self.view.azimuth_deg)
        if reason is not None:
            return self.unknown(spec, reason)
        if self.view.azimuth_deg is None and spec.requires.view != "any":
            return self.unknown(spec, REASON_NO_SCALE)
        if spec.requires.turns and not self.turns:
            return self.unknown(spec, REASON_NO_TURNS)
        return None

    # -- constructors ---------------------------------------------------
    def unknown(
        self, spec: MetricSpec, reason: str, side: str | None = None
    ) -> MetricValue:
        if reason == REASON_NO_SAMPLES:
            # Wire ``requires.landmarks`` in: when the reason would be the
            # generic "not measured", name the joint that was never tracked so
            # the filming chapter can tell the skier what to fix. Every more
            # specific reason (view, scale, turns, ``wrists_not_visible``) is
            # left exactly as the caller gave it.
            named = spec.requires.landmark_reason(self.missing_landmarks)
            if named is not None:
                reason = named
        return MetricValue(
            metric_id=spec.id if side is None else f"{spec.id}_{side}",
            value=None,
            unit=spec.unit,
            form=spec.forms[0],
            reliability=0.0,
            state="unknown",
            reason=reason,
            per_turn=None,
            faulty_turns=None,
            total_turns=None,
            evidence_ms=None,
            side=side,
        )

    def not_applicable(
        self, spec: MetricSpec, reason: str, side: str | None = None
    ) -> MetricValue:
        value = self.unknown(spec, reason, side=side)
        value.state = "not_applicable"
        return value

    def ok(
        self,
        spec: MetricSpec,
        value: float | None,
        *,
        samples: int,
        form: Form | None = None,
        per_turn: list[float | None] | None = None,
        faulty_turns: int | None = None,
        total_turns: int | None = None,
        evidence_ms: float | None = None,
        text: str | None = None,
        side: str | None = None,
        reliability: float | None = None,
        reason: str | None = None,
    ) -> MetricValue:
        """Build an ``ok`` value, or an ``unknown`` one if it is not finite."""
        if spec.unit != "class":
            if value is None:
                return self.unknown(spec, REASON_NO_SAMPLES, side=side)
            if not np.isfinite(value):
                return self.unknown(spec, REASON_NON_FINITE, side=side)
        clean_per_turn: list[float | None] | None = None
        if per_turn is not None:
            clean_per_turn = [
                float(item)
                if item is not None and np.isfinite(item)
                else None
                for item in per_turn
            ]
        rel = (
            self.reliability(spec, samples)
            if reliability is None
            else _clamp01(reliability)
        )
        return MetricValue(
            metric_id=spec.id if side is None else f"{spec.id}_{side}",
            value=None if value is None else float(value),
            unit=spec.unit,
            form=form or spec.forms[0],
            reliability=rel,
            state="ok",
            reason=reason,
            per_turn=clean_per_turn,
            faulty_turns=faulty_turns,
            total_turns=total_turns,
            evidence_ms=None if evidence_ms is None else int(round(evidence_ms)),
            text=text,
            side=side,
        )


def _evidence_extreme(
    t_ms: np.ndarray, series: np.ndarray, centre: float | None
) -> float | None:
    """Timestamp of the sample farthest from ``centre``.

    That is the frame the report should link to: the most extreme instance is
    what a coach wants to look at, not an average-looking one.
    """
    good = np.isfinite(series)
    if not np.any(good) or centre is None:
        return None
    idx = np.argmax(np.abs(series[good] - centre))
    return float(t_ms[good][idx])


def _window_values(
    series: np.ndarray, t_ms: np.ndarray, window: Window
) -> np.ndarray:
    mask = window_mask(t_ms, window)
    if not np.any(mask):
        return np.array([], dtype=np.float64)
    return series[mask]


def _per_turn(
    series: np.ndarray,
    t_ms: np.ndarray,
    turns: list[Turn],
    phase: str = "all",
    reducer: Any = _median,
) -> list[float | None]:
    return [
        reducer(_window_values(series, t_ms, turn.window(phase))) for turn in turns
    ]


def _aggregate_turns(per_turn: list[float | None]) -> float | None:
    values = [item for item in per_turn if item is not None and np.isfinite(item)]
    if not values:
        return None
    return float(np.median(values))


# ---------------------------------------------------------------------------
# metric families
# ---------------------------------------------------------------------------


def _add_frame_metric(
    out: dict[str, MetricValue],
    builder: _Builder,
    spec: MetricSpec,
    series: np.ndarray,
    t_ms: np.ndarray,
    turns: list[Turn],
    *,
    aggregate: Any = _median,
    phase: str = "all",
    side: str | None = None,
) -> None:
    """Aggregate a per-frame series into ``A`` (and ``T`` when turns exist)."""
    blocked = builder.blocked(spec)
    key = spec.id if side is None else f"{spec.id}_{side}"
    if blocked is not None:
        blocked.metric_id = key
        blocked.side = side
        out[key] = blocked
        return
    value = aggregate(series)
    samples = _count(series)
    per_turn = (
        _per_turn(series, t_ms, turns, phase=phase, reducer=aggregate)
        if turns and "T" in spec.forms
        else None
    )
    out[key] = builder.ok(
        spec,
        value,
        samples=samples,
        per_turn=per_turn,
        evidence_ms=_evidence_extreme(t_ms, series, value),
        side=side,
    )


def _stance_and_balance(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    turns: list[Turn],
    scale: BodyScale,
) -> None:
    t_ms = series.t_ms
    _add_frame_metric(
        out, builder, BY_ID["stance_width"], series.stance_width, t_ms, turns
    )
    _add_frame_metric(
        out,
        builder,
        BY_ID["stance_width_var"],
        series.stance_width,
        t_ms,
        turns,
        aggregate=_iqr,
    )
    _add_frame_metric(out, builder, BY_ID["wedge_angle"], series.wedge_deg, t_ms, turns)

    spec = BY_ID["shin_angle_fore_aft"]
    for side in SIDES:
        _add_frame_metric(
            out, builder, spec, series.shin_deg[side], t_ms, turns, side=side
        )
    _combine_sides(out, builder, spec, series.shin_deg, t_ms, turns)

    # hip_over_foot is read at the transition (design §3.4). Without turns the
    # transition restriction is dropped and the whole-clip median is used
    # instead - a documented degradation, not a fabrication; the C form is then
    # simply absent.
    spec = BY_ID["hip_over_foot"]
    for side in SIDES:
        _add_frame_metric(
            out,
            builder,
            spec,
            series.hip_over_foot[side],
            t_ms,
            turns,
            phase="transition",
            side=side,
        )
    _combine_sides(
        out, builder, spec, series.hip_over_foot, t_ms, turns, phase="transition"
    )
    combined = out.get(spec.id)
    if combined is not None and combined.state == "ok" and turns:
        faulty = 0
        total = 0
        first_bad: float | None = None
        for turn in turns:
            values = [
                _median(
                    _window_values(series.hip_over_foot[side], t_ms, turn.transition)
                )
                for side in SIDES
            ]
            good = [v for v in values if v is not None]
            if not good:
                continue
            total += 1
            if float(np.mean(good)) < BACKSEAT_RATIO:
                faulty += 1
                if first_bad is None:
                    first_bad = turn.t_start_ms
        if total:
            combined.faulty_turns = faulty
            combined.total_turns = total
            if first_bad is not None:
                combined.evidence_ms = int(round(first_bad))

    spec = BY_ID["com_vertical_travel"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        per_turn = _per_turn(
            series.hip_y_detrended,
            t_ms,
            turns,
            reducer=lambda arr: _travel_ratio(arr, scale),
        )
        out[spec.id] = builder.ok(
            spec,
            _aggregate_turns(per_turn),
            samples=len([v for v in per_turn if v is not None]),
            per_turn=per_turn,
            evidence_ms=turns[0].t_start_ms if turns else None,
        )


def _travel_ratio(values: np.ndarray, scale: BodyScale) -> float | None:
    good = _finite(values)
    if good.size < 3:
        return None
    ratio = _safe_ratio(
        float(np.max(good) - np.min(good)), scale.leg_len_px, MIN_LEG_LEN_PX
    )
    return None if not np.isfinite(ratio) else float(ratio)


def _combine_sides(
    out: dict[str, MetricValue],
    builder: _Builder,
    spec: MetricSpec,
    per_side: dict[str, np.ndarray],
    t_ms: np.ndarray,
    turns: list[Turn],
    phase: str = "all",
) -> None:
    """Combined value for a paired metric: mean of the two side aggregates.

    Deliberately *not* a median over both sides' frames pooled together, which
    is what v2 does for knee flexion (``signals.py:134-148``) and which hides
    asymmetry: pooling makes a skier who flexes 40 degrees on one leg and 10 on
    the other look like a uniform 25.
    """
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
        return
    left = out.get(f"{spec.id}_left")
    right = out.get(f"{spec.id}_right")
    values = [
        item.value
        for item in (left, right)
        if item is not None and item.state == "ok" and item.value is not None
    ]
    if not values:
        out[spec.id] = builder.unknown(spec, REASON_NO_SAMPLES)
        return
    stacked = np.concatenate([per_side[side] for side in SIDES])
    per_turn: list[float | None] | None = None
    if turns and "T" in spec.forms:
        per_turn = []
        for turn in turns:
            window = turn.window(phase)
            sides = [
                _median(_window_values(per_side[side], t_ms, window))
                for side in SIDES
            ]
            good = [v for v in sides if v is not None]
            per_turn.append(float(np.mean(good)) if good else None)
    out[spec.id] = builder.ok(
        spec,
        float(np.mean(values)),
        samples=_count(stacked),
        per_turn=per_turn,
        evidence_ms=_evidence_extreme(
            t_ms, per_side["left"], float(np.mean(values))
        ),
    )


def _edging_and_steering(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    turns: list[Turn],
) -> None:
    t_ms = series.t_ms
    spec = BY_ID["edge_angle_proxy"]
    for side in SIDES:
        _add_frame_metric(
            out, builder, spec, series.edge_deg[side], t_ms, turns, side=side
        )
    _combine_sides(out, builder, spec, series.edge_deg, t_ms, turns)

    # Aggregates use the magnitude (the skier inclines both ways); the per-turn
    # series keeps the sign so the report can show which way each arc leaned.
    _add_frame_metric(
        out,
        builder,
        BY_ID["inclination"],
        np.abs(series.inclination),
        t_ms,
        turns,
    )
    _add_frame_metric(
        out, builder, BY_ID["angulation"], np.abs(series.angulation), t_ms, turns
    )
    _add_frame_metric(out, builder, BY_ID["banking_index"], series.banking, t_ms, turns)
    _add_frame_metric(
        out, builder, BY_ID["separation_angle"], series.separation, t_ms, turns
    )
    _add_frame_metric(
        out,
        builder,
        BY_ID["upper_body_quiet"],
        series.separation,
        t_ms,
        turns,
        aggregate=_std,
    )
    spec = BY_ID["knee_valgus"]
    for side in SIDES:
        _add_frame_metric(
            out, builder, spec, series.valgus[side], t_ms, turns, side=side
        )
    _combine_sides(out, builder, spec, series.valgus, t_ms, turns)


def _rhythm(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    signal: SteeringSignal,
    turns: list[Turn],
    fps_effective: float,
) -> None:
    t_ms = series.t_ms

    spec = BY_ID["turn_rate"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        span_s = _segmented_span_s(t_ms, turns, fps_effective)
        if span_s is None:
            out[spec.id] = builder.unknown(spec, "segmented_span_too_short")
        else:
            out[spec.id] = builder.ok(
                spec,
                len(turns) / span_s,
                samples=len(turns),
                evidence_ms=turns[0].t_start_ms,
            )

    spec = BY_ID["turn_duration_var"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        durations = np.array([turn.duration_s for turn in turns], dtype=np.float64)
        mean = _mean(durations)
        std = _std(durations)
        if mean is None or std is None or mean < 1e-3:
            out[spec.id] = builder.unknown(spec, "fewer_than_two_turns")
        else:
            out[spec.id] = builder.ok(
                spec, std / mean, samples=len(turns), evidence_ms=turns[0].t_start_ms
            )

    spec = BY_ID["turn_amplitude"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        amps: list[float | None] = [turn.amplitude_deg for turn in turns]
        out[spec.id] = builder.ok(
            spec,
            _mean([turn.amplitude_deg for turn in turns]),
            samples=len(turns),
            per_turn=amps,
            evidence_ms=turns[0].t_start_ms,
        )

    shape = _turn_shape_index(signal, turns)
    spec = BY_ID["turn_shape_index"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        out[spec.id] = builder.ok(
            spec,
            _aggregate_turns(shape),
            samples=len([v for v in shape if v is not None]),
            per_turn=shape,
            evidence_ms=turns[0].t_start_ms,
        )

    edge_change = _edge_change_durations(signal, turns)
    spec = BY_ID["edge_change_duration"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        out[spec.id] = builder.ok(
            spec,
            _aggregate_turns(edge_change),
            samples=len([v for v in edge_change if v is not None]),
            per_turn=edge_change,
            evidence_ms=turns[0].t_start_ms,
        )

    spec = BY_ID["flexion_range"]
    for side in SIDES:
        _add_frame_metric(
            out,
            builder,
            spec,
            series.flexion[side],
            t_ms,
            turns,
            aggregate=_p_range,
            side=side,
        )
    _combine_sides_reducer(
        out, builder, spec, series.flexion, t_ms, turns, reducer=_p_range
    )

    spec = BY_ID["flexion_rate"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        rate = _zero_cross_rate(series.flexion_mean, fps_effective)
        if rate is None:
            out[spec.id] = builder.unknown(spec, REASON_NO_SAMPLES)
        else:
            out[spec.id] = builder.ok(
                spec, rate, samples=_count(series.flexion_mean)
            )

    spec = BY_ID["pressure_peak_phase"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        phases = _pressure_peak_phases(series, turns)
        out[spec.id] = builder.ok(
            spec,
            _aggregate_turns(phases),
            samples=len([v for v in phases if v is not None]),
            per_turn=phases,
            evidence_ms=turns[0].t_start_ms,
        )


def _combine_sides_reducer(
    out: dict[str, MetricValue],
    builder: _Builder,
    spec: MetricSpec,
    per_side: dict[str, np.ndarray],
    t_ms: np.ndarray,
    turns: list[Turn],
    reducer: Any,
) -> None:
    """Like :func:`_combine_sides` but with a non-median reducer per window."""
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
        return
    values = [
        out[f"{spec.id}_{side}"].value
        for side in SIDES
        if f"{spec.id}_{side}" in out
        and out[f"{spec.id}_{side}"].state == "ok"
        and out[f"{spec.id}_{side}"].value is not None
    ]
    if not values:
        out[spec.id] = builder.unknown(spec, REASON_NO_SAMPLES)
        return
    per_turn: list[float | None] | None = None
    if turns and "T" in spec.forms:
        per_turn = []
        for turn in turns:
            sides = [
                reducer(_window_values(per_side[side], t_ms, turn.window("all")))
                for side in SIDES
            ]
            good = [v for v in sides if v is not None]
            per_turn.append(float(np.mean(good)) if good else None)
    stacked = np.concatenate([per_side[side] for side in SIDES])
    out[spec.id] = builder.ok(
        spec,
        float(np.mean(values)),
        samples=_count(stacked),
        per_turn=per_turn,
    )


def _segmented_span_s(
    t_ms: np.ndarray, turns: list[Turn], fps_effective: float
) -> float | None:
    """Duration of the segmented span, derived from sample count and fps.

    Deliberately computed as ``n_samples / fps_effective`` rather than from the
    timestamp difference: this is the formula v2 got wrong
    (``signals.py:266``), and computing it this way means passing the source fps
    for stride-sampled frames reproduces the 2x error, so the regression test
    in ``tests/test_metrics.py`` actually tests something. The two forms agree
    whenever ``fps_effective`` matches the sampling.
    """
    if not turns:
        return None
    mask = (t_ms >= turns[0].t_start_ms) & (t_ms <= turns[-1].t_end_ms)
    samples = int(np.count_nonzero(mask))
    if samples < 2:
        return None
    span = samples / max(float(fps_effective), 1.0)
    return span if span >= MIN_SPAN_S else None


def _turn_shape_index(signal: SteeringSignal, turns: list[Turn]) -> list[float | None]:
    """Fraction of the arc spent at or above half the peak steering angle.

    **Invented formula.** The design defines ``turn_shape_index`` as
    "shaping-phase duration over total turn duration", but the phase split of
    §3.3 is by fixed thirds, so that ratio would be the constant 1/3. The
    quantity actually wanted is C-shape versus Z-shape, so the *effective*
    shaping duration is measured from the signal: the time inside the arc where
    ``|theta| >= 0.5 * amplitude``. A round C-shaped turn holds a high steering
    angle for a long fraction of the arc; a Z-shaped pivot-and-skid spikes
    briefly and gives a small index. Assumption: half of the peak steering
    angle is the "holding the arc" threshold.
    """
    out: list[float | None] = []
    for turn in turns:
        mask = window_mask(signal.t_ms, turn.window("all"))
        arc = signal.theta_deg[mask]
        if arc.size < 3 or turn.amplitude_deg <= 0.0:
            out.append(None)
            continue
        hold = np.count_nonzero(
            np.abs(arc) >= SHAPE_HOLD_FRACTION * turn.amplitude_deg
        )
        out.append(float(hold) / float(arc.size))
    return out


def _edge_change_durations(
    signal: SteeringSignal, turns: list[Turn]
) -> list[float | None]:
    """Time spent flat around a turn boundary, in seconds.

    **Invented formula.** The design calls this "transition window length",
    which for a fixed-fraction window would again be a constant. Measured
    instead: the contiguous run of samples around the start boundary where
    ``|theta| < 0.25 * mean(amplitude of the two adjacent arcs)``, converted to
    seconds from the sample timestamps. Assumption: a quarter of the arc
    amplitude marks the band in which the skis are between edges.
    """
    out: list[float | None] = []
    t_ms = signal.t_ms
    theta = signal.theta_deg
    for i, turn in enumerate(turns):
        prev_amp = turns[i - 1].amplitude_deg if i > 0 else turn.amplitude_deg
        band = EDGE_BAND_FRACTION * 0.5 * (prev_amp + turn.amplitude_deg)
        if band <= 0.0 or t_ms.size < 3:
            out.append(None)
            continue
        centre = int(np.argmin(np.abs(t_ms - turn.t_start_ms)))
        if not np.isfinite(theta[centre]) or abs(theta[centre]) >= band:
            out.append(0.0)
            continue
        lo = centre
        while lo - 1 >= 0 and abs(theta[lo - 1]) < band:
            lo -= 1
        hi = centre
        while hi + 1 < theta.size and abs(theta[hi + 1]) < band:
            hi += 1
        out.append(max(float(t_ms[hi] - t_ms[lo]) / 1000.0, 0.0))
    return out


def _pressure_peak_phases(
    series: FrameSeries, turns: list[Turn]
) -> list[float | None]:
    """Normalised position of deepest flexion inside each arc (0 = initiation)."""
    out: list[float | None] = []
    for turn in turns:
        mask = window_mask(series.t_ms, turn.window("all"))
        values = series.flexion_mean[mask]
        times = series.t_ms[mask]
        good = np.isfinite(values)
        span = turn.t_end_ms - turn.t_start_ms
        if not np.any(good) or span <= 0.0:
            out.append(None)
            continue
        idx = int(np.argmax(values[good]))
        phase = (float(times[good][idx]) - turn.t_start_ms) / span
        out.append(_clamp01(phase))
    return out


def _fault_counts(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    signal: SteeringSignal,
    turns: list[Turn],
) -> None:
    t_ms = series.t_ms

    # stem_count: transition wedge above the stem band.
    spec = BY_ID["stem_count"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        out[spec.id] = _count_metric(
            builder,
            spec,
            turns,
            lambda turn: _median(
                _window_values(series.wedge_deg, t_ms, turn.transition)
            ),
            lambda value: value > STEM_WEDGE_DEG,
        )

    # backseat_count: hips behind the band at the finish.
    spec = BY_ID["backseat_count"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        def finish_hof(turn: Turn) -> float | None:
            sides = [
                _median(_window_values(series.hip_over_foot[side], t_ms, turn.finish))
                for side in SIDES
            ]
            good = [v for v in sides if v is not None]
            return float(np.mean(good)) if good else None

        out[spec.id] = _count_metric(
            builder, spec, turns, finish_hof, lambda value: value < BACKSEAT_RATIO
        )

    # rotation_count: the upper body leads the skis into the new arc.
    spec = BY_ID["rotation_count"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        out[spec.id] = _count_metric(
            builder,
            spec,
            turns,
            lambda turn: _rotation_lead(series, signal, turn),
            lambda value: value >= ROTATION_DEG,
        )

    # braking_count: the arc collapses into a late steering spike.
    spec = BY_ID["braking_count"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        shape = _turn_shape_index(signal, turns)
        peaks = _steering_peak_phases(signal, turns)

        def braking(turn: Turn) -> float | None:
            idx = turn.index
            if idx >= len(shape) or shape[idx] is None or peaks[idx] is None:
                return None
            collapsed = shape[idx] < BRAKING_SHAPE_MAX
            late = peaks[idx] > BRAKING_PEAK_PHASE
            return 1.0 if (collapsed and late) else 0.0

        out[spec.id] = _count_metric(
            builder, spec, turns, braking, lambda value: value >= 0.5
        )

    _asymmetry(out, builder, series)


def _rotation_lead(
    series: FrameSeries, signal: SteeringSignal, turn: Turn
) -> float | None:
    """Degrees by which separation_angle rotates *with* the new arc.

    **Invented formula.** The design says "turns where separation_angle leads
    the skis into the turn" without a formula. Implemented as: compare the mean
    separation angle in the transition with the mean in the initiation. If it
    moves in the same direction as the steering angle does over the same pair of
    windows, the upper body is turning with (or ahead of) the skis rather than
    staying quiet, and the magnitude of that co-directed change is returned.
    Counter-rotation (the correct pattern) returns 0.
    """
    sep_trans = _median(_window_values(series.separation, series.t_ms, turn.transition))
    sep_init = _median(_window_values(series.separation, series.t_ms, turn.initiation))
    th_trans = _median(_window_values(signal.theta_deg, signal.t_ms, turn.transition))
    th_init = _median(_window_values(signal.theta_deg, signal.t_ms, turn.initiation))
    if None in (sep_trans, sep_init, th_trans, th_init):
        return None
    d_sep = float(sep_init) - float(sep_trans)  # type: ignore[arg-type]
    d_theta = float(th_init) - float(th_trans)  # type: ignore[arg-type]
    if d_sep == 0.0 or d_theta == 0.0:
        return 0.0
    if (d_sep > 0.0) != (d_theta > 0.0):
        return 0.0
    return abs(d_sep)


def _steering_peak_phases(
    signal: SteeringSignal, turns: list[Turn]
) -> list[float | None]:
    out: list[float | None] = []
    for turn in turns:
        mask = window_mask(signal.t_ms, turn.window("all"))
        arc = signal.theta_deg[mask]
        times = signal.t_ms[mask]
        span = turn.t_end_ms - turn.t_start_ms
        if arc.size < 3 or span <= 0.0:
            out.append(None)
            continue
        idx = int(np.argmax(np.abs(arc)))
        out.append(_clamp01((float(times[idx]) - turn.t_start_ms) / span))
    return out


def _count_metric(
    builder: _Builder,
    spec: MetricSpec,
    turns: list[Turn],
    measure: Any,
    is_faulty: Any,
) -> MetricValue:
    """Build a ``C``-form value: faulty turns out of measurable turns.

    Turns whose quantity cannot be measured are excluded from ``total_turns``
    rather than assumed clean, so the report's *"stems in 3 of 22 transitions"*
    phrasing (design §6.1) stays honest, and the missing evidence shows up as
    reduced reliability instead.
    """
    per_turn: list[float | None] = []
    faulty = 0
    total = 0
    first_bad: float | None = None
    for turn in turns:
        value = measure(turn)
        per_turn.append(value)
        if value is None or not np.isfinite(value):
            continue
        total += 1
        if is_faulty(value):
            faulty += 1
            if first_bad is None:
                first_bad = turn.t_start_ms
    if total == 0:
        return builder.unknown(spec, REASON_NO_SAMPLES)
    coverage = total / max(len(turns), 1)
    reliability = builder.reliability(spec, total) * coverage
    return builder.ok(
        spec,
        float(faulty),
        samples=total,
        form="C",
        per_turn=per_turn,
        faulty_turns=faulty,
        total_turns=total,
        evidence_ms=first_bad,
        reliability=reliability,
    )


def _asymmetry(
    out: dict[str, MetricValue], builder: _Builder, series: FrameSeries
) -> None:
    """Mean signed left-minus-right difference over pooled sd (design §3.4).

    **Formula detail invented where the design is silent.** For every paired
    metric with both sides measured, ``d = |left| - |right|`` is divided by the
    pooled standard deviation of the two per-frame series. The divisor is
    floored at 5 % of the pair's mean magnitude (and at ``1e-6`` absolutely) and
    the resulting z score is clipped to +/-6. That floor is the whole point: a
    near-constant pair would otherwise divide a tiny numerator by a tinier
    denominator and produce exactly the kind of ~1000x artefact v2 has at
    ``signals.py:168``. A symmetric skier scores ~0; the sign says which side
    carries more of the quantity.

    Assumption behind the magnitudes: for the signed lateral and fore/aft pairs
    (``knee_valgus``, ``hip_over_foot``, ``shin_angle_fore_aft``) a single 2D
    view mixes the sagittal and frontal axes, and the mixing term enters the two
    sides with opposite sign. Comparing magnitudes cancels that projection
    artefact and still answers the question the design asks — which side is
    doing less — while the two already non-negative pairs
    (``edge_angle_proxy``, ``flexion_range``) are unaffected by taking ``abs``.
    """
    spec = BY_ID["asymmetry_index"]
    pools: dict[str, dict[str, np.ndarray]] = {
        "shin_angle_fore_aft": series.shin_deg,
        "hip_over_foot": series.hip_over_foot,
        "edge_angle_proxy": series.edge_deg,
        "knee_valgus": series.valgus,
        "flexion_range": series.flexion,
    }
    scores: list[float] = []
    samples = 0
    for metric_id in PAIRED_METRICS:
        left = out.get(f"{metric_id}_left")
        right = out.get(f"{metric_id}_right")
        if (
            left is None
            or right is None
            or left.state != "ok"
            or right.state != "ok"
            or left.value is None
            or right.value is None
        ):
            continue
        pool = pools.get(metric_id)
        if pool is None:
            continue
        stacked = np.concatenate([np.abs(pool["left"]), np.abs(pool["right"])])
        sd = _std(stacked) or 0.0
        magnitude = 0.5 * (abs(left.value) + abs(right.value))
        floor = max(ASYM_REL_FLOOR * magnitude, ASYM_ABS_FLOOR)
        divisor = max(sd, floor)
        z = (abs(left.value) - abs(right.value)) / divisor
        scores.append(float(np.clip(z, -ASYM_Z_CLIP, ASYM_Z_CLIP)))
        samples += _count(stacked)
    if not scores:
        out[spec.id] = builder.unknown(spec, "no_paired_metrics_available")
        return
    out[spec.id] = builder.ok(
        spec,
        float(np.mean(scores)),
        samples=samples,
        reliability=builder.reliability(spec, len(scores) * 10),
    )


def _poles_and_hands(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    turns: list[Turn],
) -> None:
    t_ms = series.t_ms

    spec = BY_ID["hands_in_view"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        n = max(t_ms.size, 1)
        samples = _count(series.hands_forward)
        if samples / n < MIN_WRIST_FRACTION:
            out[spec.id] = builder.unknown(spec, "wrists_not_visible")
        else:
            out[spec.id] = builder.ok(
                spec, _mean(series.hands_forward), samples=samples
            )

    spikes = _pole_spikes(series)
    matches = _match_spikes_to_turns(spikes, turns)

    spec = BY_ID["pole_touch_rate"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        matched = len([m for m in matches if m is not None])
        out[spec.id] = builder.ok(
            spec,
            matched / max(len(turns), 1),
            samples=len(turns),
            evidence_ms=turns[0].t_start_ms if turns else None,
        )

    spec = BY_ID["pole_touch_timing"]
    blocked = builder.blocked(spec)
    if blocked is not None:
        out[spec.id] = blocked
    else:
        offsets = [m for m in matches if m is not None]
        if not offsets:
            out[spec.id] = builder.unknown(spec, "no_pole_touch_detected")
        else:
            out[spec.id] = builder.ok(
                spec,
                float(np.mean(offsets)),
                samples=len(offsets),
                per_turn=list(matches),
                evidence_ms=turns[0].t_start_ms,
            )


def _pole_spikes(series: FrameSeries) -> list[float]:
    """Timestamps of wrist-velocity spikes.

    **Invented formula.** The design says "detected wrist-velocity spikes"
    without a detector. Implemented as: wrist speed in leg lengths per second
    (the faster of the two wrists), threshold at ``median + 2 * 1.4826 * MAD``
    with an absolute floor of 0.6 leg lengths per second, keep local maxima, and
    apply a 0.25 s refractory so one plant is not counted twice. Assumption: a
    pole plant is the fastest thing the hand does near a transition; without a
    pole tip landmark this is the closest observable.
    """
    speed = series.wrist_speed
    good = np.isfinite(speed)
    if np.count_nonzero(good) < 4:
        return []
    values = speed[good]
    times = series.t_ms[good]
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) * 1.4826
    threshold = max(median + POLE_SPIKE_MAD_K * mad, POLE_SPIKE_MIN_LEG_PER_S)
    out: list[float] = []
    last = -1e18
    for i in range(values.size):
        if values[i] < threshold:
            continue
        if i > 0 and values[i - 1] > values[i]:
            continue
        if i + 1 < values.size and values[i + 1] > values[i]:
            continue
        if (times[i] - last) / 1000.0 < POLE_REFRACTORY_S:
            continue
        out.append(float(times[i]))
        last = float(times[i])
    return out


def _match_spikes_to_turns(
    spikes: list[float], turns: list[Turn]
) -> list[float | None]:
    """Signed offset in seconds of the nearest spike to each turn boundary.

    A spike counts for a turn when it falls within
    ``POLE_MATCH_FRACTION * duration`` of the start boundary; at most one spike
    per turn, so the rate stays in ``[0, 1]``. Negative offsets mean the plant
    happened before the edge change.
    """
    out: list[float | None] = []
    for turn in turns:
        tolerance = POLE_MATCH_FRACTION * turn.duration_s * 1000.0
        best: float | None = None
        for spike in spikes:
            delta = spike - turn.t_start_ms
            if abs(delta) > tolerance:
                continue
            if best is None or abs(delta) < abs(best):
                best = delta
        out.append(None if best is None else best / 1000.0)
    return out


def _quality(
    out: dict[str, MetricValue],
    builder: _Builder,
    series: FrameSeries,
    view: ViewEstimate,
    turns: list[Turn],
    landmark_quality: float,
    usable_ratio: float,
    camera_motion: str,
    fps_effective: float,
) -> None:
    spec = BY_ID["view_azimuth_deg"]
    if view.azimuth_deg is None:
        out[spec.id] = builder.unknown(spec, REASON_NO_SCALE)
    else:
        out[spec.id] = builder.ok(
            spec,
            view.azimuth_deg,
            samples=int(series.t_ms.size),
            reliability=_clamp01(landmark_quality / RELIABILITY_QUALITY_FULL),
        )
    spec = BY_ID["view_class"]
    out[spec.id] = builder.ok(
        spec,
        None,
        samples=int(series.t_ms.size),
        text=str(view.view_class.value),
        reason=view.reason,
        reliability=_clamp01(landmark_quality / RELIABILITY_QUALITY_FULL),
    )
    spec = BY_ID["landmark_quality"]
    out[spec.id] = builder.ok(
        spec, landmark_quality, samples=int(series.t_ms.size), reliability=1.0
    )
    spec = BY_ID["usable_frame_ratio"]
    out[spec.id] = builder.ok(
        spec, usable_ratio, samples=int(series.t_ms.size), reliability=1.0
    )
    spec = BY_ID["camera_motion"]
    out[spec.id] = builder.ok(
        spec,
        None,
        samples=int(series.t_ms.size),
        text=camera_motion,
        reliability=0.4,
    )
    spec = BY_ID["fps_effective"]
    out[spec.id] = builder.ok(
        spec, fps_effective, samples=int(series.t_ms.size), reliability=1.0
    )
    spec = BY_ID["turn_count"]
    out[spec.id] = builder.ok(
        spec, float(len(turns)), samples=max(len(turns), 1), reliability=1.0
    )


def _infer_camera_motion(
    series: FrameSeries, scale: BodyScale, scene: SceneContext | None
) -> str:
    """static / panning / follow from hip travel over body scale.

    **Invented formula.** The design lists ``camera_motion`` as "inferred" with
    no method, and background optical flow is not available in this layer, so
    the only observable is how far the skier translates within the frame
    relative to their own size: a static camera lets the skier cross the frame
    (large travel), a follow camera keeps them centred (small travel). Bands:
    ``>= 3`` leg lengths of travel is ``static``, ``<= 1`` is ``follow``, in
    between ``panning``. Weak by construction, which is why the metric carries
    reliability 0.4 and an explicit scene override wins. Note for callers: the
    design says a follow camera invalidates whole-clip frequency metrics; here
    the steering signal already degrades its tangent instead
    (``SteeringSignal.tangent_source``).
    """
    if scene is not None and scene.camera_motion is not None:
        return str(getattr(scene.camera_motion, "value", scene.camera_motion))
    xs = series.hip_mid[:, 0]
    ys = series.hip_mid[:, 1]
    good = np.isfinite(xs) & np.isfinite(ys)
    if np.count_nonzero(good) < 3 or not scale.ok:
        return CAMERA_UNKNOWN
    travel = float(
        np.hypot(
            np.max(xs[good]) - np.min(xs[good]), np.max(ys[good]) - np.min(ys[good])
        )
    )
    ratio = travel / float(scale.leg_len_px or 1.0)
    if ratio >= CAMERA_STATIC_TRAVEL:
        return CameraMotion.STATIC.value
    if ratio <= CAMERA_FOLLOW_TRAVEL:
        return CameraMotion.FOLLOW.value
    return CameraMotion.PANNING.value


def _missing_landmarks(arrays: LandmarkArrays) -> frozenset[int]:
    """Indices with no finite coordinate in any frame of the clip.

    Deliberately strict: a joint tracked in even one frame is *weak*, not
    *absent*, and weakness is already carried by ``reliability``. Absence is
    what a metric's ``requires.landmarks`` is about.
    """
    if arrays.n == 0:
        return frozenset()
    present = np.any(np.isfinite(arrays.x), axis=0)
    return frozenset(
        int(index) for index in np.flatnonzero(~present)
    )


def _landmark_quality(arrays: LandmarkArrays) -> float:
    """Mean over frames of the weakest core-landmark visibility."""
    if arrays.n == 0:
        return 0.0
    core = arrays.conf[:, list(CORE_LANDMARKS)]
    return float(np.mean(np.min(core, axis=1)))


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def compute_metrics(
    analysis: ClipAnalysis,
    turns: list[Turn] | None = None,
    profile: Any | None = None,
    scene: SceneContext | dict | None = None,
    *,
    fps_effective: float | None = None,
    frame_stride: int = 1,
    clip_date: date | None = None,
) -> MetricPack:
    """Compute the whole §3.4 catalog for one clip.

    ``turns`` should come from :func:`core.sports.turns.segment_turns`; pass
    ``None`` and it is segmented here with the same ``fps_effective``.

    ``profile`` accepts an :class:`~core.sports.profile.AthleteContext`, the
    ``athlete`` block on the analysis, a stored profile snapshot or anything
    with those attributes; ``None`` falls back to ``analysis.athlete``.
    ``scene`` likewise accepts a :class:`~core.sports.scene.SceneContext` or the
    stored ``scene`` block, falling back to ``analysis.scene``.

    ``fps_effective`` resolution order: the explicit argument, then the resolved
    scene's ``fps_effective`` (which is what the pipeline records), then
    ``analysis.fps_effective``, then ``effective_fps(analysis.fps,
    frame_stride)``. A caller that has neither a scene nor a recorded rate must
    pass ``frame_stride`` (2 for the Windows pipeline) or the rate metrics
    inherit v2's 2x error.

    Never raises for degenerate input: a five-frame clip, a clip with no
    ``blaze33``, or an all-low-confidence clip returns a pack in which every
    metric carries ``state="unknown"`` and a reason.
    """
    frames = list(analysis.frames)
    resolved_scene = resolve_scene(
        scene if scene is not None else getattr(analysis, "scene", None)
    )
    recorded = getattr(analysis, "fps_effective", None)
    fps = _first_positive(
        fps_effective,
        resolved_scene.fps_effective,
        recorded,
        effective_fps(analysis.fps, frame_stride),
    )
    if profile is None:
        profile = getattr(analysis, "athlete", None)
    athlete = build_athlete_context(profile, clip_date=clip_date)
    arrays = landmark_arrays(frames)
    scale = estimate_body_scale(arrays, athlete)
    view = estimate_view(arrays, scale)
    signal = steering_signal(frames, fps, arrays=arrays)
    if turns is None:
        from core.sports.turns import segment_turns_from_signal

        turns = segment_turns_from_signal(signal)
    series = build_series(arrays, scale, view, fps)
    quality = _landmark_quality(arrays)
    usable_ratio = (
        float(np.count_nonzero(series.usable)) / float(arrays.n) if arrays.n else 0.0
    )
    camera_motion = _infer_camera_motion(series, scale, resolved_scene)
    builder = _Builder(
        view=view,
        athlete=athlete,
        landmark_quality=quality,
        turns=turns,
        forward_source=series.forward_source,
        missing_landmarks=_missing_landmarks(arrays),
    )
    out: dict[str, MetricValue] = {}
    if scale.ok:
        _stance_and_balance(out, builder, series, turns, scale)
        _edging_and_steering(out, builder, series, turns)
        _rhythm(out, builder, series, signal, turns, fps)
        _fault_counts(out, builder, series, signal, turns)
        _poles_and_hands(out, builder, series, turns)
    else:
        for spec in REGISTRY:
            if spec.group == "quality":
                continue
            out[spec.id] = builder.unknown(spec, REASON_NO_SCALE)
            for side_id, side in zip(spec.side_ids, SIDES):
                out[side_id] = builder.unknown(spec, REASON_NO_SCALE, side=side)
    _quality(
        out,
        builder,
        series,
        view,
        turns,
        quality,
        usable_ratio,
        camera_motion,
        fps,
    )
    _fill_missing(out, builder)
    return MetricPack(
        metrics=out,
        view=view,
        scale=scale,
        athlete=athlete,
        scene=resolved_scene,
        fps_effective=fps,
        turn_count=len(turns),
        landmark_quality=quality,
        usable_frame_ratio=usable_ratio,
        camera_motion=camera_motion,
        n_frames=arrays.n,
    )


def _fill_missing(out: dict[str, MetricValue], builder: _Builder) -> None:
    """Guarantee every registry id (and side variant) is present in the pack."""
    for spec in REGISTRY:
        if spec.id not in out:
            out[spec.id] = builder.unknown(spec, REASON_NO_SAMPLES)
        for side_id, side in zip(spec.side_ids, SIDES):
            if side_id not in out:
                out[side_id] = builder.unknown(spec, REASON_NO_SAMPLES, side=side)


def metric_summary(
    pack: MetricPack, ids: Iterable[str] | None = None
) -> dict[str, Any]:
    """Flat, JSON-friendly view of a pack; handy for fixtures and debugging."""
    keys = tuple(ids) if ids is not None else metric_ids()
    out: dict[str, Any] = {}
    for key in keys:
        item = pack.metrics.get(key)
        if item is None:
            continue
        out[key] = {
            "value": item.value,
            "text": item.text,
            "unit": item.unit,
            "state": item.state,
            "reason": item.reason,
            "reliability": round(item.reliability, 3),
            "faulty_turns": item.faulty_turns,
            "total_turns": item.total_turns,
        }
    return out
