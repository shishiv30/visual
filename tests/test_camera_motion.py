"""Tests for camera motion compensation (P1c)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from core.sports.camera_motion import CameraMotionClass, estimate_camera_motion

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "camera_motion" / "static_camera.json"


def test_static_fixture_metadata() -> None:
    meta = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert meta["motion_class"] == "static"


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("cv2") is None,
    reason="opencv not installed",
)
def test_estimate_camera_motion_identity_frames() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frames = [frame.copy() for _ in range(5)]
    hips = [(80.0, 60.0 + i * 20.0) for i in range(5)]
    result = estimate_camera_motion(frames, hips, leg_len_px=40.0, stride=1)
    assert result.motion_class in (
        CameraMotionClass.STATIC,
        CameraMotionClass.PANNING,
    )
    assert result.mean_flow_quality >= 0.0
