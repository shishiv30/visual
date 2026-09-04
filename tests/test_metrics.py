"""Metric catalog tests (design v3 §3.1-§3.4)."""

from __future__ import annotations

import datetime
import math

import numpy as np

from core.sports.metrics import (
    BY_ID,
    LATERAL_MIN_AZIMUTH_DEG,
    PAIRED_METRICS,
    REASON_TOO_FRONTAL,
    REASON_TOO_PROFILE,
    REGISTRY,
    SAGITTAL_MAX_AZIMUTH_DEG,
    SIDES,
    MetricPack,
    _wedge_foot_weight,
    build_athlete_context,
    carving_applicable,
    compute_metrics,
    effective_fps,
    metric_ids,
    metric_summary,
    spec_for,
)
from core.sports.metrics import STEM_WEDGE_DEG
from core.sports.profile import AthleteContext
from core.sports.scene import CameraMotion, SceneContext, ViewClass
from core.sports.turns import segment_turns
from tests import ski_fixtures as F

FPS = 15.0


class _Profile:
    """Duck-typed stand-in for ``clients.windows.store.athletes.AthleteProfile``."""

    def __init__(
        self,
        birthday: str = "1990-04-02",
        height_cm: float = 175.0,
        weight_kg: float = 72.0,
        ski_cm: float = 165.0,
        gender: str = "female",
    ) -> None:
        self.birthday = birthday
        self.height_cm = height_cm
        self.weight_kg = weight_kg
        self.ski_cm = ski_cm
        self.gender = gender


CLIP_DATE = datetime.date(2026, 8, 30)


def _pack(clip, **kwargs) -> MetricPack:
    turns = segment_turns(clip.frames, kwargs.get("fps_effective", FPS))
    return compute_metrics(clip, turns, **kwargs)


def _lateral_ids() -> list[str]:
    skip = {"ski_wedge_angle", "ski_parallelism"}
    return [
        spec.id
        for spec in REGISTRY
        if spec.requires.view == "lateral" and spec.id not in skip
    ]


def _sagittal_ids() -> list[str]:
    return [spec.id for spec in REGISTRY if spec.requires.view == "sagittal"]


# --- registry ---------------------------------------------------------------


def test_registry_matches_the_design_catalog() -> None:
    groups = {
        "stance": 8,
        "edging": 7,
        "rhythm": 8,
        "faults": 5,
        "poles": 3,
        "quality": 7,
    }
    counts: dict[str, int] = {}
    for spec in REGISTRY:
        counts[spec.group] = counts.get(spec.group, 0) + 1
    assert counts == groups
    assert len(REGISTRY) == sum(groups.values()) == 38


def test_registry_entries_are_well_formed() -> None:
    ids = [spec.id for spec in REGISTRY]
    assert len(ids) == len(set(ids))
    for spec in REGISTRY:
        assert spec.forms, spec.id
        assert set(spec.forms) <= {"A", "T", "C"}, spec.id
        assert spec.noise_class in {"low", "medium", "high"}, spec.id
        assert spec.unit in {"ratio", "deg", "Hz", "s", "count", "class"}, spec.id
        assert spec.requires.view in {"any", "lateral", "sagittal"}, spec.id
        assert spec.description.strip(), spec.id
        assert spec.denominator, spec.id


def test_quality_metrics_are_never_scored() -> None:
    for spec in REGISTRY:
        if spec.group == "quality":
            assert not spec.scored, spec.id
        else:
            assert spec.scored, spec.id


def test_metric_ids_cover_side_variants() -> None:
    ids = metric_ids()
    assert len(ids) == len(set(ids))
    assert len(ids) == len(REGISTRY) + 2 * len(PAIRED_METRICS)
    for metric_id in PAIRED_METRICS:
        for side in SIDES:
            assert f"{metric_id}_{side}" in ids
    assert metric_ids(include_sides=False) == tuple(spec.id for spec in REGISTRY)


