"""Low-score frame fill from neighboring high-score poses."""

from __future__ import annotations

import pytest

from core.pose_track import (
    fill_low_score_poses,
    frame_score,
    stabilize_pose_sequence,
)
from schemas.clip_analysis import AnalyzedFrame
from schemas.core_inference import (
    BackendId,
    COCO17_NAMES,
    CoreInferenceResult,
    Detection,
    ErrorCode,
    FrameMeta,
    InferenceError,
    Keypoint,
    ModelMeta,
    Pose,
    SkeletonKind,
    SourceKind,
)


def _result(
    *,
    timestamp_ms: float,
    bbox: tuple[float, float, float, float],
    keypoints: list[tuple[str, float, float, float]],
    score: float = 0.8,
) -> CoreInferenceResult:
    kps = [
        Keypoint(name=name, x=x, y=y, z=0.0, confidence=vis)
        for name, x, y, vis in keypoints
    ]
    named = {k.name for k in kps}
    for name in COCO17_NAMES:
        if name not in named:
            kps.append(Keypoint(name=name, x=bbox[0], y=bbox[1], z=0.0, confidence=0.5))
    pose = Pose(
        skeleton=SkeletonKind.COCO_17,
        keypoints=kps,
        score=score,
        detection_index=0,
    )
    det = Detection(class_name="person", confidence=score, bbox_xyxy=bbox)
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=timestamp_ms,
            width=640,
            height=480,
        ),
        detections=[det],
        poses=[pose],
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


def _skier(timestamp_ms: float, nose_x: float) -> CoreInferenceResult:
    return _result(
        timestamp_ms=timestamp_ms,
        bbox=(nose_x - 60.0, 200.0, nose_x + 60.0, 430.0),
        keypoints=[
            ("nose", nose_x, 220.0, 0.9),
            ("left_eye", nose_x + 8.0, 216.0, 0.8),
            ("right_eye", nose_x - 8.0, 216.0, 0.8),
            ("left_shoulder", nose_x + 30.0, 260.0, 0.9),
            ("right_shoulder", nose_x - 30.0, 260.0, 0.9),
            ("left_hip", nose_x + 25.0, 340.0, 0.85),
            ("right_hip", nose_x - 25.0, 340.0, 0.85),
            ("left_ankle", nose_x + 40.0, 420.0, 0.8),
            ("right_ankle", nose_x - 40.0, 420.0, 0.8),
        ],
    )


def _empty(timestamp_ms: float) -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=timestamp_ms,
            width=640,
            height=480,
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
        error=InferenceError(code=ErrorCode.NO_PERSON, message="no person"),
    )


def _frame(result: CoreInferenceResult) -> AnalyzedFrame:
    return AnalyzedFrame(t_ms=result.frame.timestamp_ms, result=result)


def _nose_x(result: CoreInferenceResult) -> float:
    return next(k.x for k in result.poses[0].keypoints if k.name == "nose")


def test_frame_score_empty_is_zero() -> None:
    assert frame_score(_empty(0.0)) == 0.0


def test_frame_score_skier_is_high() -> None:
    assert frame_score(_skier(0.0, 340.0)) >= 55.0


def test_high_empty_high_midpoint() -> None:
    frames = [
        _frame(_skier(0.0, 300.0)),
        _frame(_empty(66.0)),
        _frame(_skier(133.0, 400.0)),
    ]
    fill_low_score_poses(frames)
    mid = frames[1].result
    assert mid.error is None
    assert mid.poses
    assert _nose_x(mid) == pytest.approx(350.0, abs=2.0)


def test_gap_over_400ms_not_filled() -> None:
    frames = [
        _frame(_skier(0.0, 300.0)),
        _frame(_empty(250.0)),
        _frame(_skier(500.0, 400.0)),
    ]
    fill_low_score_poses(frames)
    assert frames[1].result.poses == []
    assert frames[1].result.error is not None


def test_all_zero_unchanged() -> None:
    frames = [_frame(_empty(0.0)), _frame(_empty(33.0)), _frame(_empty(66.0))]
    fill_low_score_poses(frames)
    assert all(not item.result.poses for item in frames)


def test_trailing_hold_within_200ms() -> None:
    frames = [_frame(_skier(0.0, 300.0)), _frame(_empty(100.0))]
    fill_low_score_poses(frames)
    assert frames[1].result.poses
    assert _nose_x(frames[1].result) == pytest.approx(300.0)


def _collapsed(timestamp_ms: float, nose_x: float) -> CoreInferenceResult:
    return _result(
        timestamp_ms=timestamp_ms,
        bbox=(nose_x - 40.0, 200.0, nose_x + 40.0, 320.0),
        keypoints=[
            ("nose", nose_x, 220.0, 0.9),
            ("left_eye", nose_x + 8.0, 216.0, 0.8),
            ("right_eye", nose_x - 8.0, 216.0, 0.8),
            ("left_shoulder", nose_x + 20.0, 250.0, 0.9),
            ("right_shoulder", nose_x - 20.0, 250.0, 0.9),
            ("left_hip", nose_x + 12.0, 275.0, 0.85),
            ("right_hip", nose_x - 12.0, 275.0, 0.85),
            ("left_ankle", nose_x + 16.0, 310.0, 0.8),
            ("right_ankle", nose_x - 16.0, 310.0, 0.8),
        ],
        score=0.9,
    )


def _hip_y(result: CoreInferenceResult) -> float:
    left = next(k.y for k in result.poses[0].keypoints if k.name == "left_hip")
    right = next(k.y for k in result.poses[0].keypoints if k.name == "right_hip")
    return (left + right) / 2.0


def test_stabilize_collapses_mid_spike() -> None:
    frames = [
        _frame(_skier(0.0, 340.0)),
        _frame(_collapsed(66.0, 340.0)),
        _frame(_skier(133.0, 340.0)),
    ]
    stabilize_pose_sequence(frames)
    assert _hip_y(frames[1].result) == pytest.approx(340.0, abs=8.0)
    assert _nose_x(frames[1].result) == pytest.approx(340.0, abs=2.0)


def test_stabilize_keeps_real_translation() -> None:
    frames = [
        _frame(_skier(0.0, 300.0)),
        _frame(_skier(66.0, 450.0)),
        _frame(_skier(133.0, 600.0)),
    ]
    stabilize_pose_sequence(frames)
    assert _nose_x(frames[1].result) == pytest.approx(450.0, abs=1.0)
