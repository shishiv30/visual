import numpy as np

from clients.windows.pipeline.normalize import MAX_HEIGHT, _scale_bgr


def test_scale_bgr_caps_height_720() -> None:
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = _scale_bgr(frame)
    h, w = out.shape[:2]
    assert h == MAX_HEIGHT or h == MAX_HEIGHT - 1
    assert abs(w / h - 1920 / 1080) < 0.02
    assert h <= 720


def test_scale_bgr_leaves_short_video() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = _scale_bgr(frame)
    assert out.shape[0] == 480
    assert out.shape[1] == 640
