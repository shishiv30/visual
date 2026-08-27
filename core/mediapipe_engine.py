"""Offline MediaPipe Pose Landmarker → CoreInferenceResult."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from core.blaze_map import map_blaze33
from core.mapping import dummy_frame, invalid_input
from core.person_roi import crop_for_pose, remap_from_crop
from core.pose_filter import (
    crop_box_for_retry,
    crop_disagrees_with_prev,
    ema_smooth,
    is_plausible,
    pick_primary,
    reject_implausible,
    remap_to_full,
)
from schemas.core_inference import (
    BackendId,
    CameraIntrinsics,
    CoreInferenceResult,
    ModelMeta,
    SourceKind,
)

DEFAULT_TASK = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_full.task"


class MediaPipeEngine:
    def __init__(
        self,
        task_path: str | Path | None = None,
        *,
        num_poses: int = 2,
        min_score: float = 0.5,
        video: bool = False,
    ) -> None:
        try:
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import (
                PoseLandmarker,
                PoseLandmarkerOptions,
                RunningMode,
            )
        except ImportError as exc:
            raise ImportError(
                "mediapipe is required for MediaPipeEngine. "
                "pip install -r requirements-mediapipe.txt"
            ) from exc

        path = Path(task_path) if task_path else DEFAULT_TASK
        if not path.is_file():
            raise FileNotFoundError(
                f"missing {path}; run python scripts/download_pose_landmarker.py"
            )
        self.task_path = path
        self.device = "cpu"
        self._video = video
        self._last_bbox: tuple[float, float, float, float] | None = None
        self._last_result: CoreInferenceResult | None = None
        self._last_ts = -1
        self.last_blaze33: np.ndarray | None = None
        import sys
        # macOS Metal GPU delegate crashes from a background thread; force CPU there only.
        # On Windows leave delegate unset so mediapipe auto-selects (GPU when available).
        base_kwargs: dict = {"model_asset_path": str(path)}
        if sys.platform == "darwin":
            base_kwargs["delegate"] = BaseOptions.Delegate.CPU
        mode = RunningMode.VIDEO if video else RunningMode.IMAGE
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(**base_kwargs),
            running_mode=mode,
            num_poses=num_poses,
            min_pose_detection_confidence=min_score,
            min_pose_presence_confidence=min_score,
            min_tracking_confidence=min_score,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)
        crop_options = PoseLandmarkerOptions(
            base_options=BaseOptions(**base_kwargs),
            running_mode=RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=min_score,
            min_pose_presence_confidence=min_score,
            min_tracking_confidence=min_score,
        )
        self._crop_landmarker = PoseLandmarker.create_from_options(crop_options)

    def close(self) -> None:
        for lm in (self._landmarker, self._crop_landmarker):
            closer = getattr(lm, "close", None)
            if callable(closer):
                closer()

    def infer(
        self,
        bgr: np.ndarray,
        *,
        source_kind: SourceKind = SourceKind.IMAGE,
        timestamp_ms: float = 0.0,
        camera_intrinsics: CameraIntrinsics | None = None,
        roi_hint: tuple[float, float, float, float] | None = None,
    ) -> CoreInferenceResult:
        meta = ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name=self.task_path.name,
            latency_ms=0.0,
            device=self.device,
        )
        if bgr is None or not isinstance(bgr, np.ndarray) or bgr.ndim != 3 or bgr.size == 0:
            dummy = dummy_frame(bgr, source_kind, timestamp_ms, camera_intrinsics)
            return invalid_input("expected a non-empty HxWxC BGR image", meta, dummy)

        height, width = int(bgr.shape[0]), int(bgr.shape[1])
        t0 = time.perf_counter()
        mapped: CoreInferenceResult | None = None
        if roi_hint is not None:
            crop, ox, oy, scale = crop_for_pose(bgr, roi_hint)
            cropped = self._detect_crop(crop)
            cropped = remap_from_crop(cropped, ox, oy, scale, width, height)
            cropped = pick_primary(cropped, self._last_bbox)
            crop_ok = is_plausible(cropped) or (
                cropped.error is None and cropped.poses
            )
            if crop_ok and not crop_disagrees_with_prev(self._last_result, cropped):
                mapped = cropped
        if mapped is None:
            mapped = self._detect_full(bgr, timestamp_ms)
            mapped = pick_primary(mapped, self._last_bbox)
            if not is_plausible(mapped):
                retry_bgr, ox, oy = self._roi_bgr(bgr, mapped)
                if retry_bgr is not None:
                    cropped = self._detect_crop(retry_bgr)
                    cropped = remap_to_full(cropped, ox, oy, width, height)
                    cropped = pick_primary(cropped, self._last_bbox)
                    if (
                        is_plausible(cropped)
                        or (cropped.error is None and cropped.poses)
                    ) and not crop_disagrees_with_prev(self._last_result, cropped):
                        mapped = cropped
                mapped = reject_implausible(mapped)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        mapped.model_meta.model_name = self.task_path.name
        mapped.model_meta.latency_ms = latency_ms
        mapped.frame.source_kind = source_kind
        mapped.frame.timestamp_ms = timestamp_ms
        mapped.frame.camera_intrinsics = camera_intrinsics
        mapped.frame.width = width
        mapped.frame.height = height
        mapped = ema_smooth(self._last_result, mapped)
        if mapped.error is None and mapped.detections:
            self._last_bbox = mapped.detections[0].bbox_xyxy
            self._last_result = mapped
        else:
            self._last_result = None
        return mapped

    def _detect_full(self, bgr: np.ndarray, timestamp_ms: float) -> CoreInferenceResult:
        import mediapipe as mp

        height, width = int(bgr.shape[0]), int(bgr.shape[1])
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        t0 = time.perf_counter()
        if self._video:
            ts = int(max(timestamp_ms, self._last_ts + 1))
            self._last_ts = ts
            result = self._landmarker.detect_for_video(mp_image, ts)
        else:
            result = self._landmarker.detect(mp_image)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return self._landmarks_to_core(result, width, height, latency_ms)

    def _detect_crop(self, bgr: np.ndarray) -> CoreInferenceResult:
        import mediapipe as mp

        height, width = int(bgr.shape[0]), int(bgr.shape[1])
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        t0 = time.perf_counter()
        result = self._crop_landmarker.detect(mp_image)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return self._landmarks_to_core(result, width, height, latency_ms)

    def _roi_bgr(
        self, bgr: np.ndarray, mapped: CoreInferenceResult
    ) -> tuple[np.ndarray | None, int, int]:
        w = int(bgr.shape[1])
        h = int(bgr.shape[0])
        bbox: tuple[float, float, float, float] | None = None
        if mapped.detections:
            bbox = mapped.detections[0].bbox_xyxy
        elif self._last_bbox is not None:
            bbox = self._last_bbox
        if bbox is None:
            return None, 0, 0
        x1, y1, x2, y2 = crop_box_for_retry(bbox, w, h)
        crop = bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return None, 0, 0
        return crop, x1, y1

    def _landmarks_to_core(
        self, result: object, width: int, height: int, latency_ms: float
    ) -> CoreInferenceResult:
        pose_list = getattr(result, "pose_landmarks", None) or []
        n = len(pose_list)
        xyz = np.zeros((max(n, 0), 33, 4), dtype=np.float32)
        for i, lm_list in enumerate(pose_list):
            for j, lm in enumerate(lm_list[:33]):
                vis = lm.visibility if lm.visibility is not None else lm.presence
                if vis is None:
                    vis = 1.0
                xyz[i, j, 0] = float(lm.x) * width
                xyz[i, j, 1] = float(lm.y) * height
                xyz[i, j, 2] = float(lm.z) * width
                xyz[i, j, 3] = float(vis)
        self.last_blaze33 = xyz[0].copy() if n else None
        return map_blaze33(
            xyz if n else None,
            num_people=n,
            width=width,
            height=height,
            latency_ms=latency_ms,
            device=self.device,
        )
