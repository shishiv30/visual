import pytest

from core.mediapipe_engine import DEFAULT_TASK, MediaPipeEngine
from schemas.core_inference import BackendId


@pytest.mark.skipif(not DEFAULT_TASK.is_file(), reason="pose_landmarker_full.task missing")
def test_mediapipe_engine_synthetic_image() -> None:
    mediapipe = pytest.importorskip("mediapipe")
    import numpy as np

    engine = MediaPipeEngine()
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    result = engine.infer(image)
    assert result.model_meta.backend_id == BackendId.MEDIAPIPE_POSE.value
    assert result.frame.width == 256
    assert result.frame.height == 256
    _ = mediapipe
