"""Tests for compensated steering integration (P3)."""

from __future__ import annotations

import numpy as np

from core.sports.metrics import REASON_CAMERA_FOLLOW_UNRELIABLE, MetricPack, MetricValue, _Builder
from core.sports.metrics import BY_ID


def test_camera_follow_blocks_turn_rate() -> None:
    builder = _Builder(
        view=type("V", (), {"azimuth_deg": 40.0})(),
        athlete=type("A", (), {"age_band": "age-18-39"})(),
        landmark_quality=0.8,
        turns=[type("T", (), {"duration_s": 1.0})()],
        forward_source="path",
        camera_motion="follow",
        steering_compensated=False,
    )
    blocked = builder.camera_follow_blocks(BY_ID["turn_rate"])
    assert blocked is not None
    assert blocked.reason == REASON_CAMERA_FOLLOW_UNRELIABLE


def test_compensated_steering_unblocks_turn_rate() -> None:
    builder = _Builder(
        view=type("V", (), {"azimuth_deg": 40.0})(),
        athlete=type("A", (), {"age_band": "age-18-39"})(),
        landmark_quality=0.8,
        turns=[type("T", (), {"duration_s": 1.0})()],
        forward_source="path",
        camera_motion="follow",
        steering_compensated=True,
    )
    assert builder.camera_follow_blocks(BY_ID["turn_rate"]) is None
