"""Geometric veto and temporal smoothing for pole/jitter cases."""

from __future__ import annotations

from core.pose_filter import (
    crop_box_for_retry,
    crop_disagrees_with_prev,
    ema_smooth,
    is_plausible,
    pick_primary,
    reject_implausible,
)
from schemas.core_inference import (
    BackendId,
    COCO17_NAMES,
    CoreInferenceResult,
    Detection,
    ErrorCode,
    FrameMeta,
    Keypoint,
    ModelMeta,
    Pose,
    SkeletonKind,
    SourceKind,
)


def _result(
    *,
    width: int,
    height: int,
    bbox: tuple[float, float, float, float],
    keypoints: list[tuple[str, float, float, float]],
    score: float = 0.8,
    extra_poses: list[Pose] | None = None,
    extra_dets: list[Detection] | None = None,
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
    poses = [pose] + (extra_poses or [])
    dets = [det] + (extra_dets or [])
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.IMAGE,
            timestamp_ms=0.0,
            width=width,
            height=height,
        ),
        detections=dets,
        poses=poses,
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


def _skier() -> CoreInferenceResult:
    return _result(
        width=640,
        height=480,
        bbox=(280.0, 200.0, 400.0, 430.0),
        keypoints=[
            ("nose", 340.0, 220.0, 0.9),
            ("left_eye", 348.0, 216.0, 0.8),
            ("right_eye", 332.0, 216.0, 0.8),
            ("left_shoulder", 370.0, 260.0, 0.9),
            ("right_shoulder", 310.0, 260.0, 0.9),
            ("left_hip", 365.0, 340.0, 0.85),
            ("right_hip", 315.0, 340.0, 0.85),
            ("left_ankle", 380.0, 420.0, 0.8),
            ("right_ankle", 300.0, 420.0, 0.8),
        ],
    )


def _pole_fused() -> CoreInferenceResult:
    return _result(
        width=640,
        height=480,
        bbox=(300.0, 10.0, 360.0, 460.0),
        keypoints=[
            ("nose", 330.0, 20.0, 0.4),
            ("left_eye", 332.0, 18.0, 0.3),
            ("right_eye", 328.0, 18.0, 0.3),
            ("left_shoulder", 350.0, 80.0, 0.4),
            ("right_shoulder", 310.0, 80.0, 0.4),
            ("left_hip", 348.0, 280.0, 0.7),
            ("right_hip", 312.0, 280.0, 0.7),
            ("left_ankle", 352.0, 450.0, 0.8),
            ("right_ankle", 308.0, 450.0, 0.8),
        ],
    )


def test_plausible_skier_passes() -> None:
    assert is_plausible(_skier())


def test_pole_plus_person_is_rejected() -> None:
    fused = _pole_fused()
    bbox = fused.detections[0].bbox_xyxy
    assert not is_plausible(fused)
    rejected = reject_implausible(fused)
    assert rejected.error is not None
    assert rejected.error.code == ErrorCode.LOW_CONFIDENCE
    assert rejected.poses == []
    _x1, y1, _x2, y2 = crop_box_for_retry(bbox, 640, 480)
    assert y1 > 100
    assert (y2 - y1) < 450


def test_pick_primary_prefers_iou_with_previous() -> None:
    skier = _skier()
    pole = Pose(
        skeleton=SkeletonKind.COCO_17,
        keypoints=skier.poses[0].keypoints,
        score=0.99,
        detection_index=1,
    )
    pole_det = Detection(
        class_name="person",
        confidence=0.99,
        bbox_xyxy=(10.0, 0.0, 40.0, 480.0),
    )
    skier.poses.append(pole)
    skier.detections.append(pole_det)
    picked = pick_primary(skier, (270.0, 190.0, 410.0, 440.0))
    assert len(picked.poses) == 1
    x1 = picked.detections[0].bbox_xyxy[0]
    assert x1 > 100


def test_ema_damps_jump() -> None:
    a = _skier()
    b = _skier()
    nose = next(k for k in b.poses[0].keypoints if k.name == "nose")
    nose.x = 500.0
    smooth = ema_smooth(a, b)
    out = next(k for k in smooth.poses[0].keypoints if k.name == "nose")
    assert out.x < 450.0
    assert out.x > 340.0


def test_crop_disagrees_when_torso_collapses() -> None:
    prev = _skier()
    curr = _result(
        width=640,
        height=480,
        bbox=(300.0, 200.0, 380.0, 310.0),
        keypoints=[
            ("nose", 340.0, 220.0, 0.9),
            ("left_eye", 348.0, 216.0, 0.8),
            ("right_eye", 332.0, 216.0, 0.8),
            ("left_shoulder", 360.0, 250.0, 0.9),
            ("right_shoulder", 320.0, 250.0, 0.9),
            ("left_hip", 355.0, 270.0, 0.85),
            ("right_hip", 325.0, 270.0, 0.85),
            ("left_ankle", 358.0, 300.0, 0.8),
            ("right_ankle", 322.0, 300.0, 0.8),
        ],
    )
    assert crop_disagrees_with_prev(prev, curr)
    assert not crop_disagrees_with_prev(prev, _skier())