def test_spec_for_resolves_side_ids_only_for_paired_metrics() -> None:
    assert spec_for("knee_valgus_left") is BY_ID["knee_valgus"]
    assert spec_for("knee_valgus") is BY_ID["knee_valgus"]
    assert spec_for("stance_width_left") is None
    assert spec_for("nonsense") is None


def test_count_form_metrics_are_the_five_fault_metrics() -> None:
    count_forms = {spec.id for spec in REGISTRY if "C" in spec.forms}
    assert count_forms == {
        "hip_over_foot",
        "stem_count",
        "backseat_count",
        "rotation_count",
        "braking_count",
    }


# --- clean fixture ----------------------------------------------------------


def test_every_registry_id_is_present_in_the_pack() -> None:
    pack = _pack(F.parallel_skier())
    for metric_id in metric_ids():
        assert metric_id in pack.metrics, metric_id
        assert pack.metrics[metric_id].metric_id == metric_id


def test_parallel_fixture_values_are_plausible() -> None:
    pack = _pack(F.parallel_skier())
    assert pack.turn_count == 10
    assert pack.view is not None and pack.view.view_class == "quarter"
    assert abs(pack.value("turn_rate") - 1.0) < 0.1
    assert abs(pack.value("flexion_rate") - 1.0) < 0.15
    assert 0.2 < pack.value("stance_width") < 0.35
    assert pack.value("wedge_angle") < 2.0
    assert 15.0 < pack.value("flexion_range") < 30.0
    assert 0.0 <= pack.value("turn_shape_index") <= 1.0
    assert 0.0 <= pack.value("pressure_peak_phase") <= 1.0
    assert 15.0 < pack.value("turn_amplitude") < 30.0
    assert pack.value("turn_count") == 10.0
    assert pack.value("usable_frame_ratio") == 1.0
    assert pack.metrics["view_class"].text == "quarter"
    assert pack.metrics["view_class"].value is None
    assert pack.metrics["camera_motion"].text == "static"


def test_clean_fixture_reports_no_faults() -> None:
    pack = _pack(F.parallel_skier())
    faults = ("stem_count", "backseat_count", "rotation_count", "braking_count")
    for metric_id in faults:
        item = pack.metrics[metric_id]
        assert item.state == "ok", (metric_id, item.reason)
        assert item.faulty_turns == 0, metric_id
        assert item.total_turns == pack.turn_count, metric_id
        assert item.form == "C"


def test_per_turn_series_align_with_the_turn_list() -> None:
    clip = F.parallel_skier()
    turns = segment_turns(clip.frames, FPS)
    pack = compute_metrics(clip, turns)
    for spec in REGISTRY:
        if "T" not in spec.forms and "C" not in spec.forms:
            continue
        item = pack.metrics[spec.id]
        if item.per_turn is None:
            continue
        assert len(item.per_turn) == len(turns), spec.id
        for value in item.per_turn:
            assert value is None or math.isfinite(value), spec.id


def test_evidence_is_an_integer_timestamp_inside_the_clip() -> None:
    pack = _pack(F.parallel_skier())
    last = 1000.0 * (len(F.parallel_skier().frames) - 1) / FPS
    for item in pack.metrics.values():
        if item.evidence_ms is None:
            continue
        assert isinstance(item.evidence_ms, int)
        assert -1 <= item.evidence_ms <= last + 1


# --- view gating (§3.1) -----------------------------------------------------


def test_wedge_foot_weight_decreases_toward_profile() -> None:
    quarter = _wedge_foot_weight(40.0)
    profile = _wedge_foot_weight(SAGITTAL_MAX_AZIMUTH_DEG)
    assert quarter > profile
    assert profile == 0.0
    assert _wedge_foot_weight(LATERAL_MIN_AZIMUTH_DEG) == 0.40


