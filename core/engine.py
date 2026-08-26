"""YOLO11 pose/detect Core engine."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

from core.mapping import (
    dummy_frame,
    frame_from_bgr,
    gpu_oom,
    invalid_input,
    map_pose_arrays,
)
from schemas.core_inference import (
    CameraIntrinsics,
    CoreInferenceResult,
    ModelMeta,
    SourceKind,
)

DEFAULT_WEIGHTS = "yolo11n-pose.pt"


class CoreEngine:
    def __init__(
        self,
        weights: str | Path = DEFAULT_WEIGHTS,
        *,
        device: str | None = None,
        conf_threshold: float = 0.25,
    ) -> None:
        if device is None:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.conf_threshold = conf_threshold
        self.weights = str(weights)
        self.model = YOLO(self.weights)
        self.model.to(device)

    def infer(
        self,
        bgr: np.ndarray,
        *,
        source_kind: SourceKind = SourceKind.IMAGE,
        timestamp_ms: float = 0.0,
        camera_intrinsics: CameraIntrinsics | None = None,
        imgsz: int | None = None,
    ) -> CoreInferenceResult:
        backend_id = "yolo11n-pose" if "pose" in Path(self.weights).name else "yolo11n"
        meta = ModelMeta(
            backend_id=backend_id,
            model_name=Path(self.weights).name,
            latency_ms=0.0,
            device=self.device,
        )
        if bgr is None or not isinstance(bgr, np.ndarray) or bgr.ndim != 3 or bgr.size == 0:
            dummy = dummy_frame(bgr, source_kind, timestamp_ms, camera_intrinsics)
            return invalid_input("expected a non-empty HxWxC BGR image", meta, dummy)

        frame = frame_from_bgr(
            bgr,
            source_kind=source_kind,
            timestamp_ms=timestamp_ms,
            camera_intrinsics=camera_intrinsics,
        )
        if imgsz is None:
            imgsz = ((frame.height + 31) // 32) * 32

        t0 = time.perf_counter()
        try:
            results = self.model.predict(
                bgr,
                verbose=False,
                device=self.device,
                imgsz=imgsz,
            )
            if self.device.startswith("cuda"):
                torch.cuda.synchronize()
        except torch.cuda.OutOfMemoryError as exc:
            return gpu_oom(str(exc), meta, frame)

        meta = meta.model_copy(update={"latency_ms": (time.perf_counter() - t0) * 1000.0})
        result = results[0]
        names = {int(k): str(v) for k, v in result.names.items()}
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            boxes_xyxy = np.zeros((0, 4), dtype=np.float32)
            boxes_conf = np.zeros((0,), dtype=np.float32)
            boxes_cls = np.zeros((0,), dtype=np.float32)
        else:
            boxes_xyxy = boxes.xyxy.detach().cpu().numpy()
            boxes_conf = boxes.conf.detach().cpu().numpy()
            boxes_cls = boxes.cls.detach().cpu().numpy()

        kpts_xy = None
        kpts_conf = None
        keypoints = result.keypoints
        if keypoints is not None and keypoints.xy is not None and len(keypoints) > 0:
            kpts_xy = keypoints.xy.detach().cpu().numpy()
            if keypoints.conf is not None:
                kpts_conf = keypoints.conf.detach().cpu().numpy()
            else:
                kpts_conf = np.ones(kpts_xy.shape[:2], dtype=np.float32)

        return map_pose_arrays(
            frame=frame,
            model_meta=meta,
            boxes_xyxy=boxes_xyxy,
            boxes_conf=boxes_conf,
            boxes_cls=boxes_cls,
            class_names=names,
            kpts_xy=kpts_xy,
            kpts_conf=kpts_conf,
            conf_threshold=self.conf_threshold,
        )
