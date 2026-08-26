import numpy as np
import pytest

from core.engine import CoreEngine
from core.mapping import invalid_input
from schemas.core_inference import (
    ErrorCode,
    FrameMeta,
    ModelMeta,
    SourceKind,
)

torch = pytest.importorskip("torch")


def test_invalid_image_without_loading_weights() -> None:
    meta = ModelMeta(
        backend_id="yolo11n-pose",
        model_name="yolo11n-pose.pt",
        latency_ms=0.0,
        device="cpu",
    )
    frame = FrameMeta(
        source_kind=SourceKind.IMAGE,
        timestamp_ms=0.0,
        width=1,
        height=1,
    )
    result = invalid_input("expected a non-empty HxWxC BGR image", meta, frame)
    assert result.error is not None
    assert result.error.code == ErrorCode.INVALID_INPUT


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required for live Core smoke")
def test_cuda_pose_on_synthetic_person_like_image() -> None:
    engine = CoreEngine(conf_threshold=0.01)
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    image[:] = (30, 30, 30)
    result = engine.infer(image, source_kind=SourceKind.IMAGE)
    assert result.schema_version == "0.1.0"
    assert result.frame.width == 640
    assert result.frame.height == 480
    assert result.model_meta.latency_ms >= 0.0
    if result.error is not None:
        assert result.error.code in {ErrorCode.NO_PERSON, ErrorCode.LOW_CONFIDENCE}
    else:
        assert result.detections
        assert all(len(pose.keypoints) == 17 for pose in result.poses)
