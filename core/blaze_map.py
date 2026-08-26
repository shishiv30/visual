"""BlazePose 33 → CoreInferenceResult (Python twin of native/core_map)."""

from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np

from schemas.core_inference import (
    COCO17_NAMES,
    BackendId,
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

BLAZE_TO_COCO: tuple[int, ...] = (0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)
VIS_BBOX = 0.1
VIS_PERSON = 0.25
MODEL_NAME = "pose_landmarker_full.task"


def _empty_error(
    *,
    width: int,
    height: int,
    latency_ms: float,
    device: str,
    code: ErrorCode,
    message: str,
) -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.IMAGE,
            timestamp_ms=0.0,
            width=max(width, 1),
            height=max(height, 1),
        ),
        detections=[],
        poses=[],
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name=MODEL_NAME,
            latency_ms=latency_ms,
            device=device or "cpu",
        ),
        error=InferenceError(code=code, message=message),
    )


def map_blaze33(
    xyz_vis: np.ndarray | None,
    *,
    num_people: int,
    width: int,
    height: int,
    latency_ms: float,
    device: str,
) -> CoreInferenceResult:
    if width < 1 or height < 1 or num_people < 0:
        return _empty_error(
            width=width,
            height=height,
            latency_ms=latency_ms,
            device=device,
            code=ErrorCode.INVALID_INPUT,
            message="expected width,height >= 1 and a blaze33 buffer",
        )
    if num_people > 0 and xyz_vis is None:
        return _empty_error(
            width=width,
            height=height,
            latency_ms=latency_ms,
            device=device,
            code=ErrorCode.INVALID_INPUT,
            message="expected width,height >= 1 and a blaze33 buffer",
        )
    if num_people == 0:
        return _empty_error(
            width=width,
            height=height,
            latency_ms=latency_ms,
            device=device,
            code=ErrorCode.NO_PERSON,
            message="no detections",
        )

    detections: list[Detection] = []
    poses: list[Pose] = []
    any_low = False
    for p in range(num_people):
        person = xyz_vis[p]
        kps: list[Keypoint] = []
        vis_sum = 0.0
        xs: list[float] = []
        ys: list[float] = []
        for coco_i, blaze_i in enumerate(BLAZE_TO_COCO):
            x = float(person[blaze_i, 0])
            y = float(person[blaze_i, 1])
            z = float(person[blaze_i, 2])
            v = min(1.0, max(0.0, float(person[blaze_i, 3])))
            vis_sum += v
            kps.append(
                Keypoint(name=COCO17_NAMES[coco_i], x=x, y=y, z=z, confidence=v)
            )
            if v >= VIS_BBOX:
                xs.append(x)
                ys.append(y)
        mean_v = vis_sum / 17.0
        if mean_v < VIS_PERSON or not xs:
            any_low = True
            continue
        detections.append(
            Detection(
                class_name="person",
                confidence=mean_v,
                bbox_xyxy=(
                    min(max(min(xs), 0.0), float(width)),
                    min(max(min(ys), 0.0), float(height)),
                    min(max(max(xs), 0.0), float(width)),
                    min(max(max(ys), 0.0), float(height)),
                ),
            )
        )
        poses.append(
            Pose(
                skeleton=SkeletonKind.COCO_17,
                keypoints=kps,
                score=mean_v,
                detection_index=len(detections) - 1,
            )
        )

    if not detections:
        code = ErrorCode.LOW_CONFIDENCE if any_low else ErrorCode.NO_PERSON
        msg = (
            "all detections below vis threshold 0.25"
            if any_low
            else "no detections"
        )
        return _empty_error(
            width=width,
            height=height,
            latency_ms=latency_ms,
            device=device,
            code=code,
            message=msg,
        )

    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.IMAGE,
            timestamp_ms=0.0,
            width=width,
            height=height,
        ),
        detections=detections,
        poses=poses,
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name=MODEL_NAME,
            latency_ms=latency_ms,
            device=device or "cpu",
        ),
        error=None,
    )


def _dll_path() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "native" / "core_map"
    for name in ("core_map.dll", "libcore_map.dll", "libcore_map.so", "libcore_map.dylib"):
        for folder in (
            root / "build",
            root / "build" / "Release",
            root / "build" / "Debug",
            root,
        ):
            cand = folder / name
            if cand.exists():
                return cand
    return None


def map_blaze33_native(
    xyz_vis: np.ndarray | None,
    *,
    num_people: int,
    width: int,
    height: int,
    latency_ms: float,
    device: str,
) -> CoreInferenceResult:
    path = _dll_path()
    if path is None:
        raise FileNotFoundError("core_map shared library not built")
    lib = ctypes.CDLL(str(path))
    lib.core_map_from_blaze33.restype = ctypes.c_void_p
    lib.core_map_from_blaze33.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_float,
        ctypes.c_char_p,
    ]
    lib.core_map_free.argtypes = [ctypes.c_void_p]
    buf = None
    if num_people > 0 and xyz_vis is not None:
        flat = np.ascontiguousarray(xyz_vis.astype(np.float32).reshape(-1))
        buf = flat.ctypes.data_as(ctypes.c_void_p)
    raw = lib.core_map_from_blaze33(
        buf,
        int(num_people),
        int(width),
        int(height),
        float(latency_ms),
        (device or "cpu").encode("utf-8"),
    )
    if not raw:
        raise RuntimeError("core_map_from_blaze33 returned NULL")
    try:
        json_text = ctypes.cast(raw, ctypes.c_char_p).value
        if json_text is None:
            raise RuntimeError("core_map JSON was empty")
        return CoreInferenceResult.model_validate_json(json_text.decode("utf-8"))
    finally:
        lib.core_map_free(raw)
