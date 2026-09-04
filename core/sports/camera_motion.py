"""Background camera motion estimation and 2D coordinate compensation (P1c).

Sparse optical flow outside the skier bbox, RANSAC affine fit, and hip
coordinate stabilization for steering. Pure numpy/OpenCV — no Qt dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - optional at import, required at runtime
    cv2 = None  # type: ignore[assignment]


class CameraMotionClass(str, Enum):
    STATIC = "static"
    PANNING = "panning"
    FOLLOW = "follow"


@dataclass(frozen=True)
class CameraMotionFrame:
    """Per-frame background motion estimate."""

    affine_2x3: np.ndarray
    flow_quality: float
    motion_class: CameraMotionClass


@dataclass
class CameraMotionResult:
    frames: list[CameraMotionFrame]
    motion_class: CameraMotionClass
    mean_flow_quality: float

    def compensate_points(self, points: np.ndarray, frame_index: int) -> np.ndarray:
        """Apply inverse affine to (n, 2) pixel coordinates."""
        if frame_index < 0 or frame_index >= len(self.frames):
            return points
        mat = self.frames[frame_index].affine_2x3
        if mat.shape != (2, 3):
            return points
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[1] != 2:
            return points
        hom = np.column_stack([pts, np.ones(len(pts))])
        inv = cv2.invertAffineTransform(mat) if cv2 is not None else _invert_affine(mat)
        out = hom @ inv.T
        return out


def _invert_affine(mat: np.ndarray) -> np.ndarray:
    a = np.vstack([mat, [0.0, 0.0, 1.0]])
    return np.linalg.inv(a)[:2, :]


def _require_cv2() -> None:
    if cv2 is None:
        raise RuntimeError("opencv-python required for camera motion compensation")


def _skier_bbox(
    hip_xy: tuple[float, float] | None,
    ankle_xy: tuple[float, float] | None,
    width: int,
    height: int,
    *,
    pad: float = 0.35,
) -> tuple[int, int, int, int]:
    """Rough skier rectangle for background masking."""
    pts = [p for p in (hip_xy, ankle_xy) if p is not None]
    if not pts:
        return 0, 0, width, height
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = float(np.mean(xs))
    cy = float(np.mean(ys))
    span = max(max(xs) - min(xs), max(ys) - min(ys), 40.0)
    half = span * (0.5 + pad)
    x0 = int(max(0, cx - half))
    y0 = int(max(0, cy - half))
    x1 = int(min(width, cx + half))
    y1 = int(min(height, cy + half))
    return x0, y0, x1, y1


def _estimate_affine(
    prev_gray: np.ndarray,
    gray: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> tuple[np.ndarray, float]:
    _require_cv2()
    h, w = gray.shape
    mask = np.ones((h, w), dtype=np.uint8) * 255
    x0, y0, x1, y1 = bbox
    mask[y0:y1, x0:x1] = 0
    pts = cv2.goodFeaturesToTrack(
        prev_gray,
        maxCorners=120,
        qualityLevel=0.01,
        minDistance=8,
        mask=mask,
    )
    if pts is None or len(pts) < 8:
        identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        return identity, 0.0
    nxt, status, _err = cv2.calcOpticalFlowPyrLK(prev_gray, gray, pts, None)
    if nxt is None or status is None:
        identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        return identity, 0.0
    good = status.reshape(-1) == 1
    p0 = pts[good].reshape(-1, 2)
    p1 = nxt[good].reshape(-1, 2)
    if len(p0) < 6:
        identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        return identity, 0.0
    mat, inliers = cv2.estimateAffinePartial2D(
        p0,
        p1,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
    )
    if mat is None:
        identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        return identity, 0.0
    quality = float(np.count_nonzero(inliers)) / float(len(p0))
    return mat.astype(np.float64), quality


def _classify_motion(
    hip_travel_leg: float,
    flow_qualities: list[float],
) -> CameraMotionClass:
    mean_q = float(np.mean(flow_qualities)) if flow_qualities else 0.0
    if hip_travel_leg >= 3.0:
        return CameraMotionClass.STATIC
    if hip_travel_leg <= 1.0 and mean_q >= 0.25:
        return CameraMotionClass.FOLLOW
    return CameraMotionClass.PANNING


def estimate_camera_motion(
    frames_bgr: list[np.ndarray],
    hip_pixels: list[tuple[float, float] | None],
    *,
    leg_len_px: float = 120.0,
    ankle_pixels: list[tuple[float, float] | None] | None = None,
    stride: int = 2,
) -> CameraMotionResult:
    """Estimate background affine motion on a sparse frame sample."""
    _require_cv2()
    n = len(frames_bgr)
    if n == 0:
        return CameraMotionResult([], CameraMotionClass.STATIC, 0.0)
    ankle_pixels = ankle_pixels or [None] * n
    indices = list(range(0, n, max(stride, 1)))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames_bgr]
    h, w = grays[0].shape
    results: list[CameraMotionFrame] = []
    qualities: list[float] = []
    prev_i = indices[0]
    for i in indices[1:]:
        bbox = _skier_bbox(hip_pixels[i], ankle_pixels[i], w, h)
        mat, quality = _estimate_affine(grays[prev_i], grays[i], bbox)
        hip_travel = 0.0
        if hip_pixels[prev_i] is not None and hip_pixels[i] is not None:
            dx = hip_pixels[i][0] - hip_pixels[prev_i][0]
            dy = hip_pixels[i][1] - hip_pixels[prev_i][1]
            hip_travel = float(np.hypot(dx, dy) / max(leg_len_px, 1.0))
        motion = _classify_motion(hip_travel, [quality])
        results.append(
            CameraMotionFrame(
                affine_2x3=mat,
                flow_quality=quality,
                motion_class=motion,
            )
        )
        qualities.append(quality)
        prev_i = i
    if not results:
        identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        results = [
            CameraMotionFrame(
                affine_2x3=identity,
                flow_quality=0.0,
                motion_class=CameraMotionClass.STATIC,
            )
        ]
    travel_leg = 0.0
    hips = [p for p in hip_pixels if p is not None]
    if len(hips) >= 2:
        dx = hips[-1][0] - hips[0][0]
        dy = hips[-1][1] - hips[0][1]
        travel_leg = float(np.hypot(dx, dy) / max(leg_len_px, 1.0))
    overall = _classify_motion(travel_leg, qualities)
    return CameraMotionResult(
        frames=results,
        motion_class=overall,
        mean_flow_quality=float(np.mean(qualities)) if qualities else 0.0,
    )


def compensate_hip_path(
    hip_pixels: list[tuple[float, float] | None],
    motion: CameraMotionResult,
) -> list[tuple[float, float] | None]:
    """Stabilize hip positions using per-step inverse affines."""
    if not hip_pixels or not motion.frames:
        return hip_pixels
    out: list[tuple[float, float] | None] = [hip_pixels[0]]
    for i in range(1, len(hip_pixels)):
        pt = hip_pixels[i]
        if pt is None:
            out.append(None)
            continue
        frame_idx = min(i - 1, len(motion.frames) - 1)
        arr = motion.compensate_points(np.array([pt], dtype=np.float64), frame_idx)
        out.append((float(arr[0, 0]), float(arr[0, 1])))
    return out