def test_profile_view_suppresses_lateral_metrics_with_the_documented_reason() -> None:
    pack = _pack(F.profile_view_skier())
    assert pack.view is not None
    assert pack.view.view_class == "profile"
    assert pack.view.azimuth_deg < LATERAL_MIN_AZIMUTH_DEG
    assert pack.view.reason == REASON_TOO_PROFILE
    for metric_id in _lateral_ids():
        item = pack.metrics[metric_id]
        assert item.state == "unknown", metric_id
        assert item.reason == REASON_TOO_PROFILE, metric_id
        assert item.value is None, metric_id
        assert item.reliability == 0.0, metric_id


def test_profile_view_keeps_fore_aft_metrics() -> None:
    """A profile clip is the *best* view for fore/aft, so those stay measured."""
    pack = _pack(F.profile_view_skier())
    for metric_id in _sagittal_ids():
        assert pack.metrics[metric_id].state == "ok", metric_id


def test_frontal_view_suppresses_fore_aft_metrics() -> None:
    pack = _pack(F.frontal_view_skier())
    assert pack.view.azimuth_deg > SAGITTAL_MAX_AZIMUTH_DEG
    for metric_id in _sagittal_ids():
        item = pack.metrics[metric_id]
        assert item.state == "unknown", metric_id
        assert item.reason == REASON_TOO_FRONTAL, metric_id
    for metric_id in _lateral_ids():
        assert pack.metrics[metric_id].state == "ok", metric_id


def test_side_variants_are_suppressed_with_their_base_metric() -> None:
    pack = _pack(F.profile_view_skier())
    for side in SIDES:
        item = pack.metrics[f"knee_valgus_{side}"]
        assert item.state == "unknown"
        assert item.reason == REASON_TOO_PROFILE
        assert item.side == side


# --- fault counts -----------------------------------------------------------


def test_stemmed_fixture_counts_exactly_three_faulty_turns() -> None:
    pack = _pack(F.stemmed_skier())
    item = pack.metrics["stem_count"]
    assert item.state == "ok"
    assert item.faulty_turns == 3
    assert item.total_turns == pack.turn_count == 10
    assert item.value == 3.0
    assert item.form == "C"
    assert item.per_turn is not None and len(item.per_turn) == 10
    # First stemmed transition is the one centred on 3.0 s.
    assert item.evidence_ms is not None and abs(item.evidence_ms - 3000) < 150


def test_wedge_fixture_stems_every_transition() -> None:
    pack = _pack(F.wedge_skier())
    wedge_val = pack.value("wedge_angle")
    assert wedge_val is not None
    assert wedge_val > STEM_WEDGE_DEG - 5.0
    item = pack.metrics["stem_count"]
    assert item.faulty_turns == item.total_turns == pack.turn_count
    assert pack.value("stance_width") > 0.4


def test_clean_and_stemmed_differ_only_in_the_stem_metrics() -> None:
    clean = _pack(F.parallel_skier())
    stemmed = _pack(F.stemmed_skier())
    assert clean.metrics["stem_count"].faulty_turns == 0
    assert stemmed.metrics["stem_count"].faulty_turns == 3
    for metric_id in ("turn_rate", "stance_width", "flexion_range", "turn_count"):
        assert abs(clean.value(metric_id) - stemmed.value(metric_id)) < 1e-6, metric_id


def test_hip_over_foot_carries_the_count_form() -> None:
    pack = _pack(F.parallel_skier())
    item = pack.metrics["hip_over_foot"]
    assert item.state == "ok"
    assert item.total_turns == pack.turn_count
    assert item.faulty_turns == 0


def test_count_metrics_report_totals_not_just_ratios() -> None:
    pack = _pack(F.stemmed_skier())
    summary = metric_summary(pack, ["stem_count"])
    assert summary["stem_count"]["faulty_turns"] == 3
    assert summary["stem_count"]["total_turns"] == 10
    assert summary["stem_count"]["state"] == "ok"


# --- left / right and asymmetry --------------------------------------------


