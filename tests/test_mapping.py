import numpy as np

from core.mapping import map_pose_arrays
from schemas.core_inference import (
    COCO17_NAMES,
    ErrorCode,
    FrameMeta,
    ModelMeta,
    SkeletonKind,
    SourceKind,
)


def _frame() -> FrameMeta:
    return FrameMeta(
        source_kind=SourceKind.IMAGE,
        timestamp_ms=0.0,
        width=640,
        height=480,
    )


def _meta() -> ModelMeta:
    return ModelMeta(
        backend_id="yolo11n-pose",
        model_name="yolo11n-pose.pt",
        latency_ms=1.0,
        device="cpu",
    )


def test_maps_person_box_and_coco17_pose() -> None:
    boxes_xyxy = np.array([[10.0, 20.0, 110.0, 220.0]], dtype=np.float32)
    boxes_conf = np.array([0.9], dtype=np.float32)
    boxes_cls = np.array([0], dtype=np.float32)
    kpts_xy = np.zeros((1, 17, 2), dtype=np.float32)
    kpts_xy[0, 0] = [50.0, 40.0]
    kpts_conf = np.ones((1, 17), dtype=np.float32) * 0.8
    result = map_pose_arrays(
        frame=_frame(),
        model_meta=_meta(),
        boxes_xyxy=boxes_xyxy,
        boxes_conf=boxes_conf,
        boxes_cls=boxes_cls,
        class_names={0: "person"},
        kpts_xy=kpts_xy,
        kpts_conf=kpts_conf,
        conf_threshold=0.25,
    )
    assert result.error is None
    assert len(result.detections) == 1
    assert result.detections[0].class_name == "person"
    assert result.detections[0].bbox_xyxy == (10.0, 20.0, 110.0, 220.0)
    assert len(result.poses) == 1
    assert result.poses[0].skeleton == SkeletonKind.COCO_17
    assert [kp.name for kp in result.poses[0].keypoints] == list(COCO17_NAMES)
    assert result.poses[0].keypoints[0].x == 50.0
    assert result.tracks == []
    assert result.segments == []


def test_no_person_when_empty() -> None:
    result = map_pose_arrays(
        frame=_frame(),
        model_meta=_meta(),
        boxes_xyxy=np.zeros((0, 4), dtype=np.float32),
        boxes_conf=np.zeros((0,), dtype=np.float32),
        boxes_cls=np.zeros((0,), dtype=np.float32),
        class_names={0: "person"},
        kpts_xy=None,
        kpts_conf=None,
        conf_threshold=0.25,
    )
    assert result.error is not None
    assert result.error.code == ErrorCode.NO_PERSON
    assert result.detections == []


def test_low_confidence_filtered() -> None:
    result = map_pose_arrays(
        frame=_frame(),
        model_meta=_meta(),
        boxes_xyxy=np.array([[1.0, 1.0, 2.0, 2.0]], dtype=np.float32),
        boxes_conf=np.array([0.1], dtype=np.float32),
        boxes_cls=np.array([0], dtype=np.float32),
        class_names={0: "person"},
        kpts_xy=None,
        kpts_conf=None,
        conf_threshold=0.25,
    )
    assert result.error is not None
    assert result.error.code == ErrorCode.LOW_CONFIDENCE
