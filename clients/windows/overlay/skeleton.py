"""COCO-17 skeleton overlay on BGR frames."""

from __future__ import annotations

import cv2
import numpy as np

from schemas.core_inference import CoreInferenceResult

COCO17_EDGES: tuple[tuple[int, int], ...] = (
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
)

MIN_VIS = 0.3


def draw_poses(bgr: np.ndarray, result: CoreInferenceResult) -> np.ndarray:
    out = bgr.copy()
    for pose in result.poses:
        pts = pose.keypoints
        if len(pts) < 17:
            continue
        for a, b in COCO17_EDGES:
            pa, pb = pts[a], pts[b]
            if pa.confidence < MIN_VIS or pb.confidence < MIN_VIS:
                continue
            cv2.line(
                out,
                (int(pa.x), int(pa.y)),
                (int(pb.x), int(pb.y)),
                (0, 165, 255),
                2,
                cv2.LINE_AA,
            )
        for kp in pts:
            if kp.confidence < MIN_VIS:
                continue
            cv2.circle(out, (int(kp.x), int(kp.y)), 4, (0, 0, 255), -1, cv2.LINE_AA)
        if result.detections:
            idx = pose.detection_index if pose.detection_index is not None else 0
            if 0 <= idx < len(result.detections):
                x1, y1, x2, y2 = result.detections[idx].bbox_xyxy
                cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), (0, 220, 0), 2)
    return out
