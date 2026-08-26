from schemas.clip_analysis import AnalyzedFrame, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)
from clients.windows.pipeline.export_overlay import format_frame_hud, nearest_frame


def _empty(t_ms: float) -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=t_ms,
            width=64,
            height=64,
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
        error=None,
    )


def test_format_frame_hud() -> None:
    assert format_frame_hud(12000, 65000, 123, 61, 180) == "0:12 / 1:05  f123  p61/180"
    assert (
        format_frame_hud(12000, 65000, 123, 61, 180, short_id="a1b2c3d4")
        == "a1b2c3d4  0:12 / 1:05  f123  p61/180"
    )
    assert format_frame_hud(0, 0, 0, None, 0) == "-- / --  f0"


def test_nearest_frame_index() -> None:
    analysis = ClipAnalysis(
        clip_id="c",
        fps=30.0,
        frame_count=3,
        frames=[
            AnalyzedFrame(t_ms=0.0, result=_empty(0.0)),
            AnalyzedFrame(t_ms=66.0, result=_empty(66.0)),
            AnalyzedFrame(t_ms=133.0, result=_empty(133.0)),
        ],
    )
    _frame, index = nearest_frame(analysis, 70.0)
    assert index == 1
    assert nearest_frame(None, 0.0) == (None, None)