def test_paired_metrics_keep_both_sides() -> None:
    pack = _pack(F.parallel_skier())
    for metric_id in PAIRED_METRICS:
        left = pack.metrics[f"{metric_id}_left"]
        right = pack.metrics[f"{metric_id}_right"]
        combined = pack.metrics[metric_id]
        assert left.state == right.state == combined.state, metric_id
        if combined.state != "ok":
            continue
        assert left.side == "left" and right.side == "right"
        # Combined is the mean of the two sides, never a pooled median.
        assert abs(combined.value - 0.5 * (left.value + right.value)) < 1e-9, metric_id


def test_asymmetry_index_is_near_zero_for_a_symmetric_skier() -> None:
    pack = _pack(F.parallel_skier())
    item = pack.metrics["asymmetry_index"]
    assert item.state == "ok"
    assert abs(item.value) < 0.15


def test_asymmetry_index_is_clearly_non_zero_for_an_asymmetric_skier() -> None:
    pack = _pack(F.asymmetric_skier())
    item = pack.metrics["asymmetry_index"]
    assert item.state == "ok"
    assert abs(item.value) > 0.7
    # The left leg flexes far more, so the signed index points left.
    assert item.value > 0.0
    left = pack.value("flexion_range_left")
    right = pack.value("flexion_range_right")
    assert left > 3.0 * right


def test_asymmetry_index_is_bounded() -> None:
    for clip in (F.parallel_skier(), F.asymmetric_skier(), F.wedge_skier()):
        value = _pack(clip).value("asymmetry_index")
        assert value is None or abs(value) <= 6.0


def test_asymmetry_unknown_without_paired_metrics() -> None:
    pack = _pack(F.low_confidence_clip())
    item = pack.metrics["asymmetry_index"]
    assert item.state == "unknown"
    assert item.value is None


# --- fps_effective regression (the v2 2x bug) ------------------------------


def test_effective_fps_helper() -> None:
    assert effective_fps(30.0, 2) == 15.0
    assert effective_fps(30.0, 1) == 30.0
    assert effective_fps(0.0, 2) == 7.5  # falls back to a 15 fps source
    assert effective_fps(30.0, 0) == 30.0
    assert effective_fps(float("nan"), 1) == 15.0


def test_rates_are_identical_at_stride_1_and_stride_2() -> None:
    """Same motion, two samplings: frequencies must agree (design §2.2)."""
    full = F.make_clip(F.SkierParams(fps=30.0))
    strided = F.stride_sample(full, 2)
    at_30 = compute_metrics(full, frame_stride=1)
    at_15 = compute_metrics(strided, frame_stride=2)
    assert at_30.fps_effective == 30.0
    assert at_15.fps_effective == 15.0
    assert at_30.turn_count == at_15.turn_count
    for metric_id in ("flexion_rate", "turn_rate"):
        a = at_30.value(metric_id)
        b = at_15.value(metric_id)
        assert a is not None and b is not None, metric_id
        assert abs(a - b) < 0.05 * a, (metric_id, a, b)
        assert abs(a - 1.0) < 0.15, (metric_id, a)


def test_using_the_source_fps_on_strided_frames_reproduces_the_2x_error() -> None:
    """Pins the bug this layer fixes: v2 divided a stride-2 sample count by the
    source fps (``signals.py:266``) and reported roughly double the true Hz."""
    full = F.make_clip(F.SkierParams(fps=30.0))
    strided = F.stride_sample(full, 2)
    correct = compute_metrics(strided, frame_stride=2)
    wrong = compute_metrics(strided, frame_stride=1)
    for metric_id in ("flexion_rate", "turn_rate"):
        a = correct.value(metric_id)
        b = wrong.value(metric_id)
        assert abs(b / a - 2.0) < 0.05, (metric_id, a, b)


