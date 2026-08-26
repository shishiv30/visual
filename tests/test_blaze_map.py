import numpy as np
import pytest

from core.blaze_map import _dll_path, map_blaze33, map_blaze33_native
from schemas.core_inference import COCO17_NAMES, BackendId, ErrorCode, SkeletonKind


def _person(width: int = 100, height: int = 200) -> np.ndarray:
    xyz = np.zeros((1, 33, 4), dtype=np.float32)
    xyz[..., 3] = 0.9
    for i in range(33):
        xyz[0, i, 0] = 10.0 + i
        xyz[0, i, 1] = 20.0 + i
        xyz[0, i, 2] = 0.01 * i
    return xyz


def test_blaze_maps_coco17_and_bbox() -> None:
    xyz = _person()
    result = map_blaze33(
        xyz, num_people=1, width=640, height=480, latency_ms=3.5, device="cpu"
    )
    assert result.error is None
    assert result.model_meta.backend_id == BackendId.MEDIAPIPE_POSE.value
    assert len(result.detections) == 1
    assert result.detections[0].class_name == "person"
    assert len(result.poses) == 1
    assert result.poses[0].skeleton == SkeletonKind.COCO_17
    names = [kp.name for kp in result.poses[0].keypoints]
    assert names == list(COCO17_NAMES)
    assert result.poses[0].keypoints[0].name == "nose"
    assert result.poses[0].keypoints[0].x == pytest.approx(10.0)
    assert result.tracks == []


def test_blaze_no_person() -> None:
    result = map_blaze33(
        None, num_people=0, width=64, height=64, latency_ms=0.0, device="cpu"
    )
    assert result.error is not None
    assert result.error.code == ErrorCode.NO_PERSON


def test_blaze_low_confidence() -> None:
    xyz = _person()
    xyz[..., 3] = 0.05
    result = map_blaze33(
        xyz, num_people=1, width=64, height=64, latency_ms=0.0, device="cpu"
    )
    assert result.error is not None
    assert result.error.code == ErrorCode.LOW_CONFIDENCE


def test_blaze_invalid_size() -> None:
    result = map_blaze33(
        None, num_people=0, width=0, height=10, latency_ms=0.0, device="cpu"
    )
    assert result.error is not None
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_native_matches_python() -> None:
    if _dll_path() is None:
        pytest.skip("core_map DLL not built")
    xyz = _person()
    py = map_blaze33(
        xyz, num_people=1, width=640, height=480, latency_ms=1.25, device="cpu"
    )
    native = map_blaze33_native(
        xyz, num_people=1, width=640, height=480, latency_ms=1.25, device="cpu"
    )
    assert native.error is None
    assert native.model_meta.backend_id == py.model_meta.backend_id
    assert native.detections[0].class_name == "person"
    assert len(native.poses[0].keypoints) == 17
    assert native.poses[0].keypoints[5].name == "left_shoulder"
    np.testing.assert_allclose(
        native.poses[0].keypoints[5].x, py.poses[0].keypoints[5].x, rtol=1e-5
    )
