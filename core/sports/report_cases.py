"""Synthetic clip parameter sets for report layout review."""

from __future__ import annotations

from dataclasses import dataclass

from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)


@dataclass(frozen=True)
class ReportCase:
    case_id: str
    clip_id: str
    expect_stages: tuple[str, ...]
    expect_ready: bool | None
    note: str
    frames: int
    stance: float
    knee_drop: float
    lean: float = 0.0
    hip_swing: float = 0.0
    knee_in_alt: tuple[float, float] | None = None
    drop_feet: bool = False
    min_frames: int | None = None


CASES: tuple[ReportCase, ...] = (
    ReportCase(
        case_id="wedge_glide_pass",
        clip_id="case-glide",
        expect_stages=("pizza_glide",),
        expect_ready=True,
        note="wide stance, little yaw → 犁式直滑过关",
        frames=8,
        stance=1.8,
        knee_drop=50.0,
    ),
    ReportCase(
        case_id="wedge_turns",
        clip_id="case-pizza",
        expect_stages=("pizza",),
        expect_ready=None,
        note="wide stance with path oscillation → 犁式转弯",
        frames=12,
        stance=1.8,
        knee_drop=50.0,
        hip_swing=8.0,
    ),
    ReportCase(
        case_id="parallel_pass_fork",
        clip_id="case-parallel",
        expect_stages=("parallel",),
        expect_ready=True,
        note="hip-width stance → 平行过关，分叉搓雪/卡宾",
        frames=8,
        stance=0.8,
        knee_drop=45.0,
    ),
    ReportCase(
        case_id="skid_fail_hockey",
        clip_id="case-skid",
        expect_stages=("skid_short",),
        expect_ready=False,
        note="parallel + high turn freq, low knee amp → 搓雪未过关",
        frames=16,
        stance=0.9,
        knee_drop=45.0,
        hip_swing=18.0,
    ),
    ReportCase(
        case_id="carve_inclination",
        clip_id="case-carve",
        expect_stages=("carve_long", "carve_medium", "carve_short"),
        expect_ready=None,
        note="parallel + inward lean → 卡宾大弯启发式",
        frames=12,
        stance=0.85,
        knee_drop=48.0,
        lean=0.35,
        hip_swing=2.0,
    ),
    ReportCase(
        case_id="mogul_absorb",
        clip_id="case-mogul",
        expect_stages=("mogul_absorb", "mogul_fallline"),
        expect_ready=None,
        note="knee-in oscillation → 蘑菇吸收",
        frames=16,
        stance=0.85,
        knee_drop=40.0,
        knee_in_alt=(55.0, 8.0),
    ),
    ReportCase(
        case_id="unknown_refilm",
        clip_id="case-unknown",
        expect_stages=("unknown",),
        expect_ready=False,
        note="too few frames → 请重拍",
        frames=2,
        stance=1.0,
        knee_drop=40.0,
        min_frames=2,
    ),
)


def _empty_core() -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=0.0,
            width=640,
            height=360,
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


def joints(
    *,
    hip_w: float = 40.0,
    stance: float = 1.5,
    knee_drop: float = 40.0,
    knee_in: float = 0.0,
    lean: float = 0.0,
    hip_x: float = 200.0,
    drop_feet: bool = False,
) -> list[BlazeJoint]:
    mid = hip_x
    lh, rh = mid - hip_w / 2, mid + hip_w / 2
    ankle_span = hip_w * stance
    la, ra = mid - ankle_span / 2, mid + ankle_span / 2
    ls, rs = lh + lean * hip_w, rh + lean * hip_w
    pts = [(0.0, 0.0)] * 33
    pts[0] = (mid, 40.0)
    pts[11] = (ls, 80.0)
    pts[12] = (rs, 80.0)
    pts[15] = (ls, 140.0)
    pts[16] = (rs, 140.0)
    pts[23] = (lh, 160.0)
    pts[24] = (rh, 160.0)
    pts[25] = (lh + knee_in, 160.0 + knee_drop)
    pts[26] = (rh - knee_in, 160.0 + knee_drop)
    pts[27] = (la, 280.0)
    pts[28] = (ra, 280.0)
    pts[31] = (la, 300.0)
    pts[32] = (ra, 300.0)
    out: list[BlazeJoint] = []
    for i in range(33):
        x, y = pts[i]
        conf = 0.0 if drop_feet and i in (27, 28, 31, 32) else 0.95
        out.append(BlazeJoint(x=x, y=y, z=0.0, confidence=conf))
    return out


def clip_for(case: ReportCase) -> ClipAnalysis:
    n = case.min_frames if case.min_frames is not None else case.frames
    seq: list[list[BlazeJoint]] = []
    for i in range(n):
        knee_in = 0.0
        if case.knee_in_alt is not None:
            knee_in = case.knee_in_alt[0] if i % 2 == 0 else case.knee_in_alt[1]
        hip_x = 180.0 + (i % 6) * case.hip_swing if case.hip_swing else 200.0
        seq.append(
            joints(
                stance=case.stance,
                knee_drop=case.knee_drop,
                knee_in=knee_in,
                lean=case.lean,
                hip_x=hip_x,
                drop_feet=case.drop_feet,
            )
        )
    frames = [
        AnalyzedFrame(t_ms=i * 66.0, result=_empty_core(), blaze33=body)
        for i, body in enumerate(seq)
    ]
    return ClipAnalysis(
        clip_id=case.clip_id,
        fps=15.0,
        frame_count=len(frames),
        frames=frames,
    )