def test_analysis_scene_block_supplies_fps_effective() -> None:
    """The pipeline records the sampled rate on ``analysis.scene``; picking it up
    from there is what keeps a stored clip honest without a stride argument."""
    clip = F.stride_sample(F.make_clip(F.SkierParams(fps=30.0)), 2)
    clip.scene = SceneContext(fps_effective=15.0).to_dict()
    pack = compute_metrics(clip)
    assert pack.fps_effective == 15.0
    assert abs(pack.value("flexion_rate") - 1.0) < 0.15
    assert pack.scene is not None and pack.scene.fps_effective == 15.0


def test_analysis_athlete_block_is_used_when_no_profile_is_passed() -> None:
    clip = F.parallel_skier()
    clip.athlete = AthleteContext(
        age_years=10.0, height_m=1.3, mass_kg=30.0
    ).to_dict()
    pack = compute_metrics(clip)
    assert pack.athlete.age_band == "age-7-12"
    assert pack.metrics["banking_index"].state == "not_applicable"
    assert pack.scale.px_per_m is not None


def test_scene_can_supply_fps_effective() -> None:
    clip = F.stride_sample(F.make_clip(F.SkierParams(fps=30.0)), 2)
    pack = compute_metrics(clip, scene=SceneContext(fps_effective=15.0))
    assert pack.fps_effective == 15.0
    assert pack.value("fps_effective") == 15.0


# --- denominator safety -----------------------------------------------------


def test_no_metric_is_nan_or_inf_on_any_fixture() -> None:
    clips = (
        F.parallel_skier(),
        F.wedge_skier(),
        F.profile_view_skier(),
        F.frontal_view_skier(),
        F.stemmed_skier(),
        F.asymmetric_skier(),
        F.poling_skier(),
        F.traverse_clip(),
        F.short_clip(),
        F.low_confidence_clip(),
        F.no_pose_clip(),
        F.parallel_skier(drop_landmarks=(11, 12)),
        F.parallel_skier(drop_landmarks=(27, 28)),
        F.parallel_skier(drop_landmarks=(31, 32)),
    )
    for clip in clips:
        pack = _pack(clip)
        for metric_id, item in pack.metrics.items():
            where = f"{clip.clip_id}.{metric_id}"
            assert item.state in {"ok", "unknown", "not_applicable"}, where
            if item.state != "ok":
                assert item.value is None, where
                assert item.reason, where
                continue
            if item.unit == "class":
                assert item.value is None and item.text, where
                continue
            assert item.value is not None, where
            assert math.isfinite(item.value), where
            assert 0.0 <= item.reliability <= 1.0, where
            if item.per_turn:
                for value in item.per_turn:
                    assert value is None or math.isfinite(value), where


def test_missing_shoulders_do_not_blow_up_a_ratio() -> None:
    """v2 divided by ``torso + 1e-3`` and produced a ~1000x ratio when the
    shoulders were missing (``signals.py:168``); nothing here may do that."""
    pack = _pack(F.parallel_skier(drop_landmarks=(11, 12)))
    for metric_id in ("inclination", "angulation", "banking_index", "separation_angle"):
        item = pack.metrics[metric_id]
        assert item.state in {"unknown", "not_applicable"}, metric_id
        assert item.value is None, metric_id
    # Unrelated rulers survive: one missing pair must not poison the pack.
    assert pack.metrics["stance_width"].state == "ok"
    assert abs(pack.value("stance_width") - 0.27) < 0.05
    assert pack.scale is not None and pack.scale.torso_len_px is None


def test_near_zero_denominator_is_suppressed_not_amplified() -> None:
    """A skier with no inclination at all leaves banking_index undefined rather
    than dividing by a fudged epsilon."""
    pack = _pack(F.traverse_clip())
    item = pack.metrics["banking_index"]
    assert item.state == "unknown"
    assert item.value is None


