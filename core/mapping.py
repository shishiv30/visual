"""Map detector/pose tensors into CoreInferenceResult."""

from __future__ import annotations

from typing import Any, Never

import numpy as np

from schemas.core_inference import (
    COCO17_NAMES,
    CameraIntrinsics,
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


def _empty_lists() -> dict[str, Any]:
    return {
        "detections": [],
        "poses": [],
        "tracks": [],
        "classifications": [],
        "segments": [],
    }


def dummy_frame(
    bgr: np.ndarray | None,
    source_kind: SourceKind,
    timestamp_ms: float,
    camera_intrinsics: CameraIntrinsics | None,
) -> FrameMeta:
    width, height = 1, 1
    if isinstance(bgr, np.ndarray) and bgr.ndim >= 2:
        height = int(bgr.shape[0]) or 1
        width = int(bgr.shape[1]) or 1
    return FrameMeta(
        source_kind=source_kind,
        timestamp_ms=timestamp_ms,
        width=width,
        height=height,
        camera_intrinsics=camera_intrinsics,
    )


def invalid_input(message: str, meta: ModelMeta, frame: FrameMeta) -> CoreInferenceResult:
    return _error_result(ErrorCode.INVALID_INPUT, message, meta, frame)


def gpu_oom(message: str, meta: ModelMeta, frame: FrameMeta) -> CoreInferenceResult:
    return _error_result(ErrorCode.GPU_OOM, message, meta, frame)


def _error_result(
    code: ErrorCode,
    message: str,
    meta: ModelMeta,
    frame: FrameMeta,
) -> CoreInferenceResult:
    match code:
        case (
            ErrorCode.NO_PERSON
            | ErrorCode.LOW_CONFIDENCE
            | ErrorCode.GPU_OOM
            | ErrorCode.INVALID_INPUT
        ):
            return CoreInferenceResult(
                frame=frame,
                model_meta=meta,
                error=InferenceError(code=code, message=message),
                **_empty_lists(),
            )
        case _:
            unreachable: Never = code
            raise ValueError(unreachable)


def map_pose_arrays(
    *,
    frame: FrameMeta,
    model_meta: ModelMeta,
    boxes_xyxy: np.ndarray,
    boxes_conf: np.ndarray,
    boxes_cls: np.ndarray,
    class_names: dict[int, str],
    kpts_xy: np.ndarray | None,
    kpts_conf: np.ndarray | None,
    conf_threshold: float,
) -> CoreInferenceResult:
    detections: list[Detection] = []
    poses: list[Pose] = []
    n = int(boxes_xyxy.shape[0]) if boxes_xyxy.size else 0
    for i in range(n):
        conf = float(boxes_conf[i])
        if conf < conf_threshold:
            continue
        cls_id = int(boxes_cls[i])
        class_name = class_names.get(cls_id, str(cls_id))
        xyxy = boxes_xyxy[i]
        detections.append(
            Detection(
                class_name=class_name,
                confidence=conf,
                bbox_xyxy=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
            )
        )
        if kpts_xy is not None and kpts_conf is not None and i < kpts_xy.shape[0]:
            kps: list[Keypoint] = []
            for j, name in enumerate(COCO17_NAMES):
                kps.append(
                    Keypoint(
                        name=name,
                        x=float(kpts_xy[i, j, 0]),
                        y=float(kpts_xy[i, j, 1]),
                        confidence=float(kpts_conf[i, j]),
                    )
                )
            poses.append(
                Pose(
                    skeleton=SkeletonKind.COCO_17,
                    keypoints=kps,
                    score=conf,
                    detection_index=len(detections) - 1,
                )
            )

    error: InferenceError | None = None
    if not detections:
        if n == 0:
            error = InferenceError(code=ErrorCode.NO_PERSON, message="no detections")
        else:
            error = InferenceError(
                code=ErrorCode.LOW_CONFIDENCE,
                message=f"all detections below conf_threshold={conf_threshold}",
            )

    return CoreInferenceResult(
        frame=frame,
        detections=detections,
        poses=poses,
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=model_meta,
        error=error,
    )


def frame_from_bgr(
    bgr: np.ndarray,
    *,
    source_kind: SourceKind,
    timestamp_ms: float,
    camera_intrinsics: CameraIntrinsics | None,
) -> FrameMeta:
    return FrameMeta(
        source_kind=source_kind,
        timestamp_ms=timestamp_ms,
        width=int(bgr.shape[1]),
        height=int(bgr.shape[0]),
        camera_intrinsics=camera_intrinsics,
    )
