from __future__ import annotations

from core.sports.posture import posture_scores
from core.sports.signals import FeaturePack, FrameSample
from schemas.stage_report import KeypointResult, KeypointStatus


def _pack(**overrides) -> FeaturePack:
    base = dict(
        n=20,
        fps=30.0,
        stance_width=1.0,
        stance_width_std=0.1,
        knee_flex_mean=40.0,
        knee_flex_amp=30.0,
        knee_flex_freq=0.5,
        upper_quiet=0.4,
        inward_lean=0.2,
        turn_freq=0.4,
        fall_line=1.0,
        backseat=0.1,
        knee_valgus=0.15,
        hip_ir_proxy=0.1,
        hands_low=0.9,
        gaze_ok=0.9,
        foot_ok=True,
        quality=0.9,
        series=[FrameSample(t_ms=0.0)],
        hip_x_mean=200.0,
    )
    base.update(overrides)
    return FeaturePack(**base)


def test_posture_scores_in_range() -> None:
    scores = posture_scores(_pack())
    for value in (
        scores.stability,
        scores.coordination,
        scores.control,
        scores.balance,
    ):
        assert 0.0 <= value <= 100.0


def test_posture_uses_keypoint_control_when_present() -> None:
    weak = posture_scores(
        _pack(inward_lean=0.2),
        [
            KeypointResult(
                id="a",
                status=KeypointStatus.FAIL,
                score=20.0,
                good="g",
                bad="b",
                drills=[],
            )
        ],
    )
    strong = posture_scores(
        _pack(inward_lean=0.2),
        [
            KeypointResult(
                id="a",
                status=KeypointStatus.PASS,
                score=90.0,
                good="g",
                bad="b",
                drills=[],
            )
        ],
    )
    assert strong.control > weak.control