def test_missing_feet_suppress_only_the_foot_metrics() -> None:
    pack = _pack(F.parallel_skier(drop_landmarks=(31, 32)))
    assert pack.metrics["wedge_angle"].state == "unknown"
    assert pack.metrics["ski_wedge_angle"].state == "unknown"
    assert pack.metrics["ski_parallelism"].state == "unknown"
    assert pack.metrics["stem_count"].state == "unknown"
    assert pack.metrics["stance_width"].state == "ok"


# --- degenerate clips -------------------------------------------------------


def test_short_clip_returns_states_not_exceptions() -> None:
    pack = _pack(F.short_clip())
    assert pack.turn_count == 0
    assert pack.n_frames == 5
    for spec in REGISTRY:
        item = pack.metrics[spec.id]
        if spec.requires.turns:
            assert item.state == "unknown", spec.id
            assert item.reason == "no_turns_segmented", spec.id
    assert pack.metrics["turn_count"].value == 0.0


def test_low_confidence_clip_suppresses_everything_measurable() -> None:
    pack = _pack(F.low_confidence_clip())
    assert pack.landmark_quality < 0.25
    assert pack.usable_frame_ratio == 0.0
    assert pack.turn_count == 0
    for spec in REGISTRY:
        if spec.group == "quality":
            continue
        item = pack.metrics[spec.id]
        assert item.state == "unknown", spec.id
        assert item.reason == "body_scale_unavailable", spec.id
    assert pack.metrics["landmark_quality"].state == "ok"


def test_clip_without_blaze_landmarks_does_not_raise() -> None:
    pack = _pack(F.no_pose_clip())
    assert pack.n_frames == 8
    assert pack.usable_frame_ratio == 0.0
    assert pack.metrics["view_azimuth_deg"].state == "unknown"


def test_empty_clip_does_not_raise() -> None:
    clip = F.no_pose_clip(n=0)
    pack = compute_metrics(clip)
    assert pack.n_frames == 0
    assert len(pack.metrics) == len(metric_ids())


def test_traverse_clip_has_no_turn_metrics() -> None:
    pack = _pack(F.traverse_clip())
    assert pack.turn_count == 0
    assert pack.metrics["turn_rate"].state == "unknown"
    assert pack.metrics["turn_rate"].reason == "no_turns_segmented"
    assert pack.metrics["stance_width"].state == "ok"


# --- profile (§2.3) ---------------------------------------------------------


def test_profile_supplies_scale_priors_without_changing_ratios() -> None:
    clip = F.parallel_skier()
    without = _pack(clip)
    with_profile = _pack(clip, profile=_Profile(), clip_date=CLIP_DATE)
    assert without.scale.px_per_m is None
    assert with_profile.scale.px_per_m is not None
    assert with_profile.scale.leg_len_m is not None
    assert abs(with_profile.scale.leg_len_m - 0.53 * 1.75) < 1e-9
    assert (
        abs(without.value("stance_width") - with_profile.value("stance_width")) < 1e-9
    )
    assert with_profile.athlete.age_band == "age-18-39"
    assert with_profile.scale.bmi is not None
    assert with_profile.athlete.ski_len_ratio is not None


def test_child_profile_marks_carving_metrics_not_applicable() -> None:
    pack = _pack(
        F.parallel_skier(),
        profile=_Profile(birthday="2016-05-01", height_cm=130.0, weight_kg=30.0),
        clip_date=CLIP_DATE,
    )
    assert pack.athlete.age_band == "age-7-12"
    assert not carving_applicable(pack.athlete)
    for metric_id in ("edge_angle_proxy", "angulation", "banking_index"):
        item = pack.metrics[metric_id]
        assert item.state == "not_applicable", metric_id
        assert item.reason == "not_applicable_age_band:age-7-12", metric_id
        assert item.value is None, metric_id
    # Policy: a profile may not silently lower a standard, so everything else is
    # still measured.
    assert pack.metrics["stance_width"].state == "ok"
    assert pack.metrics["stem_count"].state == "ok"


