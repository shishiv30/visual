from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    Keypoint,
    ModelMeta,
    Pose,
    SkeletonKind,
    SourceKind,
)
from clients.windows.pipeline.frame_locator import build_locator_payload, short_clip_id


def test_short_clip_id() -> None:
    assert short_clip_id("A1B2C3D4-ffff-0000-1111-222233334444") == "a1b2c3d4"


def test_build_locator_payload_includes_blaze_and_frame() -> None:
    pose = Pose(
        skeleton=SkeletonKind.COCO_17,
        keypoints=[
            Keypoint(name="nose", x=0.1, y=0.2, z=0.0, confidence=0.9),
        ],
        score=0.8,
    )
    result = CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=1234.0,
            width=64,
            height=64,
        ),
        detections=[],
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
    analyzed = AnalyzedFrame(
        t_ms=1234.0,
        result=result,
        blaze33=[BlazeJoint(x=0.4, y=0.5, z=-0.1, confidence=0.95)],
    )
    analysis = ClipAnalysis(
        clip_id="a1b2c3d4-ffff-0000-1111-222233334444",
        fps=30.0,
        frame_count=1,
        frames=[analyzed],
    )
    payload = build_locator_payload(
        clip_id=analysis.clip_id,
        display_name="clip",
        video_frame=86,
        t_ms=1234.0,
        fps=30.0,
        analysis=analysis,
        analyzed=analyzed,
        pose_index=43,
        stage_id="carve_short",
        feedback=None,
    )
    assert payload["video_frame"] == 86
    assert payload["short_id"] == "a1b2c3d4"
    assert payload["blaze33"] == [
        {"x": 0.4, "y": 0.5, "z": -0.1, "confidence": 0.95}
    ]
    assert payload["coco17"][0]["name"] == "nose"
    empty = build_locator_payload(
        clip_id=analysis.clip_id,
        display_name="clip",
        video_frame=86,
        t_ms=1234.0,
        fps=30.0,
        analysis=None,
        analyzed=None,
        pose_index=None,
        stage_id="",
        feedback=None,
    )
    assert empty["blaze33"] is None
    assert empty["coco17"] is None
    assert empty["video_frame"] == 86
