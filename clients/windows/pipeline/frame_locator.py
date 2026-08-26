"""Clip/frame locator strings, overlay paint, and clipboard payload."""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np

from schemas.clip_analysis import AnalyzedFrame, ClipAnalysis, BlazeJoint
from schemas.core_inference import Pose


def short_clip_id(clip_id: str) -> str:
    compact = clip_id.replace("-", "").lower()
    if len(compact) >= 8:
        return compact[:8]
    return clip_id[:8] if clip_id else ""


def draw_locator_label(bgr: np.ndarray, text: str) -> np.ndarray:
    out = bgr.copy()
    origin = (12, 28)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    cv2.putText(out, text, origin, font, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(out, text, origin, font, scale, (245, 245, 245), 1, cv2.LINE_AA)
    return out


def _blaze_payload(joints: list[BlazeJoint] | None) -> list[dict] | None:
    if not joints:
        return None
    return [
        {
            "x": joint.x,
            "y": joint.y,
            "z": joint.z,
            "confidence": joint.confidence,
        }
        for joint in joints
    ]


def _coco_payload(pose: Pose | None) -> list[dict] | None:
    if pose is None:
        return None
    return [
        {
            "name": point.name,
            "x": point.x,
            "y": point.y,
            "z": point.z,
            "confidence": point.confidence,
        }
        for point in pose.keypoints
    ]


def build_locator_payload(
    *,
    clip_id: str,
    display_name: str,
    video_frame: int,
    t_ms: float,
    fps: float,
    analysis: ClipAnalysis | None,
    analyzed: AnalyzedFrame | None,
    pose_index: int | None,
    stage_id: str,
    feedback: dict[str, Any] | None,
) -> dict[str, Any]:
    pose = None
    if analyzed is not None and analyzed.result.poses:
        pose = analyzed.result.poses[0]
    pose_count = len(analysis.frames) if analysis is not None else 0
    return {
        "clip_id": clip_id,
        "short_id": short_clip_id(clip_id),
        "display_name": display_name,
        "video_frame": video_frame,
        "pose_index": pose_index,
        "pose_count": pose_count,
        "t_ms": t_ms,
        "fps": fps,
        "stage_id": stage_id,
        "blaze33": _blaze_payload(analyzed.blaze33 if analyzed is not None else None),
        "coco17": _coco_payload(pose),
        "feedback": feedback,
    }


def locator_payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