def test_athlete_context_handles_missing_and_broken_profile_fields() -> None:
    assert build_athlete_context(None).height_m is None
    assert build_athlete_context(_Profile(birthday="")).age_band is None
    assert build_athlete_context(_Profile(birthday="nonsense")).age_years is None
    context = build_athlete_context(_Profile(height_cm=0.0))
    assert context.height_m is None
    assert context.leg_len_m is None
    assert context.bmi is None
    assert carving_applicable(context)  # unknown age never excludes a metric
    assert carving_applicable(None)
    assert build_athlete_context(AthleteContext(height_m=1.8)).height_m == 1.8
    # Both stored block shapes are accepted.
    assert build_athlete_context({"height_m": 1.7}).height_m == 1.7
    assert build_athlete_context({"height_cm": 170.0}).height_m == 1.7
    assert build_athlete_context(object()).height_m is None


# --- poles ------------------------------------------------------------------


def test_pole_touches_are_detected_and_timed() -> None:
    pack = _pack(F.poling_skier())
    rate = pack.metrics["pole_touch_rate"]
    timing = pack.metrics["pole_touch_timing"]
    assert rate.state == "ok" and rate.value is not None
    assert 0.5 <= rate.value <= 1.0
    assert timing.state == "ok"
    assert abs(timing.value) < 0.3
    assert timing.per_turn is not None and len(timing.per_turn) == pack.turn_count


def test_no_pole_touch_is_reported_as_zero_rate_and_unknown_timing() -> None:
    pack = _pack(F.parallel_skier())
    assert pack.value("pole_touch_rate") == 0.0
    assert pack.metrics["pole_touch_timing"].state == "unknown"
    assert pack.metrics["pole_touch_timing"].reason == "no_pole_touch_detected"


def test_hands_in_view_uses_the_fore_aft_axis() -> None:
    pack = _pack(F.parallel_skier())
    assert pack.value("hands_in_view") == 1.0
    behind = _pack(F.parallel_skier(hands_forward_px=-40.0))
    assert behind.value("hands_in_view") == 0.0


def test_hands_unknown_when_wrists_are_missing() -> None:
    pack = _pack(F.parallel_skier(drop_landmarks=(15, 16)))
    item = pack.metrics["hands_in_view"]
    assert item.state == "unknown"
    assert item.reason == "wrists_not_visible"


# --- view / scale estimates -------------------------------------------------


def test_view_estimate_fields_are_populated() -> None:
    pack = _pack(F.parallel_skier())
    view = pack.view
    assert view is not None
    assert view.shoulder_w_px > view.hip_w_px  # shoulders are wider
    assert view.torso_len_px is not None
    assert view.leg_len_px is not None and 180.0 < view.leg_len_px < 230.0
    assert 0.0 < view.aspect < 1.0
    assert 25.0 <= view.azimuth_deg <= 60.0
    assert view.view_class is ViewClass.QUARTER
    assert view.view_class == "quarter"  # str enum, so string compares still work
    assert view.reason is None
    assert view.lateral_ok and view.sagittal_ok


def test_body_scale_uses_segment_sums() -> None:
    pack = _pack(F.parallel_skier())
    scale = pack.scale
    assert scale is not None and scale.ok
    assert scale.shank_len_px is not None
    assert scale.leg_len_px > scale.shank_len_px
    assert scale.to_cm(0.25) is None  # no profile, so no centimetres
    with_profile = _pack(F.parallel_skier(), profile=_Profile(), clip_date=CLIP_DATE)
    assert with_profile.scale.to_cm(0.25) is not None


def test_camera_motion_can_be_overridden_by_the_scene() -> None:
    pack = _pack(
        F.parallel_skier(), scene=SceneContext(camera_motion=CameraMotion.FOLLOW)
    )
    assert pack.camera_motion == "follow"
    assert pack.metrics["camera_motion"].text == "follow"


