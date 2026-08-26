"""HSV CamShift ROI helpers."""

from __future__ import annotations

import numpy as np
import pytest

from core.person_roi import build_hist, crop_for_pose, remap_from_crop, search
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    Detection,
    FrameMeta,
    Keypoint,
    ModelMeta,
    Pose,
    SkeletonKind,
    SourceKind,
)


def _red_jacket(shift_x: int = 0) -> np.ndarray:
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    x1, y1, x2, y2 = 80 + shift_x, 60, 140 + shift_x, 160
    image[y1:y2, x1:x2] = (0, 0, 220)
    return image


def test_hist_peaks_on_red_block() -> None:
    image = _red_jacket()
    box = (80.0, 60.0, 140.0, 160.0)
    hist = build_hist(image, box)
    found = search(image, hist, box)
    cx = 0.5 * (found[0] + found[2])
    cy = 0.5 * (found[1] + found[3])
    assert 70 < cx < 150
    assert 50 < cy < 170


def test_camshift_follows_shifted_block() -> None:
    hist = build_hist(_red_jacket(0), (80.0, 60.0, 140.0, 160.0))
    moved = _red_jacket(40)
    found = search(moved, hist, (80.0, 60.0, 140.0, 160.0))
    cx = 0.5 * (found[0] + found[2])
    assert cx > 100


def test_crop_for_pose_remaps_keypoints() -> None:
    image = _red_jacket()
    crop, ox, oy, scale = crop_for_pose(image, (80.0, 60.0, 140.0, 160.0), min_side=32)
    result = CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.IMAGE,
            timestamp_ms=0.0,
            width=crop.shape[1],
            height=crop.shape[0],
        ),
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(10.0, 10.0, 20.0, 20.0),
            )
        ],
        poses=[
            Pose(
                skeleton=SkeletonKind.COCO_17,
                keypoints=[
                    Keypoint(name="nose", x=12.0, y=14.0, z=0.0, confidence=0.9)
                ],
                score=0.9,
                detection_index=0,
            )
        ],
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
    mapped = remap_from_crop(result, ox, oy, scale, 320, 240)
    nose = mapped.poses[0].keypoints[0]
    assert mapped.frame.width == 320
    assert nose.x == pytest.approx(12.0 / scale + ox, abs=0.5)
    assert nose.y == pytest.approx(14.0 / scale + oy, abs=0.5)