def test_camera_motion_is_inferred_from_hip_travel() -> None:
    assert _pack(F.parallel_skier()).camera_motion == "static"
    assert _pack(F.parallel_skier(descent_px_s=0.0)).camera_motion == "follow"


# --- pack helpers -----------------------------------------------------------


def test_pack_accessors() -> None:
    pack = _pack(F.parallel_skier())
    assert pack["turn_count"].value == 10.0
    assert pack.get("nonsense") is None
    assert pack.value("nonsense") is None
    assert "turn_rate" in pack.ok_ids()
    assert pack.value("turn_rate") is not None
    profile_pack = _pack(F.profile_view_skier())
    assert "stance_width" not in profile_pack.ok_ids()
    assert profile_pack.value("stance_width") is None


def test_metric_summary_is_json_friendly() -> None:
    summary = metric_summary(_pack(F.parallel_skier()))
    assert len(summary) == len(metric_ids())
    for key, row in summary.items():
        assert set(row) == {
            "value",
            "text",
            "unit",
            "state",
            "reason",
            "reliability",
            "faulty_turns",
            "total_turns",
        }, key
        assert row["value"] is None or isinstance(row["value"], float)


def test_reliability_reflects_view_and_sample_count() -> None:
    quarter = _pack(F.parallel_skier())
    short = _pack(F.short_clip())
    assert quarter.metrics["stance_width"].reliability > 0.5
    assert (
        short.metrics["stance_width"].reliability
        < quarter.metrics["stance_width"].reliability
    )
    # A near-profile clip degrades the lateral view factor before suppressing.
    marginal = _pack(F.parallel_skier(azimuth_deg=28.0))
    assert marginal.metrics["stance_width"].state == "ok"
    assert (
        marginal.metrics["stance_width"].reliability
        < quarter.metrics["stance_width"].reliability
    )


def test_compute_metrics_segments_turns_when_none_are_supplied() -> None:
    clip = F.parallel_skier()
    supplied = compute_metrics(clip, segment_turns(clip.frames, FPS))
    inferred = compute_metrics(clip)
    assert supplied.turn_count == inferred.turn_count == 10
    assert abs(supplied.value("turn_rate") - inferred.value("turn_rate")) < 1e-9


def _translated(clip, dx: float, dy: float):
    """The same clip with every landmark shifted by a constant pixel offset."""
    for frame in clip.frames:
        for joint in frame.blaze33 or ():
            if joint.confidence <= 0.0:
                continue
            joint.x += dx
            joint.y += dy
    return clip


def test_ratio_metrics_are_invariant_under_a_constant_translation() -> None:
    """Comparing two identical calls passes for any pure function, so it tested
    nothing. A ratio is normalized on a body length, so sliding the whole
    skeleton across the frame — a pan, a crop, a different framing — must not
    move it. Position-dependent metrics are excluded on purpose: the view and
    camera-motion estimates read absolute pixels by design.
    """
    base = _pack(F.parallel_skier())
    shifted = _pack(_translated(F.parallel_skier(), dx=137.0, dy=-58.0))
    ratios = [
        "stance_width",
        "stance_width_var",
        "wedge_angle",
        "hip_over_foot",
        "knee_valgus",
        "turn_shape_index",
    ]
    for metric_id in ratios:
        want = base.metrics[metric_id]
        got = shifted.metrics[metric_id]
        assert got.state == want.state, metric_id
        if want.value is None:
            assert got.value is None, metric_id
            continue
        assert abs(got.value - want.value) < 1e-6, metric_id


def test_com_vertical_travel_tracks_the_bob_amplitude() -> None:
    flat = _pack(F.parallel_skier(bob_px=0.0))
    deep = _pack(F.parallel_skier(bob_px=25.0))
    assert flat.value("com_vertical_travel") < deep.value("com_vertical_travel")
    # Detrended, so the constant descent of a static camera is not counted.
    assert flat.value("com_vertical_travel") < 0.02
    assert np.isfinite(deep.value("com_vertical_travel"))
